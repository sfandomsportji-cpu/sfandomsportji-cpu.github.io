"""Curated related original articles. No article body is copied or auto-collapsed."""
from __future__ import annotations


def related(article, catalog, by_key, esc):
    for group in catalog.get('groups', []):
        members = group.get('items', [])
        if not any(m.get('file') == article.file for m in members):
            continue
        siblings = [m for m in members if m.get('file') != article.file]
        links = ''.join(
            f'<a href="{esc(by_key[m["file"][:-3]].url)}">'
            f'<small>{esc(m.get("role", ""))}</small>{esc(m.get("label", ""))} ↗</a>'
            for m in siblings if m.get('file', '')[:-3] in by_key
        )
        if not links:
            return ''
        return (
            f'<section class="editorial-links__related" aria-label="함께 읽는 독립 콘텐츠">'
            f'<span>LINKED STORIES · {esc(group.get("league", ""))}</span>'
            f'<h2>{esc(group.get("title", ""))}</h2>'
            f'<p>{esc(group.get("description", ""))}</p>'
            f'<nav aria-label="이 주제의 다른 기사">{links}</nav></section>'
        )
    return ''


def index(catalog, by_key, esc, kind=''):
    rows = []
    for group in catalog.get('groups', []):
        if kind and group.get('kind') != kind:
            continue
        links = ''.join(
            f'<a href="{esc(by_key[m["file"][:-3]].url)}">'
            f'<span>{esc(m.get("role", ""))}</span>'
            f'<strong>{esc(m.get("label", ""))}</strong> ↗</a>'
            for m in group.get('items', []) if m.get('file', '')[:-3] in by_key
        )
        if not links:
            continue
        label = 'PREVIEW → REVIEW' if group.get('kind') == 'before-after' else 'INDEPENDENT STORIES'
        rows.append(
            f'<article class="editorial-links__group">'
            f'<span class="editorial-links__tag">{esc(group.get("league", ""))} · {label}</span>'
            f'<h3>{esc(group.get("title", ""))}</h3>'
            f'<p>{esc(group.get("description", ""))}</p>'
            f'<nav aria-label="{esc(group.get("title", ""))} 읽을거리">{links}</nav>'
            f'</article>'
        )
    if not rows:
        return ''
    return (
        '<section class="wrap editorial-links__index" aria-labelledby="editorialIndexTitle">'
        '<div class="editorial-links__heading"><span>KAIRO · LINKED EDITORIAL</span>'
        '<h2 id="editorialIndexTitle">같은 경기라도, 읽는 목적은 다릅니다.</h2>'
        '<p>경기 전 원문을 종료 뒤에 고쳐 쓰지 않습니다. 겹치는 주제는 연결하고, '
        '다른 관점은 독립 기사로 보존합니다.</p></div>'
        f'<div class="editorial-links__grid">{"".join(rows)}</div></section>'
    )
