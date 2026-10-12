#!/usr/bin/env python3
"""SFANDOM 정적 사이트 빌더 (외부 패키지 없음).

    python3 src/build.py

src/content/ 의 글(.md)·데이터(.json)·페이지 조각(.html)을 읽어 저장소 루트에
완성된 HTML·sitemap.xml·search-index.json 을 만듭니다. GitHub Pages는 결과물을 그대로 서비스합니다.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import pathlib
import re
import shutil
import sys
from urllib.parse import quote
import urllib.request
import xml.etree.ElementTree as ET

SRC = pathlib.Path(__file__).resolve().parent
ROOT = SRC.parent
CONTENT = SRC / 'content'
SITE = json.loads((SRC / 'site.json').read_text(encoding='utf-8'))
BASE = SITE['url'].rstrip('/')
TODAY = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
VER = TODAY.replace('-', '')

# 빌더가 만드는 최상위 경로 (다시 빌드할 때 지우고 새로 씀)
GENERATED_DIRS = ['news', 'special', 'mlb', 'kbo', 'nba', 'soccer', 'analysis', 'community', 'magazine',
                  'about', 'contact', 'sitemap', 'feed', 'weekly', 'privacy', 'terms', 'rules', 'legal', 'ads-cookies', 'search', 'games']

esc = lambda s: html.escape(str(s or ''), quote=True)

sys.dont_write_bytecode = True  # 빌드가 임시 파일(__pycache__)을 남기지 않게
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / 'tools'))
from fetch_logos import SOURCES as LOGO_SOURCES  # noqa: E402  (리그별 팀 ID · 공식 로고 주소)
import feeds  # noqa: E402  (RSS 피드 생성)
import weekly  # noqa: E402  (주간 인기 글 스냅샷)
from build_article_cards import card_name  # noqa: E402  (글별 공유 카드 파일명)
from editorial_paths import related as editorial_related, index as editorial_index
from naver_magazine import render as render_naver_magazine


# ───────────────────────── 콘텐츠 읽기 ─────────────────────────
class Article:
    def __init__(self, path: pathlib.Path):
        raw = path.read_text(encoding='utf-8')
        m = re.match(r'---\n(.*?)\n---\n(.*)', raw, re.S)
        if not m:
            raise SystemExit(f'front matter 없음: {path}')
        fm = {}
        for line in m.group(1).splitlines():
            if ':' not in line:
                continue
            k, v = line.split(':', 1)
            v = v.strip()
            try:
                fm[k.strip()] = json.loads(v)
            except json.JSONDecodeError:
                fm[k.strip()] = v
        self.__dict__.update(fm)
        self.file = path.name
        self.body = m.group(2).strip()
        self.kind = fm.get('kind', 'news')
        self.league = fm.get('league', 'MLB')
        self.sources = fm.get('sources', []) or []
        self.subtitle = fm.get('subtitle', '')
        self.url = ''

    @property
    def headline(self) -> str:
        return f'{self.title} {self.subtitle}'.strip()

    @property
    def excerpt(self) -> str:
        """카드용 본문 미리보기. 첫 문단들을 이어 약 280자까지 보여줍니다."""
        out = ''
        for block in self.body.split('\n\n'):
            if block.startswith(':::') or block.startswith('#'):
                continue
            out = (out + ' ' + re.sub(r'\s+', ' ', block).strip()).strip()
            if len(out) >= 280:
                break
        return out if len(out) <= 290 else out[:288].rstrip() + '…'

    @property
    def date_dot(self) -> str:
        return self.date.replace('-', '.')

    @property
    def section(self) -> str:
        return {'news': 'NEWS', 'analysis': 'ANALYSIS', 'magazine': 'MAGAZINE'}[self.kind]


def load_articles() -> list[Article]:
    arts = [Article(p) for p in sorted((CONTENT / 'articles').glob('*.md'))]
    used = set()
    for a in arts:
        y, mth, d = a.date.split('-')
        if a.kind == 'news':
            url = f'/news/{y}/{mth}/{a.slug}/'
            if url in used:
                url = f'/news/{y}/{mth}/{a.slug}-{d}/'
        elif a.kind == 'analysis':
            url = f'/analysis/{a.league.lower()}/{a.date}-{a.slug}/'
        else:
            url = f'/magazine/{a.slug}/'
            if url in used:
                url = f'/magazine/{a.slug}-{a.date}/'
        used.add(url)
        a.url = url
    # 같은 날짜 안에서는 파일 순서(뉴스 → 매거진 → 분석) 유지, 날짜는 최신순
    order = {'news': 0, 'magazine': 1, 'analysis': 2}
    arts.sort(key=lambda a: (a.date, getattr(a, 'priority', 0), a.league == 'NBA', -order[a.kind]), reverse=True)
    return arts


ARTICLES = load_articles()
EDITIONS = json.loads((CONTENT / 'editions.json').read_text(encoding='utf-8'))
PS = json.loads((CONTENT / 'postseason-2026.json').read_text(encoding='utf-8'))
NBA = json.loads((CONTENT / 'nba-2026.json').read_text(encoding='utf-8'))
RECORDS = json.loads((CONTENT / 'analysis-records.json').read_text(encoding='utf-8'))
BY_KEY = {a.file[:-3]: a for a in ARTICLES}
EDITORIAL_PATHS = json.loads((CONTENT / 'editorial-paths.json').read_text(encoding='utf-8'))


# ───────────────────────── 블로그 연동 (구글 · 네이버) ─────────────────────────
BLOG_CACHE = CONTENT / 'blog-feed.json'


def _strip(t: str) -> str:
    t = re.sub(r'<[^>]+>', ' ', html.unescape(t or ''))
    return re.sub(r'\s+', ' ', t).strip()


def _clip(t: str, n: int = 320) -> str:
    return t if len(t) <= n else t[:n - 1].rstrip() + '…'


def blog_img(u: str) -> str:
    """블로그 썸네일 주소를 카드에 맞는 크기로. 서버마다 받아 주는 크기가 달라 주소별로 나눠 처리한다."""
    if 'googleusercontent.com' in u or 'blogspot.com' in u:                          # 블로거: 가로 800px JPEG(-rj)
        u = re.sub(r'/[sw]\d+(?:-[a-z]+\d*)*/', '/w800-rj/', u)
        return re.sub(r'=[sw]\d+(?:-[a-z]+\d*)*$', '=w800-rj', u)
    if 'blogthumb.pstatic.net' in u:                                                 # 네이버 글 썸네일: 이 서버는 w2(가로 604px)까지만 준다
        return re.sub(r'type=[\w-]+', 'type=w2', u)
    if 'pstatic.net/image.nmv/' in u:                                                # 네이버 영상 장면: 16:9 가로 800px
        return re.sub(r'type=[\w-]+', 'type=w800', u)
    return re.sub(r'type=w\d+(?:-[a-z]+\d*)*', 'type=w773', u)                       # 그 밖의 네이버 이미지


def _img_bytes(u: str) -> int:
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 SFANDOM-build'})
    return len(urllib.request.urlopen(req, timeout=8).read())


def video_frame(u: str) -> str:
    """네이버 영상 썸네일의 첫 장면(_01)이 검은 화면이면 뒤 장면으로 바꾼다.
    검은 화면 JPEG는 2KB 안팎, 실제 장면은 30KB 이상이라 파일 크기로 가린다. 확인하지 못하면 그대로 둔다."""
    m = re.search(r'(pstatic\.net/image\.nmv/.+_)01(\.jpg)', u)
    if not m:
        return u
    small = lambda x: re.sub(r'type=[\w-]+', 'type=f480x480', x)
    try:
        if _img_bytes(small(u)) >= 6000:
            return u
        for n in ('03', '05', '02'):
            cand = u.replace(m.group(0), f'{m.group(1)}{n}{m.group(2)}')
            if _img_bytes(small(cand)) >= 6000:
                return cand
    except Exception:
        pass
    return u


# 홈 MAGAZINE에 올릴 글: NBA·MLB 글만 (다른 종목 글은 매거진 페이지에서 모두 보입니다)
CORE_RE = (r'NBA|MLB|NLDS|ALDS|NLCS|ALCS|World Series|Postseason|월드시리즈|포스트시즌|와일드카드|디비전시리즈|메이저리그|농구|야구'
           r'|Dodgers|Yankees|Padres|Brewers|Braves|Phillies|Cubs|Mets|Astros|Red Sox|White Sox|Blue Jays|Mariners|Guardians|Tigers|Rays|Orioles'
           r'|Lakers|Celtics|Knicks|Warriors|Thunder|Spurs|76ers|Nuggets|Bucks|Heat|Mavericks|Timberwolves|Cavaliers|Pistons|Rockets'
           r'|다저스|양키스|파드리스|브루어스|브레이브스|필리스|컵스|화이트삭스|레이커스|셀틱스|닉스|워리어스|썬더|스퍼스')


def is_core(p: dict) -> bool:
    return bool(re.search(CORE_RE, f"{p.get('title', '')} {p.get('summary', '')}", re.I))


def fetch_blog(key: str, conf: dict) -> list[dict]:
    """RSS/Atom 피드를 읽어 최신 글 목록을 돌려준다. 실패하면 예외."""
    req = urllib.request.Request(conf['feed'], headers={'User-Agent': 'Mozilla/5.0 SFANDOM-build'})
    root = ET.fromstring(urllib.request.urlopen(req, timeout=12).read())
    ns = {'a': 'http://www.w3.org/2005/Atom', 'media': 'http://search.yahoo.com/mrss/'}
    posts = []
    for it in root.iter('item'):                                   # RSS (네이버, 블로거 ?alt=rss)
        thumb = it.find('media:thumbnail', ns)
        desc = it.findtext('description') or ''
        img = re.search(r'<img[^>]+src="([^"]+)"', html.unescape(desc))
        posts.append({'title': _strip(it.findtext('title')), 'link': (it.findtext('link') or '').strip(),
                      'date': it.findtext('pubDate') or '', 'summary': _clip(_strip(desc)),
                      'image': thumb.get('url') if thumb is not None else (img.group(1) if img else '')})
    for it in root.findall('a:entry', ns):                          # Atom (블로거 기본)
        link = next((l.get('href') for l in it.findall('a:link', ns) if l.get('rel') == 'alternate'), '')
        thumb = it.find('media:thumbnail', ns)
        posts.append({'title': _strip(it.findtext('a:title', '', ns)), 'link': link, 'date': it.findtext('a:published', '', ns),
                      'summary': _clip(_strip(it.findtext('a:summary', '', ns) or it.findtext('a:content', '', ns))),
                      'image': thumb.get('url') if thumb is not None else ''})
    for p in posts:
        p['source'] = key
        p['link'] = re.sub(r'\?fromRss=.*$', '', p['link'])                      # 네이버 추적 파라미터 제거
        p['image'] = video_frame(blog_img(p.get('image') or ''))
        try:
            d = dt.datetime.strptime(p['date'][:25], '%a, %d %b %Y %H:%M:%S') if ',' in p['date'] else dt.datetime.fromisoformat(p['date'][:19])
            p['date'] = d.strftime('%Y-%m-%d')
        except ValueError:
            p['date'] = p['date'][:10]
    return posts[:12]


def load_blogs() -> dict:
    cache = json.loads(BLOG_CACHE.read_text(encoding='utf-8')) if BLOG_CACHE.exists() else {}
    for key, conf in SITE.get('blogs', {}).items():
        if not conf.get('feed'):
            continue
        try:
            cache[key] = fetch_blog(key, conf)
            print(f'blog {key}: {len(cache[key])} posts')
        except Exception as e:  # 네트워크가 막혀도 빌드는 계속, 지난번 캐시 사용
            print(f'blog {key}: 피드를 못 읽음 ({e.__class__.__name__}) — 캐시 사용')
    BLOG_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding='utf-8')
    return cache


BLOGS = load_blogs()


def blog_posts(limit: int = 6, core: bool = False) -> list[dict]:
    allp = [p for v in BLOGS.values() for p in v if not core or is_core(p)]
    return sorted(allp, key=lambda p: p.get('date', ''), reverse=True)[:limit]


def blog_card(p: dict) -> str:
    label = SITE['blogs'][p['source']]['label']
    img = f'<div class="thumb"><img src="{esc(blog_img(p["image"]))}" alt="" loading="lazy" referrerpolicy="no-referrer"></div>' if p.get('image') else '<div class="thumb blog-thumb" aria-hidden="true"><span>' + ('G' if p['source'] == 'google' else 'N') + '</span></div>'
    return (f'<a class="mag lift" data-date="{esc(p.get("date", ""))}" data-src="{p["source"]}" href="{esc(p["link"])}" target="_blank" rel="noopener">{img}<div class="body">'
            f'<span class="tag red">{label}</span><h3>{esc(p["title"])}</h3><p>{esc(_clip(p.get("summary", ""), 180))}</p>'
            f'<span class="tag">{p.get("date", "").replace("-", ".")} · 블로그에서 읽기 ↗</span></div></a>')


def blog_grid(limit: int, home: bool = False) -> str:
    """블로그 카드 격자. 빌드 때 받은 글(네이버·구글)을 먼저 그리고, 브라우저에서 구글 블로그 최신 글을 한 번 더 받아 합칩니다."""
    g = SITE['blogs'].get('google', {})
    cards = ''.join(blog_card(p) for p in blog_posts(limit, core=home))
    core = f' data-core="{esc(CORE_RE)}"' if home else ''
    return (f'<div class="card-grid blog-grid{" home" if home else ""}" data-blog-grid data-limit="{limit}"{core} data-blogger="{esc(g.get("url", ""))}" '
            f'data-label="{esc(g.get("label", "GOOGLE BLOG"))}">{cards}</div>'
            + ('' if cards else '<p class="muted blog-empty" style="font-size:14px">외부 연재 목록을 가져오지 못했습니다. 블로그 채널에서 확인해 주세요.</p>'))


def preserved_component(name: str) -> str:
    """Read approved markup from the permanent source tree."""
    path = CONTENT / 'components' / (name + '.html')
    return path.read_text(encoding='utf-8') if path.is_file() else ''

def page_fragment(name: str) -> tuple[str, str]:
    raw = (CONTENT / 'pages' / f'{name}.html').read_text(encoding='utf-8')
    m = re.match(r'<!-- lede: (.*?) -->\n', raw)
    lede = m.group(1) if m else ''
    body = raw[m.end():] if m else raw
    body = re.sub(r'<b>\d\d</b>', '', body)
    return lede, body


# ───────────────────────── 본문 마크다운 ─────────────────────────
def inline(s: str) -> str:
    s = esc(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*)\)', r'<a href="\2">\1</a>', s)
    return s


def render_body(a: Article, ad_after: int = 2) -> str:
    out, paras = [], 0
    for block in re.split(r'\n{2,}', a.body):
        b = block.strip()
        if not b:
            continue
        if b.startswith('::: stats'):
            rows = [r.split('|', 1) for r in b.splitlines()[1:-1] if '|' in r]
            cells = ''.join(f'<div class="stat"><b>{esc(v.strip())}</b><span>{esc(l.strip())}</span></div>' for v, l in rows)
            out.append(f'<div class="stats">{cells}</div>')
        elif b.startswith('::: angle'):
            label = b.splitlines()[0][9:].strip() or 'KAIRO ANGLE'
            text = ' '.join(b.splitlines()[1:-1])
            out.append(f'<aside class="angle" aria-label="{esc(label)}"><small>{esc(label)}</small><p>{inline(text)}</p></aside>')
        elif b.startswith('## '):
            out.append(f'<h2>{inline(b[3:])}</h2>')
        elif b.startswith('### '):
            out.append(f'<h3>{inline(b[4:])}</h3>')
        else:
            out.append(f'<p>{inline(" ".join(b.splitlines()))}</p>')
            paras += 1
            if paras == ad_after:
                out.append(ad('SF-ART-IN'))
    return '\n'.join(out)


# ───────────────────────── 조각 ─────────────────────────
def ad(slot_id: str, extra: str = '') -> str:
    slot = SITE['ads']['slots'][slot_id]
    return f'<div class="ad ad-{slot["size"]} {extra}" data-ad="{slot_id}" hidden></div>'


def ad_band(slot_id: str) -> str:
    return f'<div class="wrap ad-band">{ad(slot_id)}</div>'


def thumb(a: Article, cls: str = '') -> str:
    if not a.image:
        if 'SPOTLIGHT' in a.kicker:
            word = a.kicker.split('·')[-1]
        else:
            m = re.match(r"\s*(?:\d{4}\.\d\d\.\d\d KST · [\d:]+ )?([A-Z][A-Z .'-]*?)(?=\s*(?:\d|·|@|$))", a.meta or '')
            word = m.group(1).split()[-1] if m and m.group(1).split() else a.section
        word = re.sub(r'[^A-Z0-9 ]', '', word.upper()).strip() or a.league
        word = {'BAY': 'RAYS', 'MILWAUKEE': 'BREWERS', 'NEWS': a.league, 'ANALYSIS': a.league}.get(word, word)
        return f'<div class="thumb art-thumb {cls}" aria-hidden="true"><span class="k">{esc(a.league)} · {a.date_dot}</span><span class="w">{esc(word)}</span></div>'
    fallback_attr = ' onerror="this.onerror=null;this.src=\'/assets/teams/mlb/lad.svg\'"' if a.slug == 'dodgers-clinch-nlcs' else ''
    portrait = 'portrait' if 'headshot' in a.image else ''
    if getattr(a, 'photo_fallback', ''):
        fallback_attr = f' onerror="this.onerror=null;this.src=\'{esc(a.photo_fallback)}\'"'
    return (f'<div class="thumb {portrait} {cls}"><img src="{esc(a.image)}" alt="{esc(a.image_alt)}" '
            f'loading="lazy" decoding="async"{fallback_attr}></div>')




def home_news_thumb(a: Article, lead: bool = False) -> str:
    """Homepage NEWS thumbnails only: use relevant cached team SVGs, not generic league text."""
    if lead and a.slug == 'dodgers-clinch-nlcs':
        return ('<div class="thumb news-mark-thumb news-mark-lead" aria-hidden="true">'
                '<img src="/assets/teams/mlb/lad.svg?v=news-mark-20261010" alt="" loading="lazy" decoding="async">'
                '</div>')
    featured_teams = {
        'guardians-force-game4': ('mlb', ('CLE', 'CWS')),
        'nba-preseason-watch': ('nba', ('MIN', 'ORL', 'MIL', 'GSW')),
        'warriors-lakers-preseason-2026': ('nba', ('GSW', 'LAL')),
        '76ers-knicks-preseason-2026': ('nba', ('PHI', 'NYK')),
    }
    item = featured_teams.get(a.slug)
    if item:
        league, teams = item
        style = 'quad' if len(teams) == 4 else 'duo'
        marks = ''.join(badge(t, team_color(t, league), league=league) for t in teams)
        return f'<div class="thumb news-mark-thumb news-mark-mini {style}" aria-hidden="true">{marks}</div>'
    return thumb(a)




def badge(abbr: str, color: str, size: str = '', league: str = 'mlb') -> str:
    """팀 로고를 작게 표시. 저장소에 받아 둔 파일(assets/teams/<리그>/<약자>.svg)이 있으면 그것을, 없으면 리그 공식 주소를 씁니다.
    로고를 못 불러오면 site.js가 팀 색 약자 칩으로 바꿉니다."""
    f = ROOT / 'assets' / 'teams' / league / f'{abbr.lower()}.svg'
    if f.exists():
        src = f'/assets/teams/{league}/{abbr.lower()}.svg?v=all-team-marks-20261009'
    else:
        ids, pattern = LOGO_SOURCES[league]
        src = pattern.format(id=ids[abbr]) if abbr in ids else ''
    if not src:
        return f'<span class="tchip {size}" style="--c:{color}" title="{esc(abbr)}">{esc(abbr)}</span>'
    return (f'<span class="tlogo-wrap {size}" data-abbr="{esc(abbr)}" style="--c:{color}" title="{esc(abbr)}">'
            f'<img class="tlogo" src="{src}" alt="{esc(abbr)}" width="40" height="40" loading="lazy" decoding="async" referrerpolicy="no-referrer"></span>')


def team_color(abbr: str, league: str) -> str:
    if league.lower() == 'nba':
        return NBA['colors'].get(abbr, '#444')
    for d in PS['division']:
        if d['home'] == abbr:
            return d['home_color']
        if d['away'] == abbr:
            return d['away_color']
    return '#444'


def team_badge(a: Article, i: int, size: str = 'lg') -> str:
    """분석 글 머리말의 teams(원정, 홈 약자)로 팀 로고를 만듭니다. 없으면 빈 문자열."""
    teams = getattr(a, 'teams', None) or []
    if len(teams) != 2:
        return ''
    lg = a.league.lower()
    return badge(teams[i], team_color(teams[i], lg), size, league=lg if lg in LOGO_SOURCES else 'mlb')


def split_teams(a: Article) -> tuple[str, str]:
    t = re.split(r'\s+(?:at|vs\.?|@)\s+', a.title.rstrip('.'), maxsplit=1, flags=re.I)
    return (t[0], t[1]) if len(t) > 1 else (a.title.rstrip('.'), '')


def matchup_strip(a: Article) -> str:
    """분석 글 상단의 대진 표시 (팀 로고 + 팀 이름)."""
    if not getattr(a, 'teams', None):
        return ''
    left, right = split_teams(a)
    return (f'<div class="mc-stage in-article"><div class="mc-team">{team_badge(a, 0)}<small>AWAY</small><span class="display">{esc(left.upper())}</span></div>'
            f'<span class="mc-vs">VS</span><div class="mc-team r">{team_badge(a, 1)}<small>HOME</small><span class="display">{esc(right.upper())}</span></div></div>')


TODAY_PICKS: set = set()


def morning_edition_card(a: Article, wide: bool = False) -> str:
    """An editorial photo card linking to the actual article, without rewriting the original site layout."""
    extra = ''
    if a.slug == 'mls-weekend-watch':
        extra = '<p class="morning-fixtures">인터 마이애미–D.C. 유나이티드 · 뉴잉글랜드–시애틀 · LAFC–밴쿠버</p>'
    cells = getattr(a, 'brief', None) or {}
    insight = cells.get('key') or cells.get('view') or a.excerpt
    heading = '팬보드 전문 읽기' if a.kind == 'news' else '경기 분석 전문 읽기'
    photo = thumb(a)
    return (f'<article class="ta-card morning-card lift{" morning-wide" if wide else ""}">'
            f'<div class="morning-photo">{photo}</div>'
            f'<div class="morning-copy"><div class="ta-top"><span class="tag red">{esc(a.kicker or a.league)}</span>'
            f'<span class="tag">{esc(a.date_dot)}</span></div>'
            f'<h3>{esc(a.headline)}</h3>'
            f'<p>{esc(insight[:245])}</p>{extra}'
            f'<a class="ta-more" href="{a.url}">{heading} →</a></div></article>')


def today_analysis() -> str:
    """Show the actual latest approved morning edition, not three chronologically oldest articles."""
    global TODAY_PICKS
    ed_latest = max(EDITIONS)
    keys = EDITIONS[ed_latest].get('items', [])
    picks = [BY_KEY[k] for k in keys if k in BY_KEY]
    if not picks:
        picks = sorted([a for a in ARTICLES if a.kind == 'analysis'],
                       key=lambda a: (a.date, getattr(a, 'priority', 0)), reverse=True)[:3]
    TODAY_PICKS = {a.url for a in picks if a.kind == 'analysis'}
    feature_count = len(picks)
    cards = ''.join(morning_edition_card(a, wide=(i == feature_count - 1 and feature_count % 2 == 1))
                    for i, a in enumerate(picks))
    return (f'<section class="wrap sec" id="today-analysis" aria-labelledby="taTitle">'
            f'<div class="sec-head"><h2 class="sec-title" id="taTitle">'
            f'SFANDOM &amp; KAIRO <span class="outline">ANALYSIS</span> '
            f'<span class="kr">{ed_latest.replace("-", ".")} 선정 콘텐츠 {feature_count}편</span></h2>'
            f'<a class="more" href="/news/morning/{ed_latest}/">오늘 에디션 전체 →</a></div>'
            f'<div class="ta-grid morning-feature-grid">{cards}</div>'
            f'<div class="ta-foot"><a class="review-link" href="/analysis/review/">'
            f'<span class="display" style="font-size:24px">REVIEW <span class="accent">/</span> 복기 리포트</span>'
            f'<span class="muted" style="font-size:14px">경기 결과와 분석 과정을 비교합니다</span></a>'
            f'<a class="review-link" href="/news/morning/{ed_latest}/">'
            f'<span class="display" style="font-size:24px">MORNING EDITION</span>'
            f'<span class="muted" style="font-size:14px">오늘 5편 · 사진과 분석 전체 읽기 →</span>'
            f'</a></div></section>')

def talk_icon() -> str:
    return ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linejoin="round" aria-hidden="true"><path d="M4 5h16v11H9l-5 4z"/></svg>')


def list_item(a: Article, h: str = 'h2') -> str:
    return (f'<a class="li" href="{a.url}">{thumb(a)}<div><span class="tag red">{esc(a.section)} · {esc(a.league)}</span>'
            f'<{h}>{esc(a.headline)}</{h}><p>{esc(a.excerpt)}</p>'
            f'<span class="foot"><time datetime="{a.date}">{a.date_dot}</time><span class="talk">{talk_icon()}토론</span></span></div></a>')


def mag_card(a: Article) -> str:
    return (f'<a class="mag lift" href="{a.url}">{thumb(a)}<div class="body"><span class="tag red">{esc(a.kicker or a.section)}</span>'
            f'<h3>{esc(a.headline)}</h3><p>{esc(a.excerpt)}</p><span class="tag">{a.date_dot}</span></div></a>')


def crumbs(items: list[tuple[str, str]]) -> str:
    parts = ['<a href="/">HOME</a>']
    for label, url in items:
        parts.append('<span aria-hidden="true">/</span>')
        parts.append(f'<a href="{url}">{esc(label)}</a>' if url else f'<span>{esc(label)}</span>')
    return f'<nav class="crumbs" aria-label="현재 위치">{"".join(parts)}</nav>'


def breadcrumb_ld(items: list[tuple[str, str]]) -> dict:
    lst = [{'@type': 'ListItem', 'position': 1, 'name': 'HOME', 'item': BASE + '/'}]
    for i, (label, url) in enumerate(items, start=2):
        e = {'@type': 'ListItem', 'position': i, 'name': label}
        if url:
            e['item'] = BASE + url
        lst.append(e)
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': lst}


NAV = [('NEWS', '/news/'), ('NBA', '/nba/'), ('MLB', '/mlb/'), ('ANALYSIS', '/analysis/'),
       ('MAGAZINE', '/magazine/'), ('FAN BOARD', '/community/')]
CUR = ' aria-current="page"'
EXT = ' target="_blank" rel="noopener"'
HOT = ' class="hot"'


def header(active: str) -> str:
    nav = ''.join(
        f'<a href="{u}"{CUR if active == u else ""}{HOT if l == "NBA" and active != u else ""}>{l}</a>'
        for l, u in NAV)
    return f'''<a class="skip" href="#main">본문 바로가기</a>
<header class="site-header">
  <div class="wrap header-in">
    <a class="logo" href="/" aria-label="SFANDOM 홈"><img src="/assets/brand/sfandom-logo.svg" alt="SFANDOM" width="183" height="46"></a>
    <span class="motto">{esc(SITE['motto'])}</span>
    <span class="mini-social"><a href="https://www.instagram.com/sportsfandom/" target="_blank" rel="noopener" aria-label="인스타그램 @sportsfandom"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg></a><a href="https://www.threads.com/@sportsfandom" target="_blank" rel="noopener" aria-label="스레드 @sportsfandom"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-4 8"/></svg></a></span>
    <nav class="nav" aria-label="주 메뉴">{nav}</nav>
    <span class="spacer"></span>
    <button type="button" class="icon-btn" id="searchBtn" aria-label="검색" aria-controls="searchBar" aria-expanded="false"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg></button>
    <a class="all-btn" href="/sitemap/"{CUR if active == "/sitemap/" else ""}>SITEMAP</a>
  </div>
  <div class="search-bar" id="searchBar" data-panel hidden><div class="wrap"><form action="/search/" role="search"><label class="sr-only" for="q">사이트 검색</label><input id="q" name="q" type="search" placeholder="팀, 선수, 경기로 찾기" autocomplete="off"><button class="pill" type="submit">검색</button></form></div></div>
</header>'''


def footer() -> str:
    weekly_link = '<a href="/weekly/">주간 베스트</a>' if WEEKLY_DIR.exists() and any(WEEKLY_DIR.glob('*.json')) else ''
    socials = ''.join(f'<a href="{s["url"]}" target="_blank" rel="noopener">{s["label"]}</a>' for s in SITE['socials'])
    return f'''<footer class="site-footer">
  <div class="wrap">
    <div class="footer-in">
      <div><a class="logo" href="/" aria-label="SFANDOM 홈"><img src="/assets/brand/sfandom-logo.svg" alt="SFANDOM" width="223" height="56" loading="lazy"></a>
        <p>{esc(SITE['motto'])} — <a href="/contact/">문의하기</a></p>
        <p>SFANDOM은 스포츠 정보와 팬 토론을 위한 미디어입니다. 금전이 걸린 게임을 운영·중개하지 않습니다.</p></div>
      <div class="footer-right">
        <div class="socials">{socials}</div>
        <nav class="footer-links" aria-label="하단 메뉴"><a href="/about/">소개</a><a href="/contact/">문의</a><a href="/privacy/">개인정보처리방침</a><a href="/ads-cookies/">광고·쿠키 고지</a><a href="/terms/">이용약관</a>{weekly_link}<a href="/feed/" class="footer-subscribe"><span aria-hidden="true">🔔</span> 내 팀 구독</a><a href="/rules/">커뮤니티 규칙</a><a href="/legal/">법률고지</a></nav>
      </div>
    </div>
    <div class="copy"><span>© 2026 SFANDOM. ALL RIGHTS RESERVED.</span><span>기록 출처 · 각 리그·구단 공식 자료</span></div>
  </div>
</footer>'''


def layout(title: str, body: str, *, path: str, description: str = '', image: str = '', ld: list | None = None,
           noindex: bool = False, active: str = '', og_type: str = 'website', ads: bool = False) -> str:
    full_title = title if title.startswith('SFANDOM') else f'{title} | SFANDOM'
    desc = description or SITE['description']
    img = image or f'{BASE}/assets/share/sfandom-social-20261010.png'
    if img.startswith('/'):
        img = f'{BASE}{img}'  # SNS crawlers need an absolute image URL.
    social_card = img.startswith(f'{BASE}/assets/share/')  # 대표 카드 · 글별 카드 모두 1200x630 PNG
    image_hints = (
        '<meta property="og:image:type" content="image/png">\n'
        '<meta property="og:image:width" content="1200">\n'
        '<meta property="og:image:height" content="630">\n'
        if social_card else ''
    )
    cfg = {'root': '/', 'ads': {k: SITE['ads'][k] for k in ('client', 'phase')} | {
        'slots': {k: {kk: v[kk] for kk in ('phase', 'unit', 'format', 'layout') if kk in v} for k, v in SITE['ads']['slots'].items()}},
        'supabase': SITE['supabase']}
    lds = ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in (ld or []))
    robots = 'noindex,follow' if noindex else 'index,follow,max-image-preview:large'
    # 광고 스크립트는 본문이 충분한 글 상세 페이지에만 싣는다. 목록·허브·검색·404·안내·커뮤니티 화면에는 싣지 않는다.
    ad_script = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={SITE["ads"]["client"]}" crossorigin="anonymous"></script>\n'
                 if ads and not noindex else '')
    thread_css = (f'<link rel="stylesheet" href="/assets/css/community-thread.css?v={VER}-v2">'
                  f'<link rel="stylesheet" href="/assets/css/community-admin.css?v={VER}-v1">' if path == '/community/' else '')
    news_comments_css = (f'<link rel="stylesheet" href="/assets/css/news-comments.css?v={VER}-v1">' if re.fullmatch(r'/news/\d{4}/\d{2}/[a-z0-9-]+/', path) else '')
    thread_js = (f'<script src="/assets/js/community-thread.js?v={VER}-v5" defer></script>'
                 f'<script src="/assets/js/community-admin.js?v={VER}-v1" defer></script>' if path == '/community/' else '')
    news_comments_js = (f'<script src="/assets/js/news-comments.js?v={VER}-v1" defer></script>' if re.fullmatch(r'/news/\d{4}/\d{2}/[a-z0-9-]+/', path) else '')
    return f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="{robots}">
<meta name="google-adsense-account" content="{SITE['ads']['client']}">
<meta name="theme-color" content="#0B0B0F">
<link rel="canonical" href="{BASE}{path}">
<link rel="alternate" type="application/rss+xml" title="SFANDOM 전체 소식" href="{BASE}/feed/all.xml">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="SFANDOM">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{BASE}{path}">
<meta property="og:image" content="{esc(img)}">
<meta property="og:image:secure_url" content="{esc(img)}">
{image_hints}<meta property="og:image:alt" content="{esc('SFANDOM & KAIRO 스포츠 팬 커뮤니티' if img.endswith('sfandom-social-20261010.png') else full_title)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{esc(img)}">
<meta name="twitter:title" content="{esc(full_title)}">
<meta name="twitter:description" content="{esc(desc)}">
<link rel="icon" type="image/svg+xml" href="/assets/brand/sfandom-mark.svg">
<link rel="icon" type="image/png" sizes="512x512" href="/assets/brand/sfandom-mark-512.png">
<link rel="apple-touch-icon" href="/assets/brand/sfandom-mark-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Black+Han+Sans&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/assets/css/site.css?v={VER}-desktop-wide-1680-v1">
{('<link rel="stylesheet" href="/assets/css/brand-story.css?v=20261012-site01">' if path == '/' else '')}
{('<link rel="stylesheet" href="/assets/css/naver-magazine.css?v=20261012-restored-thumbnails">' if path == '/magazine/' else '')}
{('<link rel="stylesheet" href="/assets/css/game-center.css?v=20261012-site03">' if path in ('/', '/games/') else '')}
{('<link rel="stylesheet" href="/assets/css/analysis-cycle.css?v=20261012-site04">' if path in ('/analysis/', '/analysis/review/', '/analysis/mlb/2026-10-11-nlcs-dodgers-brewers-game1/') else '')}
{('<link rel="stylesheet" href="/assets/css/editorial-links.css?v=20261012-site04-map">' if path.startswith(('/analysis/', '/news/', '/magazine/')) else '')}
{thread_css}{news_comments_css}
{ad_script}<script>window.SFANDOM={json.dumps(cfg, ensure_ascii=False)};</script>
{lds}
</head>
<body>
{header(active)}
<main id="main">
{body}
</main>
{footer()}
<script src="/assets/js/site.js?v={VER}-sound3-board1" defer></script>
{thread_js}{news_comments_js}
</body>
</html>
'''


# ───────────────────────── 출력 ─────────────────────────
PAGES: list[dict] = []   # sitemap / search 용


def write(url: str, html_text: str, *, index: bool = True, lastmod: str = TODAY, search: dict | None = None):
    target = ROOT / url.lstrip('/') / 'index.html' if url.endswith('/') else ROOT / url.lstrip('/')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html_text, encoding='utf-8')
    if index:
        PAGES.append({'url': url, 'lastmod': lastmod})
    if search:
        SEARCH.append(search)


SEARCH: list[dict] = []


def org_ld() -> dict:
    return {'@context': 'https://schema.org', '@graph': [
        {'@type': 'Organization', '@id': f'{BASE}/#organization', 'name': 'SFANDOM', 'alternateName': '스팬덤', 'url': BASE + '/',
         'logo': {'@type': 'ImageObject', 'url': f'{BASE}/assets/brand/sfandom-mark-512.png'},
         'sameAs': [s['url'] for s in SITE['socials']]},
        {'@type': 'WebSite', '@id': f'{BASE}/#website', 'url': BASE + '/', 'name': 'SFANDOM', 'inLanguage': 'ko-KR',
         'publisher': {'@id': f'{BASE}/#organization'},
         'potentialAction': {'@type': 'SearchAction', 'target': f'{BASE}/search/?q={{q}}', 'query-input': 'required name=q'}}]}


# ───────────────────────── 팬 보드 공통 조각 ─────────────────────────
CHANNELS = ['NBA', 'MLB', 'NEWS', '분석 토론', '직관 후기', '자유']   # 글 제목 앞 [채널] 머리말로 구분 (게시판 저장소는 그대로)
QUICK_TAG = '한줄'


def channel_chips() -> str:
    chips = '<a href="/community/" data-ch="">전체</a>' + ''.join(f'<a href="/community/?ch={quote(c)}" data-ch="{esc(c)}">{esc(c)}</a>' for c in CHANNELS)
    return f'<nav class="chips" aria-label="채널" data-chips>{chips}</nav>'


def game_threads(limit: int = 7) -> str:
    """경기 스레드: NBA 예정 경기와 MLB 챔피언십시리즈를 연결합니다."""
    rows = []
    for g in [x for x in nba_home_games() if not x.get('result')][:3]:
        tag = f'{g["away"]}@{g["home"]}'
        rows.append((f'NBA · {g["day"]}', badge(g["away"], NBA["colors"].get(g["away"], "#444"), league="nba") + '<i class="thread-vs">VS</i>' + badge(g["home"], NBA["colors"].get(g["home"], "#444"), league="nba"), tag, g['kst']))
    for d in PS.get('lcs', []):
        tag = f'{d["away"]}@{d["home"]}'
        rows.append((f'{d["league"]}CS', badge(d["away"], d["away_color"]) + '<i class="thread-vs">VS</i>' + badge(d["home"], d["home_color"]), tag, '챔피언십시리즈'))
    out = ''.join(f'<a class="gt" href="/community/?thread={quote(tag)}"><span><small>{esc(k)} · {esc(when)}</small><b class="vsline">{logos}</b></span><span class="gt-in"><span class="gt-dot"></span>입장</span></a>' for k, logos, tag, when in rows[:limit])
    return f'<div class="box"><span class="box-title">GAME THREADS · 경기 스레드</span>{out}</div>'


def quick_box(size: int = 4) -> str:
    return (f'<div class="box quick" data-quick data-size="{size}"><div class="quick-head"><span class="display" style="font-size:26px">QUICK TALK</span><span class="muted" style="font-size:12px">한 줄로 가볍게</span></div>'
            f'<form class="quick-form" data-quick-form novalidate><label class="sr-only" for="qt">지금 경기 한 줄 평 (최대 60자)</label>'
            f'<input id="qt" name="text" type="text" maxlength="60" placeholder="예: 1쿼터부터 분위기 좋네요" autocomplete="off">'
            f'<label class="hp" aria-hidden="true">website<input name="website" tabindex="-1" autocomplete="off"></label><button class="pill" type="submit">등록</button></form>'
            f'<p class="status" data-quick-status role="status"></p><div class="quick-list" data-quick-list><div class="empty">경기를 보며 떠오른 생각을 한 줄로 남겨 보세요.</div></div></div>')


def message_box() -> str:
    """홈의 'SFANDOM과 대화하기' 쪽지 칸. 문의 페이지와 같은 쪽지함(드라이브 시트)으로 들어갑니다."""
    ep = (SITE.get('contact') or {}).get('endpoint', '')
    if not ep:
        return ''
    return (f'<section class="wrap sec" id="message" aria-labelledby="msgTitle"><form class="composer msg-box" data-message data-endpoint="{esc(ep)}" novalidate>'
            f'<div class="msg-head"><h2 class="display" id="msgTitle">MESSAGE</h2><span class="kr">SFANDOM과 대화하기</span></div>'
            f'<p class="muted" style="margin:0">제보, 제안, 문의 모두 좋아요. 운영자에게 바로 전달됩니다.</p>'
            f'<div class="msg-row"><div><label class="sr-only" for="msgNick">닉네임</label><input id="msgNick" name="name" type="text" maxlength="40" placeholder="닉네임 (선택)"></div>'
            f'<div><label class="sr-only" for="msgMail">답장 받을 이메일</label><input id="msgMail" name="reply" type="email" maxlength="120" placeholder="답장 받을 이메일 (선택)" autocomplete="email"></div></div>'
            f'<label class="sr-only" for="msgBody">쪽지 내용</label><textarea id="msgBody" name="body" maxlength="1000" required placeholder="하고 싶은 이야기를 적어주세요 (최대 1,000자)"></textarea>'
            f'<label class="hp" aria-hidden="true">website<input name="website" tabindex="-1" autocomplete="off"></label>'
            f'<div class="composer-foot"><span class="status" data-message-status role="status" aria-live="polite">보낸 내용은 운영자만 볼 수 있습니다. 이메일은 답장이 필요할 때만 적어주세요. <a href="/privacy/" class="accent">개인정보처리방침</a></span>'
            f'<button class="pill" type="submit">쪽지 보내기</button></div></form></section>')


# ───────────────────────── 홈 ─────────────────────────
def build_home():
    news = [a for a in ARTICLES if a.kind == 'news']
    analysis = [a for a in ARTICLES if a.kind == 'analysis']
    hero = SITE['hero']
    g = BLOGS.get('google') or []
    hero_title = '<br>'.join(esc(x) for x in hero['title'].split('\n'))
    hero_text, hero_link = hero['text'], hero.get('link', '')
    if hero.get('use_latest_google_post') and g:
        hero_title, hero_text, hero_link = esc(g[0]['title']), g[0]['summary'], g[0]['link']
    cv = SITE.get('community_video') or {}
    if cv.get('instagram_reel'):
        r = cv['instagram_reel']
        fb = (f'<video class="reel-fallback" muted loop playsinline preload="none" hidden data-src="{esc(cv["fallback_video"])}"'
              f'{(" poster=" + chr(34) + esc(cv["fallback_poster"]) + chr(34)) if cv.get("fallback_poster") else ""}></video>') if cv.get('fallback_video') else ''
        nba_media = (f'<div class="reel-fill" data-reel style="aspect-ratio:{esc(cv.get("reel_ratio", "9/16"))}"><iframe src="https://www.instagram.com/reel/{esc(r)}/embed/" title="SFANDOM 인스타그램 릴스" '
                     f'loading="lazy" scrolling="no" allowtransparency="true" allow="autoplay; encrypted-media; picture-in-picture; fullscreen"></iframe>{fb}</div>')
    else:
        nba_media = ''
    nba_band = (f'<div class="nba-band{" fill" if "reel-fill" in nba_media else ""}">{nba_media}'
                f'<div class="nba-copy"><span class="tag red">{esc(cv.get("eyebrow", ""))}</span><h3 class="display">{esc(cv.get("title", ""))}<br><span class="outline">{esc(cv.get("title2", ""))}</span></h3>'
                f'<p>{esc(cv.get("text", ""))}</p><div style="display:flex;gap:10px;flex-wrap:wrap"><a class="pill" href="/community/#write">팬 보드에서 얘기하기</a></div></div></div>') if nba_media else ''
    v = hero.get('video') or {}
    reel_tag = ''
    art = f'<div class="hero-art" aria-hidden="true"><span>{esc(hero.get("art", ""))}</span></div>'
    if hero.get('image'):
        media = f'<img src="{esc(hero["image"])}" alt="{esc(hero["alt"])}" fetchpriority="high">'
    elif v:
        poster = f' poster="{esc(v["poster"])}"' if v.get('poster') else ''
        media = '<div class="hero-art" aria-hidden="true"></div>' + (f'<video class="hero-video" muted autoplay loop playsinline preload="metadata"{poster} aria-label="{esc(v.get("label", ""))}"'
                       f' data-src="{esc(v.get("src", ""))}"></video>')
    else:
        media = art
    credit = f'<span class="hero-credit">{esc(hero["credit"])}</span>' if hero.get('credit') else ''
    home_preseason = nba_home_preseason()
    home_games = nba_home_games()
    home_heading = 'PRESEASON' if home_preseason else 'TIP-OFF'
    home_status = (f'{sum(bool(g.get("result")) for g in home_games[:5])} FINAL · NEXT' if home_preseason else nba_dday())
    home_cta = '프리시즌 일정' if home_preseason else '개막 주간 일정'
    home_aria = 'NBA 프리시즌' if home_preseason else 'NBA 개막 주간'
    tip = ''.join(nba_home_story(g) for g in home_games[:5])
    lead, rest = news[0], news[1:5]
    nl = ''.join(f'<a class="nl" href="{a.url}">{home_news_thumb(a)}<span class="t"><span class="tag">{esc(a.league)} · {a.date_dot}</span><strong>{esc(a.headline)}</strong></span><span class="talk">{talk_icon()}토론</span></a>' for a in rest)
    lcs_cards = ''.join(lcs_card(d) for d in PS.get('lcs', []))
    ta_html = today_analysis()
    shown = TODAY_PICKS
    gt = lambda a: (re.match(r'[\d.]+ [\d:]+', a.meta or '') or re.match('', '')).group(0) or '9999'
    upcoming = sorted([x for x in analysis if getattr(x, 'brief', None) and x.url not in shown], key=gt)
    minis = ''.join(f'<a class="mini lift" href="{a.url}"><span class="tag">{esc(a.league)} · {a.date_dot}</span><span class="display">{esc(a.title.rstrip(".,"))}</span><strong>{esc(a.subtitle)}</strong></a>' for a in (upcoming or [x for x in analysis if x.url not in shown])[:3])
    ed_latest = max(EDITIONS)
    body = f'''
{ad_band('SF-HOME-TOP')}
<section class="hero" aria-labelledby="heroTitle">
  <div class="hero-media">{media}</div>
  <div class="hero-shade" aria-hidden="true"></div>
  <article class="hero-copy">
    <span class="hero-badge">{esc(hero.get("badge_en", "HOT ISSUE"))}<b>{esc(hero.get("badge_kr", ""))}</b></span>
    <h1 id="heroTitle">{hero_title}</h1>
    <p>{esc(hero_text)}</p>
    <div style="display:flex;gap:10px;flex-wrap:wrap"><a class="pill white" href="{esc(hero_link or '/nba/')}" style="height:54px;padding:0 28px">{'오늘 특집 읽기' if hero_link else home_cta}</a><a class="pill ghost" href="/community/#write" style="height:54px;padding:0 28px">팬 보드에서 얘기하기</a></div>
  </article>
  {credit}{reel_tag}
  <aside class="top-stories" aria-label="{home_aria}"><h2>{home_heading} <span class="nba-dday">{home_status}</span></h2>{tip}</aside>
</section>

{preserved_component('home-brand-story')}

{game_preview()}

{ta_html}

{nba_section()}

<section class="wrap sec" aria-labelledby="newsTitle">
  <div class="sec-head"><h2 class="sec-title" id="newsTitle">NEWS<span class="accent">.</span> <span class="kr">읽고, 바로 토론</span></h2><a class="more" href="/news/">뉴스 전체 →</a></div>
  <div class="news-grid">
    <a class="news-lead lift" href="{lead.url}">{home_news_thumb(lead, lead=True)}<div class="body"><span class="tag red">LEAD · {esc(lead.league)} · {lead.date_dot}</span><h3>{esc(lead.headline)}</h3><p>{esc(lead.excerpt)}</p><span class="talk">{talk_icon()}이 뉴스 토론하기</span></div></a>
    <div class="news-list">{nl}</div>
  </div>
</section>

<section class="wrap sec" aria-labelledby="fanTitle">
  <div class="sec-head"><h2 class="sec-title" id="fanTitle">FAN ZONE<span class="accent">.</span> <span class="kr">먼저 놀고</span></h2><a class="pill" href="/community/#write">+ 글쓰기</a></div>
  {nba_band}
  {channel_chips()}
  <div class="fan-grid">
    <aside class="fan-side">
      {quick_box(4)}
      <div class="box"><span class="box-title">HOUSE RULES</span><ul class="rules"><li>욕설 · 비하 금지</li><li>도배 · 광고 링크 금지</li><li>불법 도박 사이트 홍보 금지</li><li>개인정보 올리지 않기</li></ul><a class="more" href="/rules/">커뮤니티 규칙 →</a></div>
    </aside>
    <div class="fan-main" data-board data-size="5">
      <div class="sec-head" style="margin:0"><span class="box-title">NEW POSTS · 최신 글</span><a class="more accent" href="/community/">전체 글 보기 →</a></div>
      <div data-board-list><div class="empty">스포츠 팬들의 경기·선수 토론을 확인할 수 있습니다. <a href="/community/">팬 보드에서 최신 글 보기 →</a></div></div>
      <a class="fan-write" href="/community/#write"><span class="fan-write-ph">오늘 경기, 무슨 얘기 하고 싶어요?</span><span class="pill">글쓰기</span></a>
    </div>
    <aside class="fan-side">
      {game_threads()}
    </aside>
  </div>
</section>

<section class="wrap feed-home-wrap" aria-label="내 팀 소식 구독">
  <a class="feed-home-banner" href="/feed/">
    <span class="feed-home-icon" aria-hidden="true">🔔</span>
    <span class="feed-home-copy"><strong>MY TEAM <span>내 팀 소식 받기</span></strong><small>다저스부터 워리어스까지, 내가 좋아하는 팀의 새 글만 모아봐요.</small></span>
    <span class="feed-home-arrow" aria-hidden="true">→</span>
  </a>
</section>

<section class="wrap sec" id="lcs" aria-labelledby="dsTitle">
  <div class="sec-head"><h2 class="sec-title" id="dsTitle">MLB <span class="outline">POSTSEASON</span> <span class="kr">챔피언십시리즈</span></h2><a class="more" href="/special/postseason-2026/">대진표 · 전체 일정 →</a></div>
  <div class="grid-4" style="grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))">{lcs_cards}</div>
</section>

<section class="wrap sec split-8-4" aria-labelledby="anTitle">
  <div class="main">
    <div class="sec-head" style="margin:0"><h2 class="sec-title" id="anTitle">MORE ANALYSIS<span class="accent">.</span> <span class="kr">KAIRO · 이어지는 경기 프리뷰</span></h2><a class="more" href="/analysis/">분석 전체 →</a></div>
    <div class="grid-3">{minis}</div>
    {ad('SF-HOME-FEED')}
  </div>
  <aside class="side">
    <div class="sticky-rail">{ad('SF-HOME-RAIL')}</div>
    <div class="box"><span class="display" style="font-size:30px">MORNING EDITION</span><p style="margin:0;color:var(--text-3)">어제 경기에서 오늘 남는 것만. 최신호 {ed_latest.replace("-", ".")}</p><a class="pill" href="/news/morning/{ed_latest}/">최신호 읽기</a></div>
  </aside>
</section>

{ad_band('SF-HOME-MID')}

<section class="wrap sec" aria-labelledby="magTitle">
  <div class="sec-head"><h2 class="sec-title" id="magTitle">MAGAZINE<span class="accent">.</span></h2><a class="more" href="/magazine/">매거진 전체 →</a></div>
  {blog_grid(3, home=True)}
</section>


{message_box()}

<section class="wrap"><div class="edition-band"><div><h2>MORNING EDITION</h2><p>어제 경기 요약과 오늘의 분석 경기를 매일 아침 SFANDOM에서.</p></div><div style="display:flex;gap:10px;flex-wrap:wrap"><a class="pill" href="/news/morning/">지난 에디션</a><a class="pill ghost" href="{SITE['socials'][0]['url']}" target="_blank" rel="noopener">인스타그램 팔로우</a></div></div></section>
{ad_band('SF-HOME-BTM')}
'''
    write('/', layout('SFANDOM | Play First. Analysis Next. — 스포츠 팬 커뮤니티', body, path='/', ld=[org_ld()], active='/'))


# ───────────────────────── 글 상세 ─────────────────────────
def related(a: Article, n: int = 5) -> list[Article]:
    same = [x for x in ARTICLES if x is not a and x.edition == a.edition]
    others = [x for x in ARTICLES if x is not a and x not in same]
    return (same + others)[:n]


def build_article(a: Article):
    section_url = {'news': '/news/', 'analysis': '/analysis/', 'magazine': '/magazine/'}[a.kind]
    trail = [(a.section, section_url)]
    if a.kind == 'analysis':
        trail.append((a.league, f'/analysis/{a.league.lower()}/' if a.league.lower() in ('mlb', 'nba') else ''))
    trail.append((a.title.rstrip(',.'), ''))
    fig = ''
    if a.image:
        logo = 'logo' if a.image.endswith('.svg') or 'logo' in a.image else ''
        photo_source = getattr(a, 'photo_source', '')
        photo_license = getattr(a, 'photo_license', '')
        photo_license_url = getattr(a, 'photo_license_url', '')
        cap_txt = esc(a.credit) if a.credit.startswith('PHOTO') else esc(a.image_alt)
        if photo_source:
            cap_txt += f' · <a href="{esc(photo_source)}" target="_blank" rel="noopener noreferrer">원본 사진</a>'
        if photo_license and photo_license_url:
            cap_txt += f' · <a href="{esc(photo_license_url)}" target="_blank" rel="noopener noreferrer">{esc(photo_license)}</a>'
        cap = f'<figcaption>{cap_txt}</figcaption>'
        feature = ' dodgers-feature' if a.slug == 'dodgers-clinch-nlcs' else ''
        fallback_attr = ' onerror="this.onerror=null;this.src=\'/assets/teams/mlb/lad.svg\'"' if feature else ''
        if getattr(a, 'photo_fallback', ''):
            fallback_attr = f' onerror="this.onerror=null;this.src=\'{esc(a.photo_fallback)}\'"'
        fallback = '<div class="feature-fallback">DODGERS · NLCS</div>' if feature else ''
        fig = f'<figure class="figure {logo}{feature}"><img src="{esc(a.image)}" alt="{esc(a.image_alt)}" fetchpriority="high"{fallback_attr}>{fallback}{cap}</figure>'
    srcs = ''.join(f'<span>{esc(s["label"])}</span>' for s in a.sources if s.get('label'))
    src_html = f'<div class="sources"><strong>출처</strong>{srcs}</div>' if srcs else ''
    credit = f'<p class="credit">{esc(a.credit)}</p>' if a.credit and not a.credit.startswith('PHOTO') else ''
    rel = ''.join(f'<a href="{x.url}"><small>{esc(x.section)} · {x.date_dot}</small>{esc(x.headline)}</a>' for x in related(a))
    ed = f'<a class="more" href="/news/morning/{a.edition}/">{a.edition.replace("-", ".")} 모닝 에디션 전체 →</a>' if a.edition in EDITIONS else ''
    topic = quote(f'[토론] {a.title.rstrip(",.")}')
    if a.kind == 'news':
        discussion_html = f'''<section class="news-comment-box" data-news-comments data-article-path="{esc(a.url)}" aria-label="뉴스 의견">
          <h2>이 뉴스 이야기하기</h2>
          <p class="nc-intro">이 기사에 남긴 댓글은 FAN BOARD의 전체 이야기에도 함께 표시됩니다.</p>
          <div data-news-comment-list><p class="news-comment-empty">댓글을 불러오는 중…</p></div>
          <form data-news-comment-form novalidate>
            <input name="nickname" maxlength="30" placeholder="닉네임 (선택)" aria-label="닉네임">
            <textarea name="body" maxlength="2000" required aria-label="댓글 내용" placeholder="이 경기에 대한 생각을 남겨 주세요."></textarea>
            <label class="hp" aria-hidden="true">website<input name="website" tabindex="-1" autocomplete="off"></label>
            <div class="nc-actions"><button class="pill" type="submit">댓글 등록</button><a class="more" href="/community/" data-news-comment-link hidden>전체 이야기에서 보기 →</a></div>
            <p class="nc-status" data-news-comment-status role="status"></p>
          </form>
        </section>'''
    else:
        discussion_html = f'''<section class="discuss" aria-label="토론"><div><h2>이 글 토론하기</h2><p>생각이 다르면 더 좋습니다. 팬 보드에 한 줄 남겨 주세요.</p></div><a class="pill" href="/community/?topic={topic}#write">{talk_icon()}팬 보드에 글쓰기</a></section>'''
    body = f'''
{ad_band('SF-ART-TOP')}
<div class="wrap">
  <header class="article-head">
    {crumbs(trail)}
    <div class="kick"><span class="chip">{esc(a.section)} · {esc(a.league)}</span><span class="tag">{esc(a.kicker)}</span></div>
    <h1>{esc(a.title)}</h1>
    {f'<p class="sub">{esc(a.subtitle)}</p>' if a.subtitle else ''}
    <div class="byline"><span>글 <b>SFANDOM & KAIRO</b></span><time datetime="{a.date}">{a.date_dot} KST</time>{f'<span>{esc(a.meta)}</span>' if a.meta else ''}</div>
  </header>
  {preserved_component('nlcs-archived-preview-note') if a.file == '2026-10-11-nlcs-dodgers-brewers-game1.md' else ''}
  <div class="article-grid">
    <article>
      {matchup_strip(a) if a.kind == 'analysis' else ''}
      {fig}
      <div class="prose">{render_body(a)}</div>
      {src_html}{credit}
      {editorial_related(a, EDITORIAL_PATHS, BY_KEY, esc)}
      {discussion_html}
      <div style="margin-top:24px">{ed}</div>
      <div style="margin-top:32px">{ad('SF-ART-MULTI')}</div>
    </article>
    <aside class="article-aside" style="display:flex;flex-direction:column;gap:24px">
      {ad('SF-ART-RAIL')}
      <div class="aside-box"><h2>함께 읽기</h2>{rel}</div>
    </aside>
  </div>
</div>'''
    ld = {'@context': 'https://schema.org', '@type': 'NewsArticle' if a.kind != 'magazine' else 'Article',
          'headline': a.headline[:110], 'description': a.excerpt, 'datePublished': f'{a.date}T08:00:00+09:00',
          'dateModified': f'{a.date}T08:00:00+09:00', 'inLanguage': 'ko-KR', 'mainEntityOfPage': BASE + a.url,
          'author': {'@type': 'Organization', 'name': 'SFANDOM', 'url': BASE + '/about/'},
          'publisher': {'@id': f'{BASE}/#organization', '@type': 'Organization', 'name': 'SFANDOM',
                        'logo': {'@type': 'ImageObject', 'url': f'{BASE}/assets/brand/sfandom-mark-512.png'}}}
    share = a.image
    if not share:  # 사진이 없는 글은 build_article_cards.py 가 만든 글별 공유 카드 사용 (없으면 대표 카드)
        card = f'/assets/share/cards/{card_name(pathlib.Path(a.file).stem, a.__dict__)}'
        share = card if (ROOT / card.lstrip('/')).exists() else ''
    if share:
        ld['image'] = [share if share.startswith('http') else f'{BASE}{share}']
    write(a.url, layout(a.headline, body, path=a.url, description=a.excerpt, image=share, og_type='article',
                        ld=[ld, breadcrumb_ld(trail)], active=section_url, ads=True), lastmod=a.date,
          search={'u': a.url, 't': a.headline, 's': a.subtitle, 'k': a.section, 'd': a.date_dot, 'x': a.excerpt})


# ───────────────────────── 목록 ─────────────────────────
def list_with_ads(items: list[Article], every: int = 5, slot: str = 'SF-LIST-FEED') -> str:
    out = []
    for i, a in enumerate(items, 1):
        out.append(list_item(a))
        if i % every == 0 and i < len(items) and i // every <= 3:
            out.append(f'<div style="padding:16px 0">{ad(slot)}</div>')
    return '<div class="list">' + ''.join(out) + '</div>'


def page_head(title_html: str, lede: str, trail: list[tuple[str, str]], tabs: str = '') -> str:
    return f'<div class="wrap page-head">{crumbs(trail)}<h1>{title_html}</h1>{f"<p class=lede>{esc(lede)}</p>" if lede else ""}{tabs}</div>'


def tabs(items: list[tuple[str, str]], current: str) -> str:
    return '<nav class="tabs" aria-label="분류">' + ''.join(
        f'<a href="{u}"{CUR if u == current else ""}>{esc(l)}</a>' for l, u in items) + '</nav>'


def two_col(main: str, side_slot: str, side_extra: str = '') -> str:
    return (f'<div class="wrap sec split-8-4" style="padding-top:32px"><div class="main">{main}</div>'
            f'<aside class="side"><div class="sticky-rail">{ad(side_slot)}{side_extra}</div></aside></div>')


def latest_box(exclude_kind: str | None = None) -> str:
    items = [a for a in ARTICLES if a.kind != exclude_kind][:6]
    return '<div class="aside-box" style="margin-top:24px"><h2>최신 글</h2>' + ''.join(
        f'<a href="{a.url}"><small>{a.section} · {a.date_dot}</small>{esc(a.headline)}</a>' for a in items) + '</div>'


def build_lists():
    news = [a for a in ARTICLES if a.kind == 'news']
    news_tabs = tabs([('전체 뉴스', '/news/'), ('모닝 에디션', '/news/morning/')], '/news/')
    write('/news/', layout('NEWS · 스포츠 뉴스', page_head('NEWS<span class="accent">.</span> <span class="kr">읽고, 바로 토론</span>',
          '공식 기록으로 확인한 경기 소식. 모든 뉴스는 팬 보드 토론으로 이어집니다.', [('NEWS', '')], news_tabs)
          + two_col(list_with_ads(news) + ad_band('SF-LIST-BTM'), 'SF-HUB-RAIL', latest_box('news')),
          path='/news/', description='NBA 새 시즌과 MLB 포스트시즌 소식을 공식 기록 기준으로 정리합니다.', active='/news/',
          ld=[breadcrumb_ld([('NEWS', '/news/')])]))

    # 모닝 에디션
    eds = sorted(EDITIONS.items(), reverse=True)
    rows = []
    for d, e in eds:
        items = [BY_KEY[k] for k in e['items'] if k in BY_KEY]
        if not items:
            continue
        rows.append(f'<a class="li" href="/news/morning/{d}/">{thumb(items[0])}<div><span class="tag red">MORNING EDITION · {d.replace("-", ".")}</span>'
                    f'<h2>{esc((e.get("title", "") + " " + e.get("subtitle", "")).strip())}</h2><p>{esc(e.get("intro", ""))}</p>'
                    f'<span class="foot">{len(items)}개 글</span></div></a>')
        ebody = (page_head(f'MORNING <span class="accent">EDITION</span> <span class="kr">{d.replace("-", ".")}</span>', e.get('intro', ''),
                           [('NEWS', '/news/'), ('MORNING EDITION', '/news/morning/'), (d.replace('-', '.'), '')])
                 + two_col(f'<h2 class="sec-title" style="font-size:44px;margin-bottom:8px">{esc(e.get("title", ""))} <span class="kr">{esc(e.get("subtitle", ""))}</span></h2>'
                           + list_with_ads(items, 3), 'SF-HUB-RAIL', latest_box()))
        write(f'/news/morning/{d}/', layout(f'모닝 에디션 {d.replace("-", ".")} · {e.get("title", "")}', ebody, path=f'/news/morning/{d}/',
              description=e.get('intro', ''), active='/news/', ld=[breadcrumb_ld([('NEWS', '/news/'), ('MORNING EDITION', '/news/morning/'), (d, '')])], ads=True), lastmod=d)
    write('/news/morning/', layout('MORNING EDITION · 모닝 에디션', page_head('MORNING <span class="accent">EDITION</span>',
          '어제 경기에서 오늘까지 남는 것만 골라 매일 아침 정리합니다.', [('NEWS', '/news/'), ('MORNING EDITION', '')],
          tabs([('전체 뉴스', '/news/'), ('모닝 에디션', '/news/morning/')], '/news/morning/'))
          + two_col('<div class="list">' + ''.join(rows) + '</div>', 'SF-HUB-RAIL'), path='/news/morning/',
          description='SFANDOM 모닝 에디션 전체 목록', active='/news/'))

    # 매거진: sfandomsport 네이버 블로그 최근 글 링크 전용 화면.
    # 사진/영상 썸네일 외부 URL을 렌더링하거나 Google Blogger를 동적으로 스크랩하지 않습니다.
    # 과거 SFANDOM 원문은 /analysis/ 및 개별 기사 경로에 그대로 보존합니다.
    naver_mag = render_naver_magazine(BLOGS.get('naver', []), esc)
    write('/magazine/', layout('MAGAZINE · SFANDOM 네이버 블로그', page_head(
          'MAGAZINE<span class="accent">.</span> <span class="kr">NAVER BLOG</span>',
          'SFANDOM 네이버 블로그에 직접 게시한 최근 글과 선정 특집을 모았습니다. 글은 네이버 원문에서 읽습니다.',
          [('MAGAZINE', '')])
          + naver_mag,
          path='/magazine/', description='SFANDOM 네이버 블로그 최근 글과 NBA 심층 특집. 외부 사진 없는 원문 바로가기.',
          active='/magazine/'))


    # 연결된 원문을 한눈에 보는 독립 페이지 · 콘텐츠는 중복 재발행하지 않습니다.
    reading_body = (page_head('EDITORIAL <span class="accent">PATHS.</span>',
        '다른 시점과 관점으로 작성된 글은 합치지 않고, 연결해서 읽습니다.',
        [('ANALYSIS', '/analysis/'), ('연결 읽기', '')])
        + editorial_index(EDITORIAL_PATHS, BY_KEY, esc))
    write('/analysis/reading-paths/', layout('경기 기사 연결 읽기 | SFANDOM', reading_body,
          path='/analysis/reading-paths/', description='경기 전 프리뷰, 경기 후 복기와 독립 심층 기사 연결',
          active='/analysis/'))

    # 분석
    an = [a for a in ARTICLES if a.kind == 'analysis']
    lede, method = page_fragment('method')
    an_tabs = tabs([('전체', '/analysis/'), ('NBA', '/analysis/nba/'), ('MLB', '/analysis/mlb/'), ('복기 리포트', '/analysis/review/')], '/analysis/')
    write('/analysis/', layout('ANALYSIS · 경기 분석', page_head('ANALYSIS<span class="accent">.</span>', lede, [('ANALYSIS', '')], an_tabs)
          + preserved_component('analysis-cycle-guide') + two_col('<h2 class="sec-title" style="font-size:44px">LATEST <span class="kr">최근 경기 프리뷰</span></h2>' + list_with_ads(an, 4)
                    + f'<section id="method" class="sec"><h2 class="sec-title" style="font-size:56px">METHOD <span class="kr">분석은 이렇게 만듭니다</span></h2><div class="prose">{method}</div></section>',
                    'SF-HUB-RAIL', '<div class="aside-box" style="margin-top:24px"><h2>REVIEW</h2><a href="/analysis/review/">경기 전 전망과 실제 결과 기록 보기 →</a></div>'),
          path='/analysis/', description=lede, active='/analysis/'))
    write('/analysis/mlb/', layout('MLB 분석', page_head('MLB <span class="accent">ANALYSIS</span>', '선발 매치업과 순위 경쟁을 중심으로 본 MLB 경기 프리뷰.', [('ANALYSIS', '/analysis/'), ('MLB', '')],
          tabs([('전체', '/analysis/'), ('NBA', '/analysis/nba/'), ('MLB', '/analysis/mlb/'), ('복기 리포트', '/analysis/review/')], '/analysis/mlb/'))
          + two_col(list_with_ads([a for a in an if a.league == 'MLB'], 4), 'SF-HUB-RAIL', latest_box('analysis')),
          path='/analysis/mlb/', description='MLB 경기 프리뷰와 분석', active='/analysis/'))
    write('/analysis/nba/', layout('NBA 분석', page_head('NBA <span class="accent">ANALYSIS</span>', '새 시즌 주요 경기를 경기 전 구도 중심으로 정리한 NBA 프리뷰.', [('ANALYSIS', '/analysis/'), ('NBA', '')],
          tabs([('전체', '/analysis/'), ('NBA', '/analysis/nba/'), ('MLB', '/analysis/mlb/'), ('복기 리포트', '/analysis/review/')], '/analysis/nba/'))
          + two_col(list_with_ads([a for a in an if a.league == 'NBA'], 4), 'SF-HUB-RAIL', latest_box('analysis')),
          path='/analysis/nba/', description='NBA 경기 프리뷰와 분석', active='/analysis/'))
    recs = ''.join(f'''<div class="record"><span class="no">{r["no"]}</span><div><span class="tag red">{r["league"]} · {r["date"].replace("-", ".")} · {esc(r["venue"])}</span><h3>{esc(r["match"])}</h3>
<p>경기 전 · {esc(r["outlook"])} → 결과 · {esc(r["result"])}. {esc(r["detail"])}</p></div><span class="verdict {"ok" if r["matched"] else "no"}">{"MATCHED" if r["matched"] else "NOT MATCHED"}</span></div>''' for r in RECORDS['records'])
    ok = sum(r['matched'] for r in RECORDS['records'])
    write('/analysis/review/', layout('복기 리포트 · 경기 전 전망과 결과', page_head('REVIEW <span class="accent">/</span> <span class="kr">복기 리포트</span>', RECORDS['note'],
          [('ANALYSIS', '/analysis/'), ('REVIEW', '')], tabs([('전체', '/analysis/'), ('NBA', '/analysis/nba/'), ('MLB', '/analysis/mlb/'), ('복기 리포트', '/analysis/review/')], '/analysis/review/'))
          + preserved_component('review-cycle-guide') + editorial_index(EDITORIAL_PATHS, BY_KEY, esc, 'before-after') + two_col(f'<div class="stats" style="margin:0 0 12px"><div class="stat"><b>{len(RECORDS["records"])}</b><span>RECORDS</span></div><div class="stat"><b>{ok}</b><span>MATCHED</span></div><div class="stat"><b>{len(RECORDS["records"]) - ok}</b><span>NOT MATCHED</span></div><div class="stat"><b>{RECORDS["updated"][5:].replace("-", ".")}</b><span>UPDATED</span></div></div>'
                    + f'<div class="list">{recs}</div><p class="muted" style="font-size:14px;margin-top:20px">예상과 다른 결과도 지우지 않습니다. 어떤 전제가 틀렸는지 다음 분석에서 다시 확인합니다.</p>', 'SF-HUB-RAIL'),
          path='/analysis/review/', description=RECORDS['note'], active='/analysis/'))


# ───────────────────────── 허브 · 특집 ─────────────────────────
def build_hubs():
    mlb = [a for a in ARTICLES if a.league == 'MLB']
    sec = lambda kind, title, kr, anchor: (f'<section id="{anchor}" class="sec" style="padding-top:40px"><div class="sec-head"><h2 class="sec-title" style="font-size:52px">{title} <span class="kr">{kr}</span></h2></div>'
                                           + list_with_ads([a for a in mlb if a.kind == kind][:8], 4, 'SF-HUB-FEED') + '</section>')
    t = tabs([('뉴스', '#news'), ('분석', '#analysis'), ('매거진', '#magazine'), ('포스트시즌', '/special/postseason-2026/')], '')
    live_mlb = ('<section id="lcs" class="sec" style="padding-top:40px"><div class="sec-head"><h2 class="sec-title" style="font-size:42px">LEAGUE CHAMPIONSHIP <span class="kr">최신 전적 · 다음 경기</span></h2></div><div class="grid-4" style="grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))">'
                + ''.join(lcs_card(d) for d in PS.get('lcs', [])) + '</div></section>')
    main = live_mlb + sec('news', 'NEWS', 'MLB 뉴스', 'news') + sec('analysis', 'ANALYSIS', '경기 프리뷰', 'analysis') + sec('magazine', 'MAGAZINE', '기획 · 스포트라이트', 'magazine')
    write('/mlb/', layout('MLB · 메이저리그', page_head('MLB<span class="accent">.</span> <span class="kr">메이저리그</span>', '포스트시즌, 모닝 에디션, 선발 매치업까지 — MLB 이야기는 여기서 시작합니다.', [('MLB', '')], t)
          + two_col(main, 'SF-HUB-RAIL', '<div class="aside-box" style="margin-top:24px"><h2>POSTSEASON</h2><a href="/special/postseason-2026/">2026 포스트시즌 대진표 · 일정 →</a><a href="/community/">경기 얘기는 팬 보드에서 →</a></div>'),
          path='/mlb/', description='MLB 뉴스·경기 분석·매거진', active='/mlb/'))
    # NBA 허브
    story = ''.join(f'<div class="nba-story"><b>{x["k"]}</b><h3>{esc(x["t"])}</h3><p>{esc(x["x"])}</p></div>' for x in NBA['storylines'])
    kd = ''.join(f'<div class="round"><span class="display">{esc(d)}</span><span>{esc(t)}</span></div>' for d, t in NBA['key_dates'])
    nba_arts = [a for a in ARTICLES if a.league == 'NBA']
    preseason_rows = nba_cards(NBA.get('preseason_games', []), preseason_anchors=True)
    preseason_block = (f'<section class="sec" id="preseason"><div class="sec-head"><h2 class="sec-title">PRESEASON <span class="outline">GAME CENTER</span></h2><span class="muted">확인된 종료 {sum(bool(g.get("result")) for g in NBA.get("preseason_games", []))}경기 · 예정 및 확인 중 경기 구분 · 한국시간</span></div><div class="nba-stage solo"><div class="nba-rail preseason-list">{preseason_rows}</div></div></section>') if preseason_rows else ''
    nsec = lambda kind, title, kr, anchor: (f'<section id="{anchor}" class="sec"><div class="sec-head"><h2 class="sec-title">{title} <span class="kr">{kr}</span></h2></div>'
                                            + '<div class="card-grid">' + ''.join(mag_card(a) for a in nba_arts if a.kind == kind) + '</div></section>') if any(a.kind == kind for a in nba_arts) else ''
    nba_tabs = tabs([('프리시즌', '#preseason'), ('개막 주간', '#tipoff'), ('뉴스', '#news'), ('분석', '#analysis'), ('매거진', '#magazine'), ('주요 날짜', '#dates')], '')
    nba_body = (page_head('NBA <span class="accent">2026-27</span>', '새 시즌 개막까지 ' + nba_dday() + '. 개막 주간 일정과 여름 이적 시장, 개막전 프리뷰, 시즌 달력을 한곳에 모았습니다. 시간은 모두 한국시간입니다.', [('NBA', '')], nba_tabs)
                + f'''<div class="wrap">
{preseason_block}
<section class="sec" id="tipoff" style="padding-top:40px"><div class="sec-head"><h2 class="sec-title">TIP-OFF <span class="outline">WEEK</span></h2><span class="muted">개막 주간 · 시간은 한국시간</span></div><div class="nba-stage solo"><div class="nba-rail">{nba_cards(NBA["games"])}</div></div></section>
<section class="sec" id="stories"><div class="sec-head"><h2 class="sec-title">STORYLINES <span class="kr">개막 주간 볼거리</span></h2></div><div class="grid-4">{story}</div></section>
{nsec('news', 'NEWS', 'NBA 뉴스', 'news')}
{nsec('analysis', 'ANALYSIS', '개막전 프리뷰', 'analysis')}
{nsec('magazine', 'MAGAZINE', '기획 · 시즌 가이드', 'magazine')}
<section class="sec" id="christmas"><div class="sec-head"><h2 class="sec-title">CHRISTMAS <span class="outline">DAY</span></h2><span class="muted">현지 12.25 · 한국시간 12.26</span></div><div class="nba-stage solo"><div class="nba-rail five">{nba_cards(NBA["christmas"])}</div></div></section>
<section class="sec" id="dates"><div class="bracket"><div class="bracket-head"><h2>KEY DATES</h2><span class="muted">{esc(NBA["note"])}</span></div><div class="rounds">{kd}</div></div></section>
<section class="discuss"><div><h2>새 시즌 얘기는 팬 보드에서</h2><p>우승 후보, 기대되는 팀, 개막전 예상 모두 환영합니다.</p></div><a class="pill" href="/community/?topic={quote("[NBA] ")}#write">{talk_icon()}글쓰기</a></section>
</div>''')
    write('/nba/', layout('NBA 프리시즌 최종 결과·다음 경기 일정 (한국시간)', nba_body, path='/nba/', description='NBA 2026-27 프리시즌 결과와 다음 일정, 개막 주간 경기 정보를 한국시간으로 정리.', active='/nba/',
          ld=[breadcrumb_ld([('NBA', '/nba/')])]),
          search={'u': '/nba/', 't': 'NBA 프리시즌 최종 점수와 다음 일정', 's': '프리시즌 종료 경기 · 다음 일정 · 정규시즌 개막', 'k': 'NBA', 'd': '2026.10.11', 'x': 'NBA 프리시즌 최신 확인 점수와 향후 일정'})
    # 포스트시즌 특집
    wc = ''.join(wc_result(w) for w in PS['wildcard'])
    dsf = ''.join(ds_card(d, link=False, full=True) for d in PS['division'])
    lcsf = ''.join(lcs_card(d, link=False, full=True) for d in PS.get('lcs', []))
    seeds = ''.join(
        f'<div class="seed-list"><h3>{lg["name"]}</h3>' + ''.join(
            f'<div class="seed-row"><b>{s["seed"]}</b>{badge(s["abbr"], s["color"])}<span class="abbr"></span><small>{s["record"]} · {esc(s["note"])}</small></div>' for s in lg['seeds']) + '</div>'
        for lg in PS['leagues'])
    rounds = ''.join(f'<div class="round"><span class="display">{r["name"]}</span><span>{esc(r["kr"])}</span><span class="tag red">{esc(r["dates"])}</span></div>' for r in PS['rounds'])
    srcs = ''.join(f'<span>{esc(s["label"])}</span>' for s in PS['source'])
    rel = [a for a in ARTICLES if a.league == 'MLB' and a.date >= '2026-09-24'][:6]
    body = (page_head('POSTSEASON <span class="accent">2026</span>', '정규시즌 2,430경기가 끝났습니다. 챔피언십시리즈에 4개 팀이 남았습니다. NLCS·ALCS 최신 전적과 다음 경기, 지난 라운드 결과를 한국시간으로 확인합니다.',
                      [('POSTSEASON', '')])
            + f'''<div class="wrap">
<section class="sec" id="lcs" style="padding-top:40px"><div class="sec-head"><h2 class="sec-title">LEAGUE <span class="outline">CHAMPIONSHIP</span></h2><span class="muted">7전 4선승 · 한국시간 · {PS["updated"].replace("-", ".")} 기준</span></div><div class="grid-4" style="grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))">{lcsf}</div></section>
<section class="sec" id="division"><div class="sec-head"><h2 class="sec-title">DIVISION <span class="outline">SERIES</span></h2><span class="muted">5전 3선승 · 시간은 한국시간 · {PS["updated"].replace("-", ".")} 기준</span></div><div class="grid-4">{dsf}</div></section>
<section class="sec" id="wildcard"><div class="sec-head"><h2 class="sec-title">WILD CARD <span class="kr">결과</span></h2><span class="muted">3전 2선승 · 종료</span></div><div class="grid-4">{wc}</div></section>
<section class="sec" id="bracket"><div class="bracket"><div class="bracket-head"><h2>SEEDS<span class="accent">.</span></h2><span class="muted">정규시즌 최종 성적 · {PS["updated"].replace("-", ".")} 확인</span></div><div class="seeds">{seeds}</div><div class="rounds">{rounds}</div>
<div class="sources" style="border:0;padding-bottom:0"><strong>출처</strong>{srcs}</div></div></section>
{ad_band('SF-LIST-BTM')}
<section class="sec"><div class="sec-head"><h2 class="sec-title">ROAD TO <span class="accent">OCTOBER</span> <span class="kr">가을로 가는 길</span></h2><a class="more" href="/news/morning/">모닝 에디션 전체 →</a></div><div class="card-grid">{"".join(mag_card(a) for a in rel)}</div></section>
<section class="discuss"><div><h2>경기 얘기는 팬 보드에서</h2><p>예상, 복기, 한 줄 평 모두 환영합니다.</p></div><a class="pill" href="/community/?topic={quote("[챔피언십시리즈] ")}#write">{talk_icon()}글쓰기</a></section>
</div>''')
    ld = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': '2026 MLB 포스트시즌 대진표·일정', 'url': BASE + '/special/postseason-2026/', 'inLanguage': 'ko-KR'}
    write('/special/postseason-2026/', layout('2026 MLB 포스트시즌 · 챔피언십시리즈 최신 일정 (한국시간)', body, path='/special/postseason-2026/',
          description='2026 MLB 포스트시즌 챔피언십시리즈 최신 전적과 다음 경기, 디비전시리즈 종료 결과를 한국시간으로 정리.',
          ld=[ld, breadcrumb_ld([('POSTSEASON', '/special/postseason-2026/')])], active='/special/postseason-2026/'),
          search={'u': '/special/postseason-2026/', 't': '2026 MLB 포스트시즌 대진표 · 일정', 's': 'NLCS·ALCS · 디비전시리즈 종료 결과', 'k': 'SPECIAL', 'd': PS['updated'].replace('-', '.'), 'x': '챔피언십시리즈 전적과 다음 경기, 디비전시리즈 결과'})


# ───────────────────────── 포스트시즌 · NBA 카드 ─────────────────────────
def ds_next(d: dict):
    return next((g for g in d['games'] if not g.get('result')), None)



def lcs_card(d: dict, link: bool = True, full: bool = False) -> str:
    """챔피언십시리즈 최신 전적·확정 결과·앞으로의 한국시간 일정."""
    done = [g for g in d['games'] if g.get('result')]
    future = [g for g in d['games'] if not g.get('result')]
    lead = 'lead-h' if d['hw'] > d['aw'] else ('lead-a' if d['aw'] > d['hw'] else '')
    last = ''.join('<span class="ds-res"><b>G' + str(g['g']) + '</b>' + esc(g['result']) + '</span>' for g in (done if full else done[-1:]))
    next_games = future if full else future[:1]
    rest = ''.join('<span class="ds-res up"><b>G' + str(g['g']) + '</b>' + esc(g['kst']) + ' KST</span>' for g in next_games)
    when = ('G' + str(future[0]['g']) + ' · ' + esc(future[0]['kst']) + ' KST') if future else '시리즈 종료'
    tag = 'a' if link else 'div'
    href = ' href="/special/postseason-2026/#lcs"' if link else ''
    return (f'<{tag} class="matchup ds {lead}{" lift" if link else ""}"{href}><span class="tag">{esc(d["league"])}CS · 7전 4선승</span>'
            f'<div class="row">{badge(d["home"], d["home_color"], "lg")}<span class="ds-name">{esc(d["home_kr"])}<small>#{d["hs"]} · 홈 어드밴티지</small></span><span class="ds-w h">{d["hw"]}</span></div>'
            f'<div class="row">{badge(d["away"], d["away_color"], "lg")}<span class="ds-name">{esc(d["away_kr"])}<small>#{d["as"]}</small></span><span class="ds-w a">{d["aw"]}</span></div>'
            f'<div class="ds-log">{last}{rest}</div><span class="when">{when}</span></{tag}>')


def ds_card(d: dict, link: bool = True, full: bool = False) -> str:
    """디비전시리즈 카드. 시리즈 전적 + 지난 경기 결과 + 다음 경기(한국시간)."""
    done = [g for g in d['games'] if g.get('result')]
    nxt = ds_next(d)
    lead = 'lead-h' if d['hw'] > d['aw'] else ('lead-a' if d['aw'] > d['hw'] else '')
    last = ''.join('<span class="ds-res"><b>G' + str(g['g']) + '</b>' + esc(g['result']) + '</span>' for g in (done if full else done[-1:]))
    rest = ''
    if full:
        rest = ''.join('<span class="ds-res up"><b>G' + str(g['g']) + '</b>' + esc(g['kst']) + (' · 필요 시' if g.get('if') else '') + '</span>' for g in d['games'] if not g.get('result'))
    when = (str(nxt['g']) + '차전 · 한국시간 ' + esc(nxt['kst'])) if nxt else '시리즈 종료'
    tag, end = ('a', 'a') if link else ('div', 'div')
    href = ' href="/special/postseason-2026/#division"' if link else ''
    return (f'<{tag} class="matchup ds {lead}{" lift" if link else ""}"{href}><span class="tag">{d["league"]}DS · 5전 3선승</span>'
            f'<div class="row">{badge(d["home"], d["home_color"], "lg")}<span class="ds-name">{esc(d["home_kr"])}<small>#{d["hs"]} · 홈</small></span><span class="ds-w h">{d["hw"]}</span></div>'
            f'<div class="row">{badge(d["away"], d["away_color"], "lg")}<span class="ds-name">{esc(d["away_kr"])}<small>#{d["as"]}</small></span><span class="ds-w a">{d["aw"]}</span></div>'
            f'<div class="ds-log">{last}{rest}</div><span class="when">{when}</span></{end}>')


def wc_result(w: dict) -> str:
    games = ''.join('<span class="ds-res"><b>G' + str(i) + '</b>' + esc(g) + '</span>' for i, g in enumerate(w.get('games', []), 1))
    win_home = w.get('winner') == w['home_abbr']
    return (f'<div class="matchup ds done {"lead-h" if win_home else "lead-a"}"><span class="tag">{w["league"]} WILD CARD · 종료</span>'
            f'<div class="row">{badge(w["home_abbr"], w["home_color"], "lg")}<span class="ds-name">{esc(w["home"])}<small>#{w["hs"]} · 홈</small></span><span class="ds-w h">{w["series"].split("–")[0] if win_home else w["series"].split("–")[1]}</span></div>'
            f'<div class="row">{badge(w["away_abbr"], w["away_color"], "lg")}<span class="ds-name">{esc(w["away"])}<small>#{w["as"]}</small></span><span class="ds-w a">{w["series"].split("–")[1] if win_home else w["series"].split("–")[0]}</span></div>'
            f'<div class="ds-log">{games}</div><span class="when">{esc(w["winner"])} 디비전시리즈 진출</span></div>')


def nba_cards(games: list, preseason_anchors: bool = False) -> str:
    out = ''
    for g in games:
        tag = '<em class="nba-tag">' + esc(g['tag']) + '</em>' if g.get('tag') else ''
        head = (g['day'] + ' · ' + g['tv']) if g.get('day') else 'CHRISTMAS DAY'
        id_attr = f' id="preseason-{g["away"].lower()}-{g["home"].lower()}"' if preseason_anchors else ''
        separator = 'VS' if (g.get('result') or str(g.get('day', '')).upper().startswith(('FINAL', 'LIVE'))) else '@'
        out += (f'<div class="nba-card"{id_attr}><small>{esc(head)}</small>'
                f'<b class="vsline">{badge(g["away"], NBA["colors"].get(g["away"], "#444"), league="nba")}<i class="match-separator">{separator}</i>{badge(g["home"], NBA["colors"].get(g["home"], "#444"), league="nba")}</b>'
                f'<time>{esc(g["kst"])}</time>{tag}</div>')
    return out


def nba_home_story(g: dict) -> str:
    separator = 'VS' if (g.get('result') or str(g.get('day', '')).upper().startswith(('FINAL', 'LIVE'))) else '@'
    tag = f'<em class="nba-tag">{esc(g["tag"])}</em>' if g.get('tag') else ''
    destination = f'/nba/#preseason-{g["away"].lower()}-{g["home"].lower()}' if g in NBA.get('preseason_games', []) else '/nba/#tipoff'
    label = esc(f'{g["away"]} - {g["home"]} ' + ('최종 결과 확인' if g.get('result') else '경기 일정 확인'))
    return (f'<a class="ts tip" href="{destination}" aria-label="{label}"><span><span class="tag">{esc(g.get("day", "PRESEASON"))} · {esc(g["kst"])}</span>'
            f'<b class="vsline">{badge(g["away"], NBA["colors"].get(g["away"], "#444"), league="nba")}<i class="match-separator">{separator}</i>'
            f'{badge(g["home"], NBA["colors"].get(g["home"], "#444"), league="nba")}</b>{tag}</span></a>')


def nba_dday() -> str:
    days = (dt.datetime.fromisoformat(NBA['opening_kst']).date() - dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()).days
    return f'D-{days}' if days > 0 else ('D-DAY' if days == 0 else 'NOW')


def nba_home_preseason() -> bool:
    opening = dt.datetime.fromisoformat(NBA['opening_kst']).date()
    today = dt.date.fromisoformat(TODAY)
    return NBA.get('home_mode') == 'preseason' and bool(NBA.get('preseason_games')) and today < opening


def nba_home_games() -> list:
    """Keep the five home results closest to KST now instead of pinned old finals."""
    if not nba_home_preseason():
        return NBA['games']
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    def when(game):
        m = re.match(r'(\d{1,2})\.(\d{1,2}).*?(\d{2}):(\d{2})', game.get('kst', ''))
        if not m:
            return now + dt.timedelta(days=365)
        month, day, hour, minute = map(int, m.groups())
        try:
            return dt.datetime(2026, month, day, hour, minute, tzinfo=now.tzinfo)
        except ValueError:
            return now + dt.timedelta(days=365)
    ordered = sorted(NBA.get('preseason_games', []), key=when)
    recent = [g for g in ordered if now - dt.timedelta(hours=18) <= when(g) <= now + dt.timedelta(hours=60)]
    return recent or [g for g in ordered if when(g) >= now][:6] or ordered[-6:]


def nba_section() -> str:
    """NBA 현재 구간 띠 (홈 화면 전체 폭)."""
    preseason = nba_home_preseason()
    games = nba_home_games()
    cards = nba_cards(games)
    dday = (f'{sum(bool(g.get("result")) for g in games)} FINAL · NEXT' if preseason else nba_dday())
    title = 'PRESEASON <span class="outline">RESULTS</span>' if preseason else 'TIP-OFF <span class="outline">WEEK</span>'
    verified_time, _old = game_age((game_snapshot().get('leagues', {}).get('NBA') or {}).get('checked_at', ''))
    copy = (f'확인된 최종 결과와 예정·확인 중 경기를 구분합니다. 마지막 기록 확인: {verified_time}. 모든 시간은 한국시간입니다.'
            if preseason else '10월 21일(수) 새벽, 새 시즌이 시작됩니다. 개막 주간 주요 경기를 한국시간으로 정리했습니다.')
    return (f'<section class="wrap sec" id="nba" aria-labelledby="nbaTitle"><div class="nba-stage">'
            f'<div class="nba-intro"><span class="nba-kicker"><span class="nba-ball" aria-hidden="true"></span>NBA {NBA["season"]}</span>'
            f'<h2 class="sec-title" id="nbaTitle">{title}</h2>'
            f'<p>{copy}</p><a class="pill" href="/nba/">NBA 허브 →</a>'
            f'<b class="nba-dday">{dday}</b></div>'
            f'<div class="nba-rail">{cards}</div></div></section>')


# ───────────────────────── 커뮤니티 · 정적 ─────────────────────────
def build_sitemap():
    arts = lambda kind: [a for a in ARTICLES if a.kind == kind]
    k = lambda name, url, thread=False: (name, url, thread)
    bl = SITE.get('blogs', {})
    blog_kids = [k(v['label'].title().replace('Blog', '블로그'), v['url']) for v in bl.values() if v.get('url')]
    blog_kids += [k(p['title'], p['link']) for p in blog_posts(8)]
    eds = [k(f'모닝 에디션 {d.replace("-", ".")}', f'/news/morning/{d}/') for d in sorted(EDITIONS, reverse=True)]
    cols = [
        ('NEWS', '/news/', '매일 올라오는 소식. 전부 토론 글이 된다',
         [k('뉴스 목록', '/news/'), k('모닝 에디션', '/news/morning/')] + eds),
        ('NBA', '/nba/', '새 시즌 허브. 개막 주간 · 주요 일정',
         [k('개막 주간 일정', '/nba/#tipoff'), k('NBA 뉴스', '/nba/#news'), k('NBA 분석', '/analysis/nba/'), k('NBA 매거진', '/nba/#magazine'), k('크리스마스 경기', '/nba/#christmas'), k('주요 날짜', '/nba/#dates')]),
        ('MLB', '/mlb/', '포스트시즌 · 뉴스 · 분석 · 매거진',
         [k('포스트시즌 대진표', '/special/postseason-2026/'), k('디비전시리즈', '/special/postseason-2026/#division'), k('와일드카드 결과', '/special/postseason-2026/#wildcard'),
          k('MLB 뉴스', '/mlb/#news'), k('MLB 분석', '/mlb/#analysis'), k('MLB 매거진', '/mlb/#magazine')]),
        ('ANALYSIS', '/analysis/', '경기 프리뷰 + 복기',
         [k('분석 전체', '/analysis/'), k('NBA 분석', '/analysis/nba/'), k('MLB 분석', '/analysis/mlb/'), k('분석 원칙', '/analysis/#method'), k('복기 리포트', '/analysis/review/', True)]),
        ('FAN BOARD', '/community/', '먼저 놀고. 가입 없이 쓰는 팬 게시판',
         [k('팬 보드', '/community/', True), k('글쓰기', '/community/#write', True), k('커뮤니티 규칙', '/rules/')]),
        ('BLOG', SITE['blogs']['google']['url'], '뉴스 · 볼거리는 구글 · 네이버 블로그에서', blog_kids),
        ('MAGAZINE · INFO', '/magazine/', '긴 글과 사이트 안내',
         [k('매거진', '/magazine/'), k('소개', '/about/'), k('문의', '/contact/'), k('개인정보처리방침', '/privacy/'),
          k('광고 · 쿠키 고지', '/ads-cookies/'), k('이용약관', '/terms/'), k('법률고지', '/legal/'), k('검색', '/search/')]),
    ]
    col_html = ''.join(
        f'<div class="sm-col"><a class="sm-head" href="{u}"{EXT if u.startswith("http") else ""}><span class="display">{l}</span><small>{esc(u.replace("https://", ""))}</small></a><p class="sm-role">{esc(role)}</p>'
        + ''.join(f'<a class="sm-kid{" thread" if t else ""}" href="{ku}"{EXT if ku.startswith("http") else ""}>{esc(kn)}<small>{esc(ku.replace("https://", ""))}</small></a>' for kn, ku, t in kids)
        + '</div>' for l, u, role, kids in cols)
    def group(title, kr, items):
        rows = ''.join(f'<a class="sm-row" href="{a.url}"><time datetime="{a.date}">{a.date_dot}</time><span>{esc(a.headline)}</span><small>{esc(a.league)}</small></a>' for a in items)
        return f'<section class="sm-group"><h2 class="sec-title" style="font-size:44px">{title} <span class="kr">{kr} · {len(items)}편</span></h2><div class="sm-rows">{rows}</div></section>'
    body = (page_head(f'SITEMAP<span class="accent">.</span> <span class="kr motto-en">{esc(SITE["motto"])}</span>',
                      f'SFANDOM의 모든 페이지를 한곳에 모았습니다. 메뉴 {len(NAV)}개, 글 {len(ARTICLES)}편.', [('사이트맵', '')])
            + f'''<div class="wrap sec" style="padding-top:36px">
  <div class="sm-legend"><span><i class="sw red"></i>상단 메뉴</span><span><i class="sw blue"></i>토론이 붙는 페이지</span><span><i class="sw gray"></i>하위 페이지</span></div>
  <div class="sm-grid">{col_html}</div>
  {group('NEWS', '뉴스', arts('news'))}
  {group('ANALYSIS', '경기 프리뷰', arts('analysis'))}
  {group('MAGAZINE', '매거진', arts('magazine'))}
</div>''')
    write('/sitemap/', layout('사이트맵', body, path='/sitemap/', description='SFANDOM 전체 페이지 사이트맵', active='/sitemap/'))


def build_community():
    body = (page_head('FAN BOARD<span class="accent">.</span> <span class="kr">먼저 놀고</span>', '가입 없이 닉네임만으로 쓰는 팬 게시판. 경기 얘기, 직관 후기, 반론 모두 환영합니다.', [('FAN BOARD', '')])
            + f'''<div class="wrap" style="padding-top:28px">{channel_chips()}</div>
<div class="wrap sec board-grid" style="padding-top:24px">
  <div data-board data-size="10">
    <div data-admin-mode><button type="button" data-admin-open>관리자 로그인</button><button type="button" data-admin-logout hidden>로그아웃</button>
      <div data-admin-panel hidden><form data-admin-form><input name="email" type="email" placeholder="관리자 이메일" aria-label="관리자 이메일" required><button type="submit">이메일 인증</button></form><p data-admin-status role="status"></p></div>
    </div>
    <div class="thread-head" data-thread-head hidden><span class="box-title">GAME THREAD</span><strong data-thread-name></strong><a class="more" href="/community/">전체 글로 돌아가기 →</a></div>
    <div data-board-list><div class="empty">스포츠 팬들의 경기·선수 토론을 확인할 수 있습니다. <a href="/community/">팬 보드에서 최신 글 보기 →</a></div></div>
    <div class="pager" data-board-pager></div>
    <form class="composer" id="write" data-board-form style="margin-top:32px" novalidate>
      <span class="box-title">WRITE · 글쓰기</span>
      <div class="row3"><div><label for="chn">채널</label><select id="chn" name="channel">{"".join(f'<option value="{esc(c)}"{" selected" if c == "자유" else ""}>{esc(c)}</option>' for c in CHANNELS)}</select></div>
      <div><label for="nick">닉네임</label><input id="nick" name="nickname" maxlength="30" placeholder="ANON" autocomplete="nickname"></div>
      <div><label for="ttl">제목</label><input id="ttl" name="title" maxlength="100" required placeholder="오늘 경기, 무슨 얘기 하고 싶어요?"></div></div>
      <div><label for="bdy">내용</label><textarea id="bdy" name="body" maxlength="2000" required></textarea></div>
      <label class="hp" aria-hidden="true">website<input name="website" tabindex="-1" autocomplete="off"></label>
      <div class="composer-foot"><p class="status" data-board-status role="status">작성한 글은 바로 공개됩니다. 게시 전 <a href="/rules/" class="accent">커뮤니티 규칙</a>을 확인해 주세요.</p><button class="pill" type="submit">게시하기</button></div>
    </form>
  </div>
  <aside style="display:flex;flex-direction:column;gap:20px">
    {quick_box(6)}
    {game_threads()}
    <div class="box"><span class="box-title">HOUSE RULES</span><ul class="rules"><li>욕설 · 비하 · 혐오 표현 금지</li><li>도배 · 광고 링크 · 사칭 금지</li><li>불법 도박 사이트 홍보 · 가입코드 금지</li><li>개인정보 · 사생활 노출 금지</li><li>스포일러는 경기 스레드에서</li></ul><a class="more" href="/rules/">전체 규칙 →</a></div>
  </aside>
</div>''')
    write('/community/', layout('FAN BOARD · 팬 게시판', body, path='/community/', description='SFANDOM 팬 보드 — 가입 없이 쓰는 스포츠 팬 게시판', active='/community/'))


def build_static():
    pages = [
        ('about', 'ABOUT', '소개', 'SFANDOM 소개'),
        ('privacy', 'PRIVACY', '개인정보처리방침', 'SFANDOM 개인정보처리방침'),
        ('terms', 'TERMS', '이용약관', 'SFANDOM 서비스 이용약관'),
        ('rules', 'RULES', '커뮤니티 규칙', '커뮤니티 규칙'),
        ('legal', 'LEGAL', '법률고지', 'SFANDOM 주요 법률 고지'),
    ]
    for key, en, kr, title in pages:
        lede, frag = page_fragment(key)
        body = page_head(f'{en}<span class="accent">.</span> <span class="kr">{kr}</span>', lede, [(kr, '')]) + \
            f'<div class="wrap sec" style="padding-top:36px;max-width:960px;margin-left:0"><div class="prose">{frag}</div></div>'
        write(f'/{key}/', layout(title, body, path=f'/{key}/', description=lede[:150]))

    ep = (SITE.get('contact') or {}).get('endpoint', '')
    contact = f'''<div class="wrap sec" style="padding-top:36px;max-width:960px;margin-left:0">
<form class="composer contact-form" data-contact data-endpoint="{esc(ep)}" novalidate>
  <div class="row">
    <div><label for="cType">문의 종류</label>
      <select id="cType" name="type" required>
        <option value="기사·기록 정정">기사·기록 정정</option>
        <option value="게시물 신고·삭제 요청">게시물 신고·삭제 요청</option>
        <option value="제휴·광고 문의">제휴·광고 문의</option>
        <option value="기타">기타</option>
      </select></div>
    <div><label for="cTitle">제목</label><input id="cTitle" name="title" type="text" maxlength="100" required placeholder="한 줄로 적어 주세요"></div>
  </div>
  <div class="row">
    <div><label for="cName">이름 또는 닉네임 <span class="opt">선택</span></label><input id="cName" name="name" type="text" maxlength="40" autocomplete="name"></div>
    <div><label for="cReply">답변 받을 이메일 <span class="opt">답변이 필요할 때만</span></label><input id="cReply" name="reply" type="email" maxlength="120" autocomplete="email" placeholder="name@example.com"></div>
  </div>
  <div><label for="cBody">내용</label><textarea id="cBody" name="body" maxlength="850" required placeholder="글 주소, 게시물 번호, 확인할 수 있는 출처를 함께 적어 주시면 빠르게 확인할 수 있습니다."></textarea></div>
  <input class="hp" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
  <label class="check"><input type="checkbox" name="agree" required> 문의 처리를 위해 위 내용을 수집·보관하는 데 동의합니다. <a href="/privacy/">개인정보처리방침</a></label>
  <div class="composer-foot"><span class="muted" data-contact-msg role="status" aria-live="polite">{"" if ep else "쪽지함을 준비하고 있습니다. 곧 이 양식으로 보내실 수 있습니다."}</span>
    <button class="pill" type="submit"{"" if ep else " disabled"}>쪽지 보내기</button></div>
</form>
<div class="prose" style="margin-top:36px">
<h2>이런 내용을 보내 주세요</h2>
<ul><li><strong>기사·기록 정정</strong> — 해당 글 주소와 틀린 부분, 확인할 수 있는 공식 출처</li>
<li><strong>게시물 신고·삭제 요청</strong> — 게시물 번호나 제목, 요청 사유(명예훼손·개인정보·저작권 등)</li>
<li><strong>제휴·광고 문의</strong> — 회사명, 담당자 연락처, 제안 내용</li></ul>
<h2>운영 원칙</h2>
<p>보내 주신 내용은 운영자만 볼 수 있는 곳에 보관하며, 답변이 필요한 문의는 적어 주신 이메일로 회신합니다. 권리침해 신고가 들어온 게시물은 확인 전까지 임시로 비공개 처리할 수 있으며, 처리 기준은 <a href="/rules/">커뮤니티 규칙</a>과 <a href="/legal/">법률고지</a>를 따릅니다. SFANDOM은 금전이 걸린 게임, 불법 스포츠도박 사이트와 관련된 제휴 문의에는 응하지 않습니다.</p>
</div></div>'''
    write('/contact/', layout('문의', page_head('CONTACT<span class="accent">.</span> <span class="kr">문의</span>', 'SFANDOM에 전하고 싶은 이야기가 있다면 쪽지로 남겨 주세요.', [('문의', '')]) + contact,
          path='/contact/', description='SFANDOM 문의 양식 · 오류 제보 · 권리침해 신고'))

    cookies = f'''<div class="wrap sec" style="padding-top:36px;max-width:960px;margin-left:0"><div class="prose">
<h2>광고 게재</h2>
<p>SFANDOM은 Google AdSense를 통해 광고를 게재합니다. 광고는 본문과 구분되도록 “광고” 표시가 붙은 자리에만 나오며, 추천·글쓰기·투표 버튼 가까이에는 두지 않습니다.</p>
<h2>Google과 제3자 쿠키</h2>
<p>Google을 포함한 제3자 광고 파트너는 쿠키(Google의 DART 쿠키 등)를 사용하여 이용자가 SFANDOM 및 인터넷상의 다른 사이트를 방문한 기록을 바탕으로 맞춤형 광고를 게재할 수 있습니다.</p>
<ul><li><a href="https://adssettings.google.com" target="_blank" rel="noopener">Google 광고 설정</a>에서 맞춤형 광고를 끌 수 있습니다.</li>
<li><a href="https://www.aboutads.info" target="_blank" rel="noopener">www.aboutads.info</a>에서 제3자 공급업체의 맞춤형 광고 쿠키 사용을 거부할 수 있습니다.</li>
<li>Google이 광고 쿠키를 사용하는 방식은 <a href="https://policies.google.com/technologies/ads" target="_blank" rel="noopener">Google 광고 정책</a>에서 확인할 수 있습니다.</li></ul>
<h2>SFANDOM이 직접 저장하는 값</h2>
<p>SFANDOM은 연속 게시 방지를 위해 브라우저 저장공간(localStorage)에 최소한의 값만 저장합니다. 이 값은 광고 타기팅이나 이용자 프로파일링에 쓰지 않으며, 브라우저 설정에서 사이트 데이터를 삭제하면 초기화됩니다.</p>
<p>자세한 내용은 <a href="/privacy/">개인정보처리방침</a>을 참고해 주세요.</p>
</div></div>'''
    write('/ads-cookies/', layout('광고·쿠키 고지', page_head('ADS &amp; COOKIES<span class="accent">.</span> <span class="kr">광고·쿠키 고지</span>', 'SFANDOM에 게재되는 광고와 쿠키 사용에 대한 안내입니다.', [('광고·쿠키 고지', '')]) + cookies,
          path='/ads-cookies/', description='SFANDOM 광고(Google AdSense) 및 쿠키 사용 안내'))

    search = (page_head('SEARCH<span class="accent">.</span> <span class="kr">검색</span>', '', [('검색', '')])
              + '<div class="wrap sec" style="padding-top:28px"><form action="/search/" role="search" style="display:flex;gap:10px;max-width:720px"><label class="sr-only" for="searchPageInput">검색어</label><input id="searchPageInput" name="q" type="search" style="flex:1;height:52px;border:1px solid var(--line-2);border-radius:999px;background:var(--panel);padding:0 22px"><button class="pill" type="submit" style="height:52px">검색</button></form>'
              '<p class="muted" data-search-count style="margin:18px 0 0"></p><div class="list" data-search-results></div></div>')
    write('/search/', layout('검색', search, path='/search/', noindex=True), index=False)

    notfound = ('<div class="wrap sec"><div class="soon-box"><span class="chip">404</span><h2>PAGE NOT FOUND</h2><p>주소가 바뀌었거나 없는 페이지입니다. 검색하거나 홈에서 다시 시작해 주세요.</p>'
                '<form action="/search/" style="display:flex;gap:10px;width:100%;max-width:520px"><label class="sr-only" for="nf">검색</label><input id="nf" name="q" type="search" style="flex:1;height:48px;border:1px solid var(--line-2);border-radius:999px;background:var(--bg);padding:0 18px"><button class="pill" type="submit">검색</button></form>'
                '<a class="pill ghost" href="/">홈으로</a></div></div>')
    (ROOT / '404.html').write_text(layout('페이지를 찾을 수 없습니다', notfound, path='/404.html', noindex=True), encoding='utf-8')


# ───────────────────────── 옛 주소 연결 ─────────────────────────
# ───────────────────────── sitemap · robots · search ─────────────────────────
def build_meta_files():
    urls = ''.join(f'  <url><loc>{BASE}{p["url"]}</loc><lastmod>{p["lastmod"]}</lastmod></url>\n' for p in sorted(PAGES, key=lambda p: p['url']))
    (ROOT / 'sitemap.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n', encoding='utf-8')
    (ROOT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nDisallow: /src/\nDisallow: /search/\nDisallow: /README.md\n\nSitemap: {BASE}/sitemap.xml\n', encoding='utf-8')
    (ROOT / 'search-index.json').write_text(json.dumps(sorted(SEARCH, key=lambda s: s['d'], reverse=True), ensure_ascii=False), encoding='utf-8')


WEEKLY_DIR = CONTENT / 'weekly'


def prepare_weekly():
    """지난 주 스냅샷이 없으면 한 번 읽어 저장한다 (푸터 링크가 있는지 알려면 페이지 빌드보다 먼저 해야 함)."""
    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    y, w, start, end = weekly.last_week(dt.date.fromisoformat(TODAY))
    f = WEEKLY_DIR / f'{y}-w{w:02d}.json'
    if not f.exists():
        snap = weekly.fetch_snapshot(SITE.get('supabase') or {}, y, w, start, end)
        if snap:
            f.write_text(json.dumps(snap, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def build_weekly():
    """지난 주 팬 보드 인기 글(댓글 수 기준). 스냅샷이 하나도 없으면 페이지를 만들지 않는다."""
    snaps = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(WEEKLY_DIR.glob('*.json'), reverse=True)]
    if not snaps:
        return

    def issue_body(sn):
        rows = ''.join(
            f'<li style="padding:14px 0;border-bottom:1px solid var(--line,#2a2f3d)"><small>{i}위 · {esc(r["channel"])} · {esc(r["created"])}</small><br>'
            f'<a href="/community/?ch={quote(r["channel"])}"><b>{esc(r["title"])}</b></a><br>'
            f'<small>{esc(r["nickname"])} · 댓글 {r["comments"]}개</small></li>'
            for i, r in enumerate(sn['top'], 1))
        chans = ' · '.join(f'{esc(k)} {v}' for k, v in sn['channels'].items())
        return (f'<div class="wrap sec" style="padding-top:36px;max-width:960px;margin-left:0">'
                f'<p>{esc(sn["start"])} ~ {esc(sn["end"])} · 새 글 {sn["posts"]}편 · 댓글 {sn["comments"]}개<br><small>{chans}</small></p>'
                f'<ol style="list-style:none;padding:0;margin:16px 0">{rows}</ol>'
                f'<div style="display:flex;gap:10px;flex-wrap:wrap"><a class="pill" href="/community/">팬 보드에서 이어 얘기하기</a>'
                f'<a class="pill ghost" href="/weekly/">지난 주간 베스트</a></div></div>')

    for sn in snaps:
        label = f'{sn["start"][5:].replace("-", ".")} ~ {sn["end"][5:].replace("-", ".")}'
        body = page_head(f'WEEKLY<span class="accent">.</span> <span class="kr">{label} 팬 보드 베스트</span>',
                         '지난 한 주 팬 보드에서 가장 많은 이야기가 오간 글입니다. 순위는 댓글 수로만 정합니다.',
                         [('주간 베스트', '/weekly/'), (label, '')]) + issue_body(sn)
        write(f'/weekly/{sn["id"]}/', layout(f'주간 팬 보드 베스트 {label}', body, path=f'/weekly/{sn["id"]}/',
                                          description=f'{label} 팬 보드 인기 글'), lastmod=sn['end'])
    latest = snaps[0]
    archive = ''.join(f'<li><a href="/weekly/{sn["id"]}/">{esc(sn["start"])} ~ {esc(sn["end"])} · 글 {sn["posts"]}편</a></li>' for sn in snaps)
    body = page_head('WEEKLY<span class="accent">.</span> <span class="kr">주간 팬 보드 베스트</span>',
                     '매주 월요일, 지난 한 주 팬 보드 인기 글을 모읍니다.', [('주간 베스트', '')]) + issue_body(latest) + \
        f'<div class="wrap prose" style="max-width:960px;margin-left:0"><h2>지난 호</h2><ul>{archive}</ul></div>'
    write('/weekly/', layout('주간 팬 보드 베스트', body, path='/weekly/', description='지난 한 주 SFANDOM 팬 보드 인기 글'))


def build_feeds():
    """전체 · 리그별 · 팀별 RSS 와 구독 안내 페이지(/feed/)."""
    out = ROOT / 'feed'
    (out / 'team').mkdir(parents=True, exist_ok=True)

    def put(rel: str, title: str, desc: str, arts: list):
        (out / rel).write_text(feeds.render(BASE, f'/feed/{rel}', title, desc, arts), encoding='utf-8')

    put('all.xml', 'SFANDOM 전체 소식', 'SFANDOM의 뉴스 · 분석 · 매거진 최신 글', ARTICLES)
    league_links = [('all', '전체', '/feed/all.xml', len(ARTICLES))]
    for lg in ('mlb', 'nba', 'nfl', 'soccer'):
        arts = [a for a in ARTICLES if str(a.league).lower() == lg]
        if arts:
            put(f'{lg}.xml', f'SFANDOM {feeds.LEAGUE_NAME[lg]} 소식', f'SFANDOM {feeds.LEAGUE_NAME[lg]} 최신 글', arts)
            league_links.append((lg, feeds.LEAGUE_NAME[lg], f'/feed/{lg}.xml', len(arts)))
    feed_icons = {'all': '🌟', 'mlb': '⚾', 'nba': '🏀', 'nfl': '🏈', 'soccer': '⚽'}
    chips = ''.join(
        f'<a class="feed-league-link" href="{u}" title="{esc(n)} RSS 주소 열기">'
        f'<span class="feed-league-icon" aria-hidden="true">{feed_icons.get(key, "🔔")}</span>'
        f'<span class="feed-league-name">{esc(n)} 소식</span><small>{c}편</small></a>'
        for key, n, u, c in league_links)
    blocks = ''
    for lg, teams in feeds.TEAMS.items():
        cells = ''
        for abbr, _, _, name in teams:
            arts = [a for a in ARTICLES if abbr in feeds.team_matches(a, lg)]
            if not arts:
                continue
            put(f'team/{lg}-{abbr.lower()}.xml', f'SFANDOM {name} 소식', f'SFANDOM의 {name} 관련 글', arts)
            cells += (f'<a class="feed-team-card" href="/feed/team/{lg}-{abbr.lower()}.xml"'
                      f' title="{esc(name)} RSS 주소 열기">'
                      f'{badge(abbr, team_color(abbr, lg), league=lg)}'
                      f'<span class="feed-team-name">{esc(name)}</span>'
                      f'<small class="feed-team-count">{len(arts)}편</small>'
                      f'<span class="feed-team-arrow" aria-hidden="true">↗</span></a>')
        if cells:
            blocks += (f'<section class="feed-league-section" aria-label="{lg.upper()} 팀별 소식">'
                       f'<h2 class="feed-league-heading"><span aria-hidden="true">{feed_icons.get(lg, "⭐")}</span>'
                       f' {lg.upper()} <small>내 팀 고르기</small></h2>'
                       f'<div class="feed-team-grid">{cells}</div></section>')
    body = page_head('MY TEAM<span class="accent">.</span> <span class="kr">🔔 내 팀 구독</span>',
                     '응원하는 팀이 있다면 여기로! 팀별 새 글을 나만의 RSS 리더에 모아 보세요.', [('내 팀 구독', '')]) + (
        f'<div class="wrap sec feed-page-wrap">'
        f'<div class="feed-intro"><span class="feed-intro-icon" aria-hidden="true">💌</span>'
        f'<div><strong>어떤 팀이 좋아요?</strong><p>아래에서 종목이나 팀을 골라보세요. 숫자는 지금 읽을 수 있는 글 수예요.</p></div></div>'
        f'<h2 class="feed-subheading">🌈 리그별 소식 보기</h2>'
        f'<div class="feed-league-grid">{chips}</div>'
        f'{blocks}'
        f'<div class="feed-guide"><h2>💡 구독하는 방법</h2>'
        f'<p>원하는 팀을 누르면 RSS 주소가 열려요. 주소를 복사해서 Feedly나 Inoreader 같은 RSS 리더에 등록하면 새 글을 한곳에서 볼 수 있어요.</p>'
        f'<p class="feed-guide-note">※ RSS는 앱 알림이나 자동 회원 가입이 아니에요. 아직 글이 없는 팀은 첫 글이 발행되면 목록에 나타납니다.</p>'
        f'</div></div>')
    write('/feed/', layout('RSS 구독', body, path='/feed/', description='SFANDOM 전체·리그별·팀별 RSS 구독 안내'))



# ───────────────────────── 종목별 경기 센터 · 외부 확인 스냅샷 ─────────────────────────
def game_snapshot() -> dict:
    path = CONTENT / 'games-snapshot.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data.get('leagues'), dict) else {'leagues': {}}
    except (OSError, ValueError, TypeError):
        return {'leagues': {}}


SCORE_LABELS = {
    'scheduled': '예정', 'live': '진행 중 · 확인 시각 기준',
    'final': '종료', 'postponed': '연기', 'cancelled': '취소',
}
SCORE_LEAGUES = (('MLB', '⚾'), ('NBA', '🏀'), ('NFL', '🏈'), ('NHL', '🏒'))


def game_clock(kst: str) -> dt.datetime | None:
    try:
        value = dt.datetime.fromisoformat(kst)
        return value if value.tzinfo else None
    except (TypeError, ValueError):
        return None


def game_card(g: dict, stale: bool = False) -> str:
    when = game_clock(g.get('start_kst', ''))
    if not when:
        return ''
    state = g.get('status')
    if state not in SCORE_LABELS:
        return ''
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    label = SCORE_LABELS[state]
    if state == 'scheduled' and when < now - dt.timedelta(minutes=20):
        label = '결과 확인 중'
    elif stale and state == 'live':
        label = '마지막 확인 당시 진행 중'
    elif stale and state == 'scheduled':
        label = '예정 · 갱신 지연'
    scores = ''
    if state in ('live', 'final'):
        try:
            av, hv = int(g['away_score']), int(g['home_score'])
            if 0 <= av <= 300 and 0 <= hv <= 300:
                scores = f'<strong class="sf-scores__numbers">{av}<span>:</span>{hv}</strong>'
        except (ValueError, TypeError, KeyError):
            pass
    url = str(g.get('source_url', ''))
    url = url if url.startswith('https://www.espn.com/') else ''
    row_tag, link = ('a', f' href="{esc(url)}" target="_blank" rel="noopener"') if url else ('div', '')
    badge_text = '자료 시각 기준'
    if state == 'final':
        badge_text = 'FINAL'
    elif state == 'live' and not stale:
        badge_text = 'LIVE · 지연 제공'
    return (f'<{row_tag} class="sf-scores__game"{link}>'
            f'<span class="sf-scores__time"><time datetime="{esc(g["start_kst"])}">{when.strftime("%m.%d %H:%M")}</time>'
            f'<small>{esc(label)}</small></span>'
            f'<span class="sf-scores__teams"><b title="{esc(g.get("away_name", ""))}">{esc(g.get("away", "?"))}</b>'
            f'<i aria-hidden="true">VS</i><b title="{esc(g.get("home_name", ""))}">{esc(g.get("home", "?"))}</b></span>'
            f'{scores}<span class="sf-scores__tag">{esc(badge_text)}</span>'
            f'</{row_tag}>')


def game_age(checked_at: str) -> tuple[str, bool]:
    checked = game_clock(checked_at)
    if not checked:
        return '확인 시각 없음', True
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    return (checked.astimezone(now.tzinfo).strftime('%m.%d %H:%M KST'),
            now - checked > dt.timedelta(hours=2))


def game_sections(brief: bool = False) -> str:
    snapshot = game_snapshot()
    output = []
    for league, icon in SCORE_LEAGUES:
        details = snapshot.get('leagues', {}).get(league) or {}
        verified, stale = game_age(details.get('checked_at', ''))
        games = [g for g in details.get('games', []) if game_clock(g.get('start_kst', ''))]
        games.sort(key=lambda g: (g.get('start_kst', ''), g.get('id', '')))
        if brief:
            now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
            games.sort(key=lambda g: (abs((game_clock(g['start_kst']) - now).total_seconds()),g['start_kst']))
            games = games[:(4 if league == 'MLB' else 2)]
            games.sort(key=lambda g: g['start_kst'])
        else:
            games = games[-50:]
        cards = ''.join(game_card(g, stale) for g in games)
        if not cards:
            cards = '<p class="sf-scores__empty">이 시간대 확인된 경기 정보가 없습니다. 다음 자료 갱신을 기다려 주세요.</p>'
        note = ' · 일부 날짜 확인 지연' if details.get('coverage') == 'partial' else ''
        if details.get('error'):
            note += ' · 외부 자료 연결 지연'
        output.append(f'<section class="sf-scores__league" aria-label="{league} 경기 결과와 일정">'
                      f'<div class="sf-scores__league-head"><h3>{icon} {league}</h3>'
                      f'<small>확인 {esc(verified)}{esc(note)}</small></div>'
                      f'<div class="sf-scores__rows">{cards}</div></section>')
    return ''.join(output)


def game_preview() -> str:
    return (f'<section class="wrap sf-scores sf-scores--preview" aria-labelledby="scorePreviewTitle">'
            f'<div class="sf-scores__heading"><div><span class="sf-scores__eyebrow">GAME CENTER · KST</span>'
            f'<h2 id="scorePreviewTitle">경기 일정 <span>·</span> 최종 결과</h2>'
            f'<p>MLB·NBA·NFL·NHL · 외부 기록 제공처 확인 시각 기준</p></div>'
            f'<a class="pill" href="/games/">전체 경기 보기 →</a></div>'
            f'<div class="sf-scores__grid">{game_sections(True)}</div></section>')


def build_games() -> None:
    snapshot = game_snapshot()
    updated, _stale = game_age(snapshot.get('updated_at', ''))
    intro = page_head('GAME <span class="accent">CENTER.</span>',
        'MLB·NBA·NFL·NHL 경기 일정과 결과를 한국시간으로 확인합니다. 실시간 중계가 아닌 외부 기록 제공처 확인 시각 기준입니다.',
        [('GAME CENTER', '')])
    body = (intro + f'<div class="wrap sf-scores sf-scores--page">'
            f'<div class="sf-scores__heading"><div><span class="sf-scores__eyebrow">SCORES & FIXTURES · KST</span>'
            f'<h2>종목별 경기 현황</h2><p>최종 수집 시각 {esc(updated)} · ESPN 경기 기록 보조 자료. '
            f'점수와 경기 상태는 출처 페이지에서 다시 확인할 수 있습니다.</p></div></div>'
            f'<div class="sf-scores__grid">{game_sections()}</div>'
            f'<p class="sf-scores__foot">※ 예정 시간이 지났다고 종료로 표시하지 않습니다. '
            f'기록 제공처가 확정한 점수만 FINAL로 표시하며, 자료 수집이 지연되면 마지막 확인 시각을 함께 표시합니다. '
            f'KBO는 데이터 제공처 검증 전까지 자동 수집 대상에서 제외합니다.</p></div>')
    write('/games/', layout('경기 일정·결과 | SFANDOM', body, path='/games/',
         description='MLB NBA NFL NHL 경기 일정과 결과, KST 시간 및 마지막 확인 시각.'),
         search={'u': '/games/', 't': '경기 일정·결과', 's': 'MLB NBA NFL NHL', 'k': 'GAME CENTER',
                 'd': TODAY.replace('-', '.'), 'x': '경기 스코어 및 일정 KST'})


def clean_generated():
    for d in GENERATED_DIRS:
        shutil.rmtree(ROOT / d, ignore_errors=True)


def main():
    clean_generated()
    prepare_weekly()
    build_home()
    for a in ARTICLES:
        build_article(a)
    build_lists()
    build_hubs()
    build_games()
    build_community()
    build_sitemap()
    build_static()
    build_feeds()
    build_weekly()
    build_meta_files()
    print(f'built {len(PAGES)} indexable pages, {len(ARTICLES)} articles')


if __name__ == '__main__':
    main()
