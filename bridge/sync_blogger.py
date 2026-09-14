#!/usr/bin/env python3
"""SFANDOM Blogger feed sync.

Fail-closed ingest layer:
- HTTPS feed only.
- Reject malformed, empty, oversized or implausible feeds.
- Sanitize remote HTML before it ever reaches generated pages.
- Never overwrites current.json until validation succeeds.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CURRENT = DATA_DIR / "current.json"
MAX_FEED_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 8
MAX_POSTS = 30
MAX_TITLE = 300
MAX_SUMMARY = 3000
MAX_BODY_HTML = 200_000
DEFAULT_REQUIRED_LABEL = "SFANDOM-SYNC"
ALLOWED_SCHEMES = {"http", "https"}

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
IMG_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.I)

ALLOWED_TAGS = {
    "article","section","div","span","p","br","hr","h2","h3","h4",
    "strong","b","em","i","u","small","blockquote","ul","ol","li",
    "a","img","figure","figcaption"
}
VOID_TAGS = {"br","hr","img"}
SKIP_TAGS = {"script","style","iframe","object","embed","form","input","button","textarea","select","option","svg","math"}
GLOBAL_ATTRS = {"class","title"}
TAG_ATTRS = {
    "a": {"href","target","rel"},
    "img": {"src","alt","width","height","loading","decoding"},
}


def clean_text(value: str | None, limit: int) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = TAG_RE.sub(" ", value)
    value = SPACE_RE.sub(" ", value).strip()
    return value[:limit]


def safe_url(value: str | None, allow_relative: bool = False) -> str | None:
    if not value:
        return None
    value = html.unescape(value).strip()
    if allow_relative and (value.startswith("/") or value.startswith("#")):
        return value
    parsed = urlparse(value)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.netloc:
        return None
    return value


class SafeHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth or tag not in ALLOWED_TAGS:
            return
        allowed = GLOBAL_ATTRS | TAG_ATTRS.get(tag, set())
        clean_attrs = []
        has_loading = has_decoding = False
        for k, v in attrs:
            k = k.lower()
            if k.startswith("on") or k == "style" or k not in allowed or v is None:
                continue
            if k in {"href","src"}:
                u = safe_url(v, allow_relative=(k == "href"))
                if not u:
                    continue
                v = u
            if k == "target" and v != "_blank":
                continue
            if k == "rel":
                v = "noopener noreferrer"
            if k == "loading": has_loading = True
            if k == "decoding": has_decoding = True
            clean_attrs.append((k, v))
        if tag == "img":
            if not has_loading: clean_attrs.append(("loading", "lazy"))
            if not has_decoding: clean_attrs.append(("decoding", "async"))
        if tag == "a" and any(k == "target" and v == "_blank" for k,v in clean_attrs) and not any(k == "rel" for k,_ in clean_attrs):
            clean_attrs.append(("rel", "noopener noreferrer"))
        attr_text = "".join(f' {k}="{html.escape(v, quote=True)}"' for k,v in clean_attrs)
        self.out.append(f"<{tag}{attr_text}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth or tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip_depth:
            self.out.append(html.escape(data))

    def handle_entityref(self, name):
        if not self.skip_depth:
            self.out.append(f"&{name};")

    def handle_charref(self, name):
        if not self.skip_depth:
            self.out.append(f"&#{name};")


def sanitize_html(value: str | None) -> str:
    if not value:
        return ""
    parser = SafeHTML()
    parser.feed(value[:MAX_BODY_HTML])
    parser.close()
    return "".join(parser.out).strip()


def first_image_from_html(value: str | None) -> str | None:
    if not value:
        return None
    match = IMG_RE.search(value)
    return safe_url(match.group(1)) if match else None


def fetch_feed(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Feed URL must be an absolute HTTPS URL")
    req = urllib.request.Request(url, headers={
        "User-Agent": "SFANDOM-Blogger-Bridge/2.0",
        "Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_FEED_BYTES:
            raise ValueError("Feed exceeds size limit")
        payload = response.read(MAX_FEED_BYTES + 1)
    if len(payload) > MAX_FEED_BYTES:
        raise ValueError("Feed exceeds size limit")
    if not payload.strip():
        raise ValueError("Feed is empty")
    return payload


def parse_atom(root: ET.Element) -> list[dict]:
    ns = {"a": "http://www.w3.org/2005/Atom"}
    posts = []
    for entry in root.findall("a:entry", ns)[:MAX_POSTS]:
        post_id = clean_text(entry.findtext("a:id", default="", namespaces=ns), 500)
        title = clean_text(entry.findtext("a:title", default="", namespaces=ns), MAX_TITLE)
        published = (entry.findtext("a:published", default="", namespaces=ns) or entry.findtext("a:updated", default="", namespaces=ns))
        updated = entry.findtext("a:updated", default="", namespaces=ns)
        link = None
        for el in entry.findall("a:link", ns):
            href = safe_url(el.attrib.get("href"))
            if el.attrib.get("rel", "alternate") == "alternate" and href:
                link = href; break
        raw = entry.findtext("a:content", default="", namespaces=ns) or entry.findtext("a:summary", default="", namespaces=ns)
        labels = [clean_text(c.attrib.get("term", ""), 100) for c in entry.findall("a:category", ns) if c.attrib.get("term")]
        if not title or not link:
            continue
        posts.append({
            "id": post_id or link,
            "title": title,
            "url": link,
            "published": clean_text(published, 100),
            "updated": clean_text(updated, 100),
            "labels": labels[:20],
            "summary": clean_text(raw, MAX_SUMMARY),
            "image": first_image_from_html(raw),
            "body_html": sanitize_html(raw),
        })
    return posts


def parse_rss(root: ET.Element) -> list[dict]:
    posts = []
    channel = root.find("channel")
    if channel is None:
        return posts
    for item in channel.findall("item")[:MAX_POSTS]:
        title = clean_text(item.findtext("title", default=""), MAX_TITLE)
        link = safe_url(item.findtext("link", default=""))
        guid = clean_text(item.findtext("guid", default=""), 500)
        published = clean_text(item.findtext("pubDate", default=""), 100)
        raw = item.findtext("description", default="")
        labels = [clean_text(c.text, 100) for c in item.findall("category") if c.text]
        if not title or not link:
            continue
        posts.append({
            "id": guid or link,
            "title": title,
            "url": link,
            "published": published,
            "updated": published,
            "labels": labels[:20],
            "summary": clean_text(raw, MAX_SUMMARY),
            "image": first_image_from_html(raw),
            "body_html": sanitize_html(raw),
        })
    return posts


def parse_feed(payload: bytes) -> list[dict]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError(f"Malformed XML: {exc}") from exc
    local = root.tag.rsplit("}", 1)[-1].lower()
    if local == "feed": posts = parse_atom(root)
    elif local == "rss": posts = parse_rss(root)
    else: raise ValueError(f"Unsupported feed root: {local}")
    if not posts:
        raise ValueError("No valid posts found")
    return posts


def filter_required_label(posts: list[dict], label: str) -> list[dict]:
    if not label:
        return posts
    selected = [p for p in posts if label in p.get("labels", [])]
    if not selected:
        raise ValueError(f"No posts contain required label: {label}")
    return selected


def validate(posts: list[dict]) -> None:
    if not (1 <= len(posts) <= MAX_POSTS):
        raise ValueError("Post count outside allowed range")
    seen = set()
    for post in posts:
        if post["url"] in seen:
            raise ValueError("Duplicate post URL detected")
        seen.add(post["url"])
        if len(post["title"]) > MAX_TITLE or len(post["summary"]) > MAX_SUMMARY or len(post.get("body_html", "")) > MAX_BODY_HTML:
            raise ValueError("Field length violation")
        if safe_url(post["url"]) is None:
            raise ValueError("Invalid post URL")
        if post.get("image") and safe_url(post["image"]) is None:
            raise ValueError("Invalid image URL")
        body = post.get("body_html", "").lower()
        for forbidden in ("<script", "<style", "<iframe", "javascript:", " onload=", " onclick="):
            if forbidden in body:
                raise ValueError(f"Unsafe HTML survived sanitizer: {forbidden}")


def atomic_write(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile("wb", dir=DATA_DIR, delete=False) as tmp:
        tmp.write(encoded); tmp.flush(); os.fsync(tmp.fileno()); tmp_name = tmp.name
    os.replace(tmp_name, CURRENT)


def main() -> int:
    feed_url = os.environ.get("SFANDOM_BLOGGER_FEED", "").strip()
    required_label = os.environ.get("SFANDOM_REQUIRED_LABEL", DEFAULT_REQUIRED_LABEL).strip()
    if not feed_url:
        print("NOOP: SFANDOM_BLOGGER_FEED is not configured")
        return 0
    try:
        posts = parse_feed(fetch_feed(feed_url))
        posts = filter_required_label(posts, required_label)
        validate(posts)
        result = {
            "schema": 2,
            "source": "blogger-public-feed",
            "source_url": feed_url,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "post_count": len(posts),
            "posts": posts,
        }
        atomic_write(result)
    except (ValueError, urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: validated {len(posts)} posts -> {CURRENT}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
