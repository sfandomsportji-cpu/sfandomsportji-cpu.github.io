"""SFANDOM magazine: selected links to the owner's Naver blog only.

No remote images, script injection, embeddeds, feed fetches, or article body copies.
Naver RSS cache is loaded by the existing build process; this module only renders
safe, verified owned blog URLs. Invalid or empty items are silently excluded.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

ACCOUNT = "sfandomsport"
POST_URL = re.compile(r"https://blog\.naver\.com/sfandomsport/(\d{8,20})\Z")
FEATURE_TAG = re.compile(r"NBA\s*특집", re.I)
NBA_TAG = re.compile(r"NBA|76ers|Warriors|Kings|Sixers|Knicks|Thunder|Spurs|웸반야마|썬더|워리어스|필라델피아|뉴욕 닉스", re.I)
MLB_TAG = re.compile(r"MLB|NLDS|NLCS|ALDS|ALCS|Dodgers|Braves|Yamamoto|Padres|Brewers|야마모토|다저스|브루어스", re.I)
TENNIS_TAG = re.compile(r"Tennis|Sinner|Alcaraz|Djokovic|Federer|US Open|테니스|알카라스", re.I)
VOLLEY_TAG = re.compile(r"AVC|Volleyball|배구", re.I)


def posts(cache: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for item in cache if isinstance(cache, list) else []:
        if not isinstance(item, dict):
            continue
        # Verify ownership *after* stripping any potential tracking query.
        url = str(item.get("link", "")).split("?", 1)[0].split("#", 1)[0]
        if not POST_URL.fullmatch(url) or url in seen:
            continue
        title = str(item.get("title", "")).strip()
        if not title or len(title) > 400:
            continue
        date = str(item.get("date", ""))
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", date):
            continue
        seen.add(url)
        # Summary belongs to this Naver account; never use images or video frames.
        desc = re.sub(r"\s+", " ", str(item.get("summary", "")).strip())
        result.append({"title": title, "link": url, "date": date, "summary": desc[:190]})
    # Stable on same-day posts: preserve the RSS entry order.
    return sorted(result, key=lambda x: x["date"], reverse=True)


def category(title: str) -> str:
    if FEATURE_TAG.search(title):
        return "NBA · INSIGHT"
    if NBA_TAG.search(title):
        return "NBA · HIGHLIGHTS"
    if MLB_TAG.search(title):
        return "MLB · HIGHLIGHTS"
    if TENNIS_TAG.search(title):
        return "TENNIS"
    if VOLLEY_TAG.search(title):
        return "VOLLEYBALL"
    return "SPORTS"


def card(item: dict, esc, index: int, *, featured: bool) -> str:
    date = item["date"].replace("-", ".")
    intro = (item["summary"][:153].rstrip() + ("…" if len(item["summary"]) > 153 else "")) if item["summary"] else ""
    desc = f'<p>{esc(intro)}</p>' if intro else ''
    return (
        '<a class="nm-card' + (' nm-card--featured' if featured else '') + '"'
        f' href="{esc(item["link"])}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">'
        '<div class="nm-card__top">'
        f'<span class="nm-card__num">{index:02d}</span>'
        f'<span class="nm-card__type">{esc(category(item["title"]))}</span>'
        f'<time datetime="{esc(item["date"])}">{esc(date)}</time></div>'
        f'<h3>{esc(item["title"])}</h3>{desc}'
        '<span class="nm-card__open">네이버 블로그에서 원문 보기 <span aria-hidden="true">↗</span></span>'
        '</a>'
    )


def render(cache: list[dict], esc) -> str:
    listed = posts(cache)
    # Three long-form NBA insights; six newest distinct updates, all owner's posts.
    insights = [p for p in listed if FEATURE_TAG.search(p["title"])][:3]
    featured_urls = {p["link"] for p in insights}
    latest = [p for p in listed if p["link"] not in featured_urls][:6]
    featured_html = ''.join(card(p, esc, i, featured=True) for i, p in enumerate(insights, 1))
    latest_html = ''.join(card(p, esc, i, featured=False) for i, p in enumerate(latest, 1))
    if not listed:
        content = (
            '<div class="nm-empty"><h2>최근 글 목록을 확인하고 있습니다.</h2>'
            '<p>게시글을 추측해서 채우지 않습니다. 최신 글은 네이버 블로그에서 확인해 주세요.</p>'
            '<a href="https://blog.naver.com/sfandomsport" target="_blank" rel="noopener noreferrer">'
            '내 네이버 블로그 바로가기 ↗</a></div>'
        )
    else:
        feature_section = (
            '<section class="nm-section" aria-labelledby="naverSelectTitle">'
            '<div class="nm-section__header"><div><span class="nm-section__eyebrow">EDITOR\'S SELECTION</span>'
            '<h2 id="naverSelectTitle">읽을수록 깊어지는 <em>NBA 특집</em></h2></div>'
            '<p>최근 올라온 자체 해설을 먼저 골랐습니다.</p></div>'
            f'<div class="nm-grid nm-grid--feature">{featured_html}</div></section>'
        ) if featured_html else ''
        latest_section = (
            '<section class="nm-section" aria-labelledby="naverLatestTitle">'
            '<div class="nm-section__header"><div><span class="nm-section__eyebrow">LATEST FROM NAVER</span>'
            '<h2 id="naverLatestTitle">최근 발행 글</h2></div>'
            '<p>최신 게시 순서 · 네이버 원문으로 연결됩니다.</p></div>'
            f'<div class="nm-grid">{latest_html}</div></section>'
        ) if latest_html else ''
        content = feature_section + latest_section
    return (
        '<section class="wrap nm-magazine" aria-labelledby="naverMagazineTitle">'
        '<div class="nm-hero">'
        '<div class="nm-hero__copy"><span class="nm-hero__kicker">SFANDOM × NAVER BLOG</span>'
        '<h2 id="naverMagazineTitle">우리가 쓴 이야기만.<br><em>최근 글을 한눈에.</em></h2>'
        '<p>SFANDOM 네이버 블로그에 직접 게시한 글만 연결합니다. '
        '경기 사진이나 동영상은 이 페이지에서 복사하거나 불러오지 않습니다.</p>'
        '<div class="nm-hero__chips"><span>OWNED POSTS</span><span>NO EXTERNAL IMAGES</span>'
        '<span>DIRECT TO NAVER</span></div></div>'
        '<a class="nm-hero__link" href="https://blog.naver.com/sfandomsport" target="_blank" '
        'rel="noopener noreferrer" referrerpolicy="no-referrer">'
        '<strong>SFANDOM NAVER</strong><span>전체 글 네이버에서 보기 ↗</span></a></div>'
        + content +
        '<p class="nm-magazine__foot">콘텐츠와 영상은 각 네이버 블로그 원문에서 확인합니다. '
        '페이지의 글 목록은 마지막으로 정상 확인된 자체 블로그 게시글을 기준으로 구성됩니다.</p>'
        '</section>'
    )
