#!/usr/bin/env python3
from __future__ import annotations
import html, json, re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "bridge"
CURRENT = BRIDGE / "data/current.json"
STATE = BRIDGE / "state.json"
BLOG = ROOT / "blog"
SITE = "https://sfandom.com"

TEMPLATE = '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{TITLE}} | SFANDOM</title><meta name="description" content="{{DESC}}"><link rel="canonical" href="{{CANONICAL}}">
<link rel="stylesheet" href="/styles.css?v=20260827-clean3"><link rel="stylesheet" href="/assets/css/blog-v1.css?v=20260915-1">
</head><body><header class="blog-header"><a class="blog-brand" href="/">SFANDOM</a><a class="blog-back" href="/blog/">BLOG</a></header>
<main class="blog-shell"><article class="sf-blog-article"><div class="sf-blog-meta">SFANDOM BLOGGER ORIGINAL · {{DATE}}</div><h1>{{TITLE}}</h1><div class="sf-blog-body">{{BODY}}</div></article></main></body></html>'''


def load_json(path, default):
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default


def slug_from_url(url: str, post_id: str) -> str:
    name = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    if name.endswith(".html"): name = name[:-5]
    name = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-").lower()
    if name: return name[:100]
    fallback = re.sub(r"[^a-zA-Z0-9]+", "-", post_id).strip("-").lower()
    return (fallback[-48:] or "post")


def ymd(published: str):
    m = re.search(r"(20\d{2})[-/](\d{2})[-/](\d{2})", published or "")
    if m: return m.group(1), m.group(2), m.group(3)
    now = datetime.utcnow(); return str(now.year), f"{now.month:02d}", f"{now.day:02d}"


def render():
    data = load_json(CURRENT, None)
    if not data or not data.get("posts"):
        print("NOOP: no validated posts to render")
        return 0
    state = load_json(STATE, {"posts": {}}); states = state.setdefault("posts", {})
    cards=[]; generated=0
    for post in data["posts"]:
        pid = post["id"]
        rec = states.get(pid, {})
        slug = rec.get("slug") or slug_from_url(post["url"], pid)
        year, month, day = ymd(post.get("published", ""))
        canonical = rec.get("canonical") or f"{SITE}/blog/{year}/{month}/{slug}/"
        desc = html.escape((post.get("summary") or "")[:160], quote=True)
        title = html.escape(post["title"])
        page = TEMPLATE.replace("{{TITLE}}", title).replace("{{DESC}}", desc).replace("{{CANONICAL}}", canonical).replace("{{DATE}}", f"{year}.{month}.{day}").replace("{{BODY}}", post.get("body_html") or f"<p>{html.escape(post.get('summary',''))}</p>")
        target = BLOG / year / month / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        states[pid] = {"slug": slug, "canonical": canonical, "published": post.get("published"), "updated": post.get("updated"), "status": "published", "source_url": post["url"], "title": post["title"]}
        cards.append((post.get("published", ""), canonical, post["title"], post.get("summary", "")))
        generated += 1
    cards.sort(reverse=True)
    items = "".join(f'<li><a href="{html.escape(url, quote=True)}"><strong>{html.escape(title)}</strong><span>{html.escape(pub[:10])}</span><p>{html.escape(summary[:150])}</p></a></li>' for pub,url,title,summary in cards)
    BLOG.mkdir(parents=True, exist_ok=True)
    (BLOG/"index.html").write_text(f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SFANDOM Blog</title><meta name="description" content="SFANDOM Blogger Originals"><link rel="canonical" href="{SITE}/blog/"><link rel="stylesheet" href="/styles.css?v=20260827-clean3"><link rel="stylesheet" href="/assets/css/blog-v1.css?v=20260915-1"></head><body><header class="blog-header"><a class="blog-brand" href="/">SFANDOM</a></header><main class="blog-shell"><h1>SFANDOM BLOG</h1><ul class="blog-list">{items}</ul></main></body></html>', encoding="utf-8")
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"PASS: rendered {generated} static posts")
    return 0

if __name__ == "__main__": raise SystemExit(render())
