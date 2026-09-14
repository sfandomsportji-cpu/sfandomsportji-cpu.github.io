#!/usr/bin/env python3
"""SFANDOM Blogger bridge sandbox.

Fail-closed behavior:
- Never touches production HTML/CSS.
- Never overwrites current.json unless a complete validation pass succeeds.
- Rejects malformed, empty, oversized, or implausible feeds.
- Emits text/meta only in phase 1; no remote HTML is forwarded.

Usage (sandbox only):
  SFANDOM_BLOGGER_FEED='https://<blog>/feeds/posts/default' python bridge/sync_blogger.py
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import tempfile
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CURRENT = DATA_DIR / "current.json"
MAX_FEED_BYTES = 2 * 1024 * 1024  # phase-1 hard cap: 2 MiB
TIMEOUT_SECONDS = 8
MAX_POSTS = 30
MAX_TITLE = 300
MAX_SUMMARY = 3000

ALLOWED_SCHEMES = {"http", "https"}

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
IMG_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.I)


def clean_text(value: str | None, limit: int) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = TAG_RE.sub(" ", value)
    value = SPACE_RE.sub(" ", value).strip()
    return value[:limit]


def safe_url(value: str | None) -> str | None:
    if not value:
        return None
    value = html.unescape(value).strip()
    parsed = urlparse(value)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.netloc:
        return None
    return value


def first_image_from_html(value: str | None) -> str | None:
    if not value:
        return None
    match = IMG_RE.search(value)
    return safe_url(match.group(1)) if match else None


def fetch_feed(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Feed URL must be an absolute HTTPS URL")

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SFANDOM-Bridge-Sandbox/1.0",
            "Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml;q=0.9",
        },
    )
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
    posts: list[dict] = []
    for entry in root.findall("a:entry", ns)[:MAX_POSTS]:
        title = clean_text(entry.findtext("a:title", default="", namespaces=ns), MAX_TITLE)
        published = (entry.findtext("a:published", default="", namespaces=ns) or
                     entry.findtext("a:updated", default="", namespaces=ns))

        link = None
        for el in entry.findall("a:link", ns):
            rel = el.attrib.get("rel", "alternate")
            href = safe_url(el.attrib.get("href"))
            if rel == "alternate" and href:
                link = href
                break

        raw = (entry.findtext("a:content", default="", namespaces=ns) or
               entry.findtext("a:summary", default="", namespaces=ns))
        summary = clean_text(raw, MAX_SUMMARY)
        image = first_image_from_html(raw)
        labels = [
            clean_text(c.attrib.get("term", ""), 100)
            for c in entry.findall("a:category", ns)
            if c.attrib.get("term")
        ]

        if not title or not link:
            continue
        posts.append({
            "title": title,
            "url": link,
            "published": clean_text(published, 100),
            "labels": labels[:20],
            "summary": summary,
            "image": image,
        })
    return posts


def parse_rss(root: ET.Element) -> list[dict]:
    posts: list[dict] = []
    channel = root.find("channel")
    if channel is None:
        return posts
    for item in channel.findall("item")[:MAX_POSTS]:
        title = clean_text(item.findtext("title", default=""), MAX_TITLE)
        link = safe_url(item.findtext("link", default=""))
        published = clean_text(item.findtext("pubDate", default=""), 100)
        raw = item.findtext("description", default="")
        summary = clean_text(raw, MAX_SUMMARY)
        image = first_image_from_html(raw)
        labels = [clean_text(c.text, 100) for c in item.findall("category") if c.text]
        if not title or not link:
            continue
        posts.append({
            "title": title,
            "url": link,
            "published": published,
            "labels": labels[:20],
            "summary": summary,
            "image": image,
        })
    return posts


def parse_feed(payload: bytes) -> list[dict]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError(f"Malformed XML: {exc}") from exc

    local = root.tag.rsplit("}", 1)[-1].lower()
    if local == "feed":
        posts = parse_atom(root)
    elif local == "rss":
        posts = parse_rss(root)
    else:
        raise ValueError(f"Unsupported feed root: {local}")

    if not posts:
        raise ValueError("No valid posts found")
    return posts


def validate(posts: list[dict]) -> None:
    if not (1 <= len(posts) <= MAX_POSTS):
        raise ValueError("Post count outside allowed range")
    seen = set()
    for post in posts:
        if post["url"] in seen:
            raise ValueError("Duplicate post URL detected")
        seen.add(post["url"])
        if len(post["title"]) > MAX_TITLE or len(post["summary"]) > MAX_SUMMARY:
            raise ValueError("Field length violation")
        if safe_url(post["url"]) is None:
            raise ValueError("Invalid post URL")
        if post.get("image") and safe_url(post["image"]) is None:
            raise ValueError("Invalid image URL")


def atomic_write(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile("wb", dir=DATA_DIR, delete=False) as tmp:
        tmp.write(encoded)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, CURRENT)


def main() -> int:
    feed_url = os.environ.get("SFANDOM_BLOGGER_FEED", "").strip()
    if not feed_url:
        print("BLOCKED: SFANDOM_BLOGGER_FEED is not configured", file=sys.stderr)
        return 2

    try:
        payload = fetch_feed(feed_url)
        posts = parse_feed(payload)
        validate(posts)
        result = {
            "schema": 1,
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
