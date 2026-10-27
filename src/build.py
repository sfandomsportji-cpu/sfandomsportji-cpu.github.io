#!/usr/bin/env python3
"""SFANDOM 정적 사이트 빌더 (외부 패키지 없음).

    python3 src/build.py

src/content/ 의 글(.md)·데이터(.json)·페이지 조각(.html)을 읽어 저장소 루트에
완성된 HTML·sitemap.xml·search-index.json 을 만듭니다. GitHub Pages는 결과물을 그대로 서비스합니다.
"""
from __future__ import annotations

import datetime as dt
import html
import math
import json
import pathlib
import re
import shutil
import sys
import time
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


def av(rel: str) -> str:
    """자산 파일 내용으로 만든 짧은 버전표. 파일이 바뀔 때만 주소가 바뀌어 브라우저 캐시가 즉시 갱신된다."""
    import hashlib
    f = ROOT / rel.lstrip('/')
    return hashlib.md5(f.read_bytes()).hexdigest()[:8] if f.is_file() else VER

# 빌더가 만드는 최상위 경로 (다시 빌드할 때 지우고 새로 씀)
GENERATED_DIRS = ['news', 'special', 'mlb', 'kbo', 'nba', 'soccer', 'analysis', 'community', 'magazine',
                  'about', 'contact', 'sitemap', 'feed', 'weekly', 'privacy', 'terms', 'rules', 'legal', 'ads-cookies', 'search', 'games', 'links']

esc = lambda s: html.escape(str(s or ''), quote=True)

sys.dont_write_bytecode = True  # 빌드가 임시 파일(__pycache__)을 남기지 않게
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / 'tools'))
from fetch_logos import SOURCES as LOGO_SOURCES  # noqa: E402  (리그별 팀 ID · 공식 로고 주소)
import feeds  # noqa: E402  (RSS 피드 생성)
import weekly  # noqa: E402  (주간 인기 글 스냅샷)
from build_article_cards import card_name, is_match_card  # noqa: E402  (글별 공유 카드 파일명)
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
        self.image = fm.get('image', '')  # 일부 기사에 이미지가 없어도 빌드 유지
        # KAIRO 전망·분석 기사처럼 에디션/사진 출처 머리말이 없는 글도 빌드가 멈추지 않게 기본값을 둔다
        self.credit = fm.get('credit', '')
        self.image_alt = fm.get('image_alt', '')
        self.edition = fm.get('edition', '')
        self.kicker = fm.get('kicker', '')
        self.meta = fm.get('meta', '')
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
ARTICLE_URLS = {a.url for a in ARTICLES}  # 기사 바로 밑 토론(댓글·답글)이 붙는 페이지
EDITIONS = json.loads((CONTENT / 'editions.json').read_text(encoding='utf-8'))
SPECIALS = json.loads((CONTENT / 'specials.json').read_text(encoding='utf-8'))
SOCCER_LOGOS = json.loads((CONTENT / 'soccer_logos.json').read_text(encoding='utf-8'))
PS = json.loads((CONTENT / 'postseason-2026.json').read_text(encoding='utf-8'))
NBA = json.loads((CONTENT / 'nba-2026.json').read_text(encoding='utf-8'))
RECORDS = json.loads((CONTENT / 'analysis-records.json').read_text(encoding='utf-8'))
BY_KEY = {a.file[:-3]: a for a in ARTICLES}


def auto_editions() -> None:
    """손으로 쓴 에디션이 없는 날짜는, 그날 `edition` 값을 가진 글을 묶어 에디션을 자동으로 만든다(분석 먼저, 우선순위 순)."""
    days = sorted({getattr(a, 'edition', '') for a in ARTICLES if getattr(a, 'edition', '')})
    for d in days:
        if d in EDITIONS or d < max(EDITIONS):
            continue
        group = sorted([a for a in ARTICLES if getattr(a, 'edition', '') == d],
                       key=lambda a: (a.kind != 'analysis', -getattr(a, 'priority', 0), a.file))
        games = [a for a in group if a.kind == 'analysis' and getattr(a, 'away', '')]
        if not games:
            continue
        leagues = ' · '.join(dict.fromkeys(a.league for a in group))
        names = ', '.join(f"{a.away}–{a.home}" for a in games[:5])
        m, dd = int(d[5:7]), int(d[8:10])
        EDITIONS[d] = {
            'title': f'{m}월 {dd}일, 오늘의 분석 {len(games)}경기',
            'subtitle': f'SFANDOM × KAIRO · {leagues}',
            'intro': f'{m}월 {dd}일 에디션. {names} 경기의 분석과 어제 경기 결과를 묶었습니다. 모든 시간은 한국시간(KST)입니다.',
            'items': [a.file[:-3] for a in group], 'auto': True}


auto_editions()
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


_NAVER_PLAYER_KEYS: dict[str, tuple[str, str, int]] = {}


def naver_player(item: dict) -> tuple[str, str, int]:
    """내 네이버 블로그 영상 글의 (영상 번호, 재생 키, 키를 받은 시각). 빌드 때 글 페이지에서 받아 오며, 못 받으면 ('', '', 0).

    재생 키는 오래 쓰면 만료되므로 받은 시각(초)을 카드에 함께 적어 두고, 브라우저가 30분이 지난 키는 쓰지 않고 네이버 원문으로 엽니다.

    못 받은 카드는 지금처럼 네이버 원문 링크로만 열립니다. 이 값은 공개 영상의 재생용 값이라 HTML에 들어가도 됩니다.
    """
    m = re.fullmatch(r'https://blog\.naver\.com/sfandomsport/(\d{8,20})', str(item.get('link') or '').split('?', 1)[0])
    if not m:
        return ('', '', 0)
    no = m.group(1)
    if no not in _NAVER_PLAYER_KEYS:
        found = ('', '', 0)
        try:
            req = urllib.request.Request(f'https://m.blog.naver.com/sfandomsport/{no}',
                                         headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)'})
            page = urllib.request.urlopen(req, timeout=6).read(700_000).decode('utf-8', 'replace')
            vid = re.search(r'"vid"\s*:\s*"([A-Z0-9]{20,64})"', page)
            key = re.search(r'"inkey"\s*:\s*"(V[A-Za-z0-9_.=-]{30,300})"', page)
            if vid and key:
                found = (vid.group(1), key.group(1), int(time.time()))
        except Exception as exc:  # 네트워크 실패는 조용히: 카드는 원문 링크로 동작
            print(f'naver player key {no}: {exc.__class__.__name__}')
        _NAVER_PLAYER_KEYS[no] = found
    return _NAVER_PLAYER_KEYS[no]


def blog_card(p: dict) -> str:
    label = SITE['blogs'][p['source']]['label']
    img = f'<div class="thumb"><img src="{esc(blog_img(p["image"]))}" alt="" loading="lazy" referrerpolicy="no-referrer"></div>' if p.get('image') else '<div class="thumb blog-thumb" aria-hidden="true"><span>' + ('G' if p['source'] == 'google' else 'N') + '</span></div>'
    vid, inkey, got = naver_player(p) if p['source'] == 'naver' else ('', '', 0)
    player = f' data-vid="{esc(vid)}" data-inkey="{esc(inkey)}" data-inkey-at="{got}"' if vid and inkey else ''
    if player:
        img = img[:-len('</div>')] + '<span class="play-badge" aria-hidden="true">▶</span></div>'
    return (f'<a class="mag lift" data-date="{esc(p.get("date", ""))}" data-src="{p["source"]}" href="{esc(p["link"])}" target="_blank" rel="noopener"{player}>{img}<div class="body">'
            f'<span class="tag red">{label}</span><h3>{esc(p["title"])}</h3><p>{esc(_clip(p.get("summary", ""), 180))}</p>'
            f'<span class="tag">{p.get("date", "").replace("-", ".")} · {"▶ 바로 재생" if player else "블로그에서 읽기 ↗"}</span></div></a>')


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


def render_split(b: str) -> str:
    """두 화면 분할 — 팀 머리줄(`팀 | 부제`)이 나오면 새 칸, `이름 | 역할 | 설명` 줄은 선수·감독 카드. 역할이 '감독'으로 시작하면 감독 카드."""
    lines = b.splitlines()
    label = lines[0][9:].strip() or 'SPLIT VIEW'
    cols, cur = [], None
    for ln in lines[1:]:
        if ln.strip() == ':::':
            break
        parts = [x.strip() for x in ln.split('|')]
        if parts[0] == '@photo' and len(parts) >= 2 and cur is not None:
            # 사진 줄 — 직전 카드가 있으면 그 카드에, 없으면 칸 머리에 붙인다. 파일이 없으면(보관 기간 만료) 조용히 건너뛴다.
            if (ROOT / parts[1].lstrip('/')).exists():
                ph = (parts[1], parts[2] if len(parts) > 2 else '')
                if cur['cards']:
                    cur['cards'][-1] = cur['cards'][-1][:3] + (ph,)
                else:
                    cur['photo'] = ph
            continue
        if len(parts) == 2 and parts[0]:
            cur = {'team': parts[0], 'sub': parts[1], 'cards': []}
            cols.append(cur)
        elif len(parts) >= 3 and cur is not None:
            cur['cards'].append((parts[0], parts[1], ' | '.join(parts[2:]), None))
    html = ''
    for c in cols[:2]:
        def img(ph, cls):
            return f'<img class="{cls}" src="{esc(ph[0])}" alt="{esc(ph[1])}" loading="lazy">' if ph else ''
        cards = ''.join(
            f'<article class="split-card{" mgr" if role.startswith("감독") else ""}{" has-photo" if ph else ""}">{img(ph, "split-face")}<div><h4>{esc(name)}<small>{esc(role)}</small></h4><p>{inline(text)}</p></div></article>'
            for name, role, text, ph in c['cards'])
        html += f'<div class="split-col"><div class="split-head"><b>{esc(c["team"])}</b><span>{esc(c["sub"])}</span></div>{img(c.get("photo"), "split-trio")}{cards}</div>'
    return f'<section class="split" aria-label="{esc(label)}">{html}</section>'


def render_body(a: Article) -> str:
    out = []
    for block in re.split(r'\n{2,}', a.body):
        b = block.strip()
        if not b:
            continue
        if b.startswith('::: stats'):
            rows = [r.split('|', 1) for r in b.splitlines()[1:-1] if '|' in r]
            cells = ''.join(f'<div class="stat"><b>{esc(v.strip())}</b><span>{esc(l.strip())}</span></div>' for v, l in rows)
            out.append(f'<div class="stats">{cells}</div>')
        elif b.startswith('::: split'):
            out.append(render_split(b))
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
    return '\n'.join(out)


# ───────────────────────── 조각 ─────────────────────────
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
    """Use existing local photographs only; never hotlink or substitute team logos."""
    if not a.image or not a.image.startswith('/assets/photos/'):
        return ''
    if not (ROOT / a.image.lstrip('/')).is_file():
        return ''
    return (f'<div class="thumb"><img src="{esc(a.image)}" alt="{esc(a.image_alt)}" '
            f'loading="lazy" decoding="async"></div>')



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
    st = f' style="{logo_style(f"{league}/{abbr.lower()}.svg", LOGO_FIT_PLAIN)}"' if f.exists() else ''
    return (f'<span class="tlogo-wrap {size}" data-abbr="{esc(abbr)}" style="--c:{color}" title="{esc(abbr)}">'
            f'<img class="tlogo" src="{src}" alt="{esc(abbr)}"{st} width="40" height="40" loading="lazy" decoding="async" referrerpolicy="no-referrer"></span>')


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


def soccer_badge(name: str, size: str = '') -> str:
    """축구 구단 로고(assets/teams/soccer/2026-27). soccer_logos.json에 없는 팀은 빈 문자열."""
    rel = SOCCER_LOGOS.get(name.upper().strip())
    if not rel:
        return ''
    return (f'<span class="tlogo-wrap {size}" data-abbr="{esc(name)}" style="--c:#444" title="{esc(name)}">'
            f'<img class="tlogo" src="/assets/teams/soccer/2026-27/{rel}" alt="{esc(name)}" style="{soccer_logo_style(rel, LOGO_FIT_PLAIN)}" width="40" height="40" '
            f'loading="lazy" decoding="async"></span>')


def split_teams(a: Article) -> tuple[str, str]:
    t = re.split(r'\s+(?:at|vs\.?|@)\s+', a.title.rstrip('.'), maxsplit=1, flags=re.I)
    return (t[0], t[1]) if len(t) > 1 else (a.title.rstrip('.'), '')


def matchup_strip(a: Article) -> str:
    """분석 글 상단의 대진 표시 (팀 로고 + 팀 이름)."""
    if a.league == 'SOCCER' and soccer_badge(getattr(a, 'away', '')) and soccer_badge(getattr(a, 'home', '')):
        return (f'<div class="mc-stage in-article"><div class="mc-team">{soccer_badge(a.away, "lg")}<small>AWAY</small><span class="display">{esc(a.away.upper())}</span></div>'
                f'<span class="mc-vs">VS</span><div class="mc-team r">{soccer_badge(a.home, "lg")}<small>HOME</small><span class="display">{esc(a.home.upper())}</span></div></div>')
    if not getattr(a, 'teams', None):
        return ''
    left, right = split_teams(a)
    return (f'<div class="mc-stage in-article"><div class="mc-team">{team_badge(a, 0)}<small>AWAY</small><span class="display">{esc(left.upper())}</span></div>'
            f'<span class="mc-vs">VS</span><div class="mc-team r">{team_badge(a, 1)}<small>HOME</small><span class="display">{esc(right.upper())}</span></div></div>')




def an_vote(a: Article) -> str:
    """경기별 한 줄 투표. 끝난 경기는 결과만 보여 주고, 서버 응답이 없으면 JS가 칸을 숨긴다(hidden 기본)."""
    away, home = getattr(a, 'away', ''), getattr(a, 'home', '')
    res = game_result(a)
    ro = ' data-readonly="1"' if res and res['status'] == 'final' else ''
    gid = a.file[:-3][11:]  # 날짜를 뗀 글 이름 = 경기 투표 id
    q = '누가 이길까?' if not ro else '투표 결과'
    return (f'<div class="an-vote" data-vote="{esc(gid)}"{ro} hidden><b>{q}</b>'
            f'<button type="button" data-side="away"><span>{esc(away)}</span><em></em></button>'
            f'<button type="button" data-side="home"><span>{esc(home)}</span><em></em></button><small></small></div>')


def an_recap_link(a: Article) -> str:
    res, rc = game_result(a), recap_for(a)
    if res and res['status'] == 'final' and rc:
        return f'<a class="an-read" href="{rc.url}">경기 결과 기사 →</a>'
    return ''


KBO_LOGO = {'KIA': 'KIA', 'LG': 'LG', 'KT': 'KT', 'NC': 'NC', 'SSG': 'SSG', 'DOOSAN': 'doosan', 'HANWHA': 'hanwha',
            'KIWOOM': 'kiwoom', 'LOTTE': 'lotte', 'SAMSUNG': 'samsung'}


def kbo_logo(name: str) -> str:
    """KBO 구단 이름(예: 'LG TWINS')의 첫 낱말로 assets/teams/kbo/ 로고 경로를 찾는다. 없으면 빈 문자열."""
    key = (name or '').split(' ')[0].upper()
    f = KBO_LOGO.get(key)
    return f'/assets/teams/kbo/{f}.png' if f and (ROOT / 'assets' / 'teams' / 'kbo' / f'{f}.png').is_file() else ''


def photo_small(a):
    """직접 받은 사진이 가로 1000px 미만이면 (넓은 칸에서 키우면 흐려지므로) 원본 크기로만 표시."""
    try:
        from PIL import Image
        w = Image.open(ROOT / a.image.lstrip('/')).size[0]
    except Exception:
        return ''
    return w if w < 1000 else ''


def photo_cls(a):
    """직접 받은 사진: 가로 1000px 이상이면 16:9 꽉 채움, 작으면 원본 크기를 넘겨 키우지 않고 가운데 배치."""
    if not a.image.startswith('/assets/photos/'):
        return ''
    try:
        from PIL import Image
        w = Image.open(ROOT / a.image.lstrip('/')).size[0]
    except Exception:
        return ' photo'
    return ' photo' if w >= 1000 else f' photo-sm" style="--pw:{w}px'


def an_logos(a: Article) -> str:
    """사진 밑에 두 팀 로고만 — KBO 두 팀 로고가 모두 있을 때."""
    if getattr(a, 'league', '') != 'KBO':
        return ''
    la, lh = kbo_logo(getattr(a, 'away', '')), kbo_logo(getattr(a, 'home', ''))
    if not (la and lh):
        return ''
    def st(p):
        key = p.removeprefix('/assets/teams/')
        return f' style="{logo_style(key, LOGO_FIT_PLAIN).split(";width")[0]};height:{logo_size(key, LOGO_FIT_PLAIN)[1] * 100:.1f}%;width:auto"'
    return (f'<span class="an-logos"><span><img src="{la}" alt="{esc(a.away)}"{st(la)} loading="lazy"></span>'
            f'<span><img src="{lh}" alt="{esc(a.home)}"{st(lh)} loading="lazy"></span></span>')


def an_banner(a: Article) -> str:
    """접힌 줄 위쪽에 보이는 자료사진 띠 — 직접 받은 사진(/assets/photos/)이 있을 때만."""
    if a.image.startswith('/assets/photos/') and (ROOT / a.image.lstrip('/')).is_file():
        return (f'<span class="an-media"><img class="an-banner{" sm" if photo_small(a) else ""}"{f' style="--pw:{photo_small(a)}px"' if photo_small(a) else ""} src="{esc(a.image)}" alt="{esc(a.image_alt)}" loading="lazy" decoding="async">'
                f'{an_logos(a)}</span>')
    return ''


def an_verdict_chip(a: Article) -> str:
    if not getattr(a, 'verdict', ''):
        return ''
    return f'<span class="an-vchip"><b>최종 전망</b> {esc(a.verdict)} · {esc(getattr(a, "verdict_sub", "").replace("예상 스코어 ", ""))}</span>'


def an_detail(a: Article) -> str:
    """펼쳤을 때 보이는 상세: 경기 숫자(stats 블록)와 KAIRO VIEW(angle 블록), 전문 링크."""
    stats, view_title, view = [], 'KAIRO VIEW', ''
    m = re.search(r'::: stats\n(.*?)\n:::', a.body, re.S)
    if m:
        for line in m.group(1).splitlines():
            if '|' in line:
                v, l = [x.strip() for x in line.split('|', 1)]
                stats.append((v, l))
    m = re.search(r'::: angle ([^\n]*)\n(.*?)\n:::', a.body, re.S)
    if m:
        view_title, view = m.group(1).strip() or view_title, re.sub(r'\s+', ' ', m.group(2)).strip()
    items = ''.join(f'<li><b>{esc(v)}</b><span>{esc(l)}</span></li>' for v, l in stats)
    ph = ''
    if a.image.startswith('/assets/photos/') and (ROOT / a.image.lstrip('/')).is_file():  # 직접 받은 자료사진만(3일 보관) — 홈에서도 펼치면 보이게
        ph = f'<span class="an-media"><span class="an-photo{" sm" if photo_small(a) else ""}" role="img" aria-label="{esc(a.image_alt)}" style="background-image:url({esc(a.image)})"></span>{an_logos(a)}</span>'
    vd = ''
    if getattr(a, 'verdict', ''):  # 사람이 확정한 최종 전망 — 펼친 칸 사진 옆에 한눈에
        sm = ''.join(f'<li>{esc(x)}</li>' for x in (getattr(a, 'summary', None) or []))
        vd = (f'<div class="an-verdict"><b>SFANDOM 최종 전망</b><strong>{esc(a.verdict)}</strong>'
              f'<em>{esc(getattr(a, "verdict_sub", ""))}</em>' + (f'<ul>{sm}</ul>' if sm else '') + '</div>')
    return (f'<div class="an-open{" has-verdict" if vd else ""}">{ph}{vd}<ul class="an-stats">{items}</ul>'
            f'<p class="an-view"><b>{esc(view_title)}</b>{esc(view)}</p>{an_vote(a)}'
            f'<div class="an-links"><a class="an-read" href="{a.url}">분석 전문 읽기 →</a>{an_recap_link(a)}</div></div>')


def game_result(a: Article):
    """분석 글에 연결된 경기의 진행 상태. 글의 game(스냅샷 id)로 ESPN·NPB 스냅샷에서, 없으면 results.json(수동)에서 찾는다.
    반환: {'status','away','home','verdict'} 또는 None. verdict는 pick이 있고 경기가 끝났을 때만 'hit'/'miss'."""
    res = None
    gid = getattr(a, 'game', '')
    if gid:
        for lg in game_snapshot().get('leagues', {}).values():
            for g in lg.get('games', []):
                if g.get('id') == gid:
                    res = {'status': g.get('status'), 'away': g.get('away_score'), 'home': g.get('home_score')}
    if res is None:
        try:
            m = json.loads((CONTENT / 'results.json').read_text(encoding='utf-8')).get(a.file[:-3])
        except (OSError, ValueError):
            m = None
        if isinstance(m, dict):
            res = {'status': m.get('status', 'final'), 'away': m.get('away'), 'home': m.get('home')}
    if not res or res['status'] not in ('live', 'final'):
        return None
    if not all(isinstance(res[k], int) for k in ('away', 'home')):
        return None
    res['verdict'] = ''
    pick = getattr(a, 'pick', '')
    if pick in ('away', 'home') and res['status'] == 'final' and res['away'] != res['home']:
        res['verdict'] = 'hit' if (res['away'] > res['home']) == (pick == 'away') else 'miss'
    return res


def recap_for(a: Article):
    """같은 시리즈의 결과 기사(파일명 preview → recap, 날짜 무관) 중 가장 가까운 것."""
    stem = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', a.file[:-3])
    if not stem.endswith('-preview'):
        return None
    want = stem[:-len('-preview')] + '-recap'
    hit = [b for b in ARTICLES if re.sub(r'^\d{4}-\d{2}-\d{2}-', '', b.file[:-3]) == want]
    return hit[0] if hit else None


def hit_rate():
    """pick을 남긴 분석 중 끝난 경기의 (맞힌 수, 전체)."""
    done = [game_result(a) for a in ARTICLES if a.kind == 'analysis' and getattr(a, 'pick', '')]
    done = [r for r in done if r and r['verdict']]
    return sum(r['verdict'] == 'hit' for r in done), len(done)


def an_team(name: str, league: str) -> str:
    """분석 줄의 팀 표기. 축구는 로고를 이름 앞에 붙이고, 이름과 로고가 줄바꿈에서 갈라지지 않게 묶는다."""
    if league == 'SOCCER' and soccer_badge(name):
        return f'<span style="white-space:nowrap">{soccer_badge(name)}{esc(name)}</span>'
    return esc(name)


def analysis_row(a: Article, opened: bool = False) -> str:
    away, home = getattr(a, 'away', ''), getattr(a, 'home', '')
    if not (away and home):
        raise SystemExit(f'분석 줄에 대진(away/home)이 없음: {a.file}')
    day, _, clock = (getattr(a, 'kst', '') or '').partition(' ')
    tag = a.kicker.split('·')[-1].strip() if a.kicker else a.league
    if tag.upper().startswith(a.league.upper() + ' '):
        tag = tag[len(a.league) + 1:]
    labels = ['핵심', '변수', '시선']
    rows = {k: v for k, v in (getattr(a, 'glance', None) or [])}
    cells = ''.join(f'<span class="an-cell" data-label="{k}">{esc(rows.get(k, "-"))}</span>' for k in labels)
    res = game_result(a)
    state = ''
    if res:
        mark = {'hit': ' ✔', 'miss': ' ✘'}.get(res['verdict'], '')
        label = '종료' if res['status'] == 'final' else 'LIVE'
        state = (f'<em class="an-state" data-s="{res["status"]}" data-v="{res["verdict"]}">{label} {res["away"]}–{res["home"]}{mark}</em>')
    return (f'<details class="an-item" data-final="{1 if res and res["status"] == "final" else 0}" data-teams="{esc(away)}|{esc(home)}"{" open" if opened else ""}><summary class="an-row">{an_banner(a)}{an_verdict_chip(a)}'
            f'<span class="an-time"><b>{esc(clock or "-")}</b><small>{esc(day)} {esc(a.league)}</small>{state}</span>'
            f'<span class="an-match"><span class="an-names"><small>{esc(tag)}</small>'
            f'<span class="an-teams">{an_team(away, a.league)} <i>VS</i> {an_team(home, a.league)}</span></span></span>'
            f'{cells}<span class="an-go" aria-hidden="true">+</span></summary>{an_detail(a)}</details>')


# 오늘 축구 — 홈 가로 카드 줄 (편집부 일정표. 배당·확률 표기 없음, 킥오프는 한국시간)
SOCCER_TODAY = {
    'label': '10.20 (화) 새벽',
    'until': '2026-10-20T05:00:00+09:00',  # 이 시각(한국시간)이 지나면 홈에서 자동으로 내림. 새 일정은 label·matches·until 을 함께 갱신
    'matches': [
        ('01:30', '세리에 A', 'serie-a/ac-monza.png', '몬자', 'serie-a/cagliari-calcio.png', '칼리아리'),
        ('03:45', '세리에 A', 'serie-a/parma-calcio-1913.png', '파르마', 'serie-a/torino-fc.png', '토리노'),
        ('04:00', '프리미어리그', 'premier-league/tottenham-hotspur.png', '토트넘', 'premier-league/coventry-city.png', '코벤트리'),
        ('04:00', '라리가', 'la-liga/getafe-cf.png', '헤타페', 'la-liga/rayo-vallecano.png', '라요 바예카노'),
    ],
}


# 팀 로고 파일마다 안쪽 투명 여백·가로세로 비율이 달라 그대로 쓰면 크기가 들쭉날쭉하다(야구·농구·축구 공통).
# src/measure_logos.py 가 파일에서 실제 그림 영역을 실측해 logo_boxes.json 에 저장해 두며(원본은 수정하지 않음),
# 화면에서는 이 값으로 모든 로고를 같은 기준으로 맞춘다. 키는 assets/teams/ 아래 상대 경로.
try:
    LOGO_BOXES = json.loads((CONTENT / 'logo_boxes.json').read_text(encoding='utf-8'))
except Exception:
    LOGO_BOXES = {}


def logo_box(key: str) -> tuple:
    """((위·오른쪽·아래·왼쪽 투명 여백 %), 그림 가로/세로 비율). 실측값이 없으면 여백 없음·정사각으로 본다."""
    v = LOGO_BOXES.get(key)
    return (tuple(v[:4]), v[4]) if v else ((0, 0, 0, 0), 1.0)


# (기준 크기, 한 변 최대, 대각선 최대) — 상자 한 변을 1로 본 비율. 가로·세로 비율이 달라도 눈에 보이는 크기가 비슷하도록
# 가로세로의 기하평균을 맞추고, 상자(원형 배지 등)를 넘지 않게 제한한다.
LOGO_FIT_BADGE = (0.66, 0.80, 0.92)  # 홈 '오늘 SOCCER' 원형 배지
LOGO_FIT_PLAIN = (0.80, 0.96, 0.0)  # 글 안 대진·분석 목록·홈 카드: 눈에 보이는 면적(가로×세로)을 같게 맞추되 긴 변은 칸의 96% 이내, 가운데 정렬


try:  # 글자 위주의 가로로 긴 로고(레이커스 등)는 로고별 배율을 따로 보관 (src/content/logo_scale.json)
    LOGO_SCALE = {k: v for k, v in json.loads((CONTENT / 'logo_scale.json').read_text(encoding='utf-8')).items() if not k.startswith('_')}
except Exception:
    LOGO_SCALE = {}


def logo_size(key: str, fit: tuple) -> tuple:
    """상자 한 변을 1로 했을 때 보여 줄 (가로, 세로)."""
    _, asp = logo_box(key)
    g, cap, diag = fit
    if fit is LOGO_FIT_PLAIN:  # 면적 통일 + 긴 변 상한: 가로형·세로형·원형이 비슷한 크기로 보이게(로고별 배율 없음)
        w, h = g * math.sqrt(asp), g / math.sqrt(asp)
        k = min(1.0, cap / max(w, h))
        return w * k, h * k
    w, h = g * math.sqrt(asp), g / math.sqrt(asp)
    k = min(1.0, cap / w, cap / h, diag / math.hypot(w, h))
    m = LOGO_SCALE.get(key, 1.0) if fit is not LOGO_FIT_BADGE else 1.0
    return w * k * m, h * k * m


def logo_style(key: str, fit: tuple) -> str:
    inset, _ = logo_box(key)
    w, h = logo_size(key, fit)
    return f'object-view-box:inset({" ".join(f"{v:g}%" for v in inset)});width:{w * 100:.1f}%;height:{h * 100:.1f}%'


def soccer_logo_style(rel: str, fit: tuple) -> str:
    return logo_style(f'soccer/2026-27/{rel}', fit)


HOME_HIDE_MLB = True  # 홈에서만 MLB 노출 숨김 (False면 복원). /mlb/ 등 다른 페이지는 그대로
SHOW_HOME_SOCCER = True  # 홈 '오늘 SOCCER' 노출 스위치 (False면 홈에서만 숨김, 데이터·함수·CSS는 보존)


def soccer_today_active() -> bool:
    """SOCCER_TODAY['until'](한국시간) 이전일 때만 홈에 노출. 값이 없으면 항상 노출."""
    until = SOCCER_TODAY.get('until')
    if not until:
        return True
    return dt.datetime.now(dt.timezone.utc) < dt.datetime.fromisoformat(until)


SOCCER_LINKS = {}
for _a in ARTICLES:
    _m = {'monza-cagliari-20261019': '몬자', 'parma-torino-20261019': '파르마', 'tottenham-coventry-20261019': '토트넘', 'getafe-rayo-20261019': '헤타페'}
    if getattr(_a, 'slug', '') in _m:
        SOCCER_LINKS[_m[_a.slug]] = _a.url


def soccer_today() -> str:
    def logo(rel, name):
        return (f'<span class="sc-team"><span class="sc-logo"><img src="/assets/teams/soccer/2026-27/{rel}" alt="{esc(name)}" '
                f'style="{soccer_logo_style(rel, LOGO_FIT_BADGE)}" width="64" height="64" loading="lazy" decoding="async"></span><b>{esc(name)}</b></span>')
    cards = ''.join(
        f'<a class="sc-card" role="listitem" href="{SOCCER_LINKS.get(h, "/analysis/")}" aria-label="{esc(h)} 대 {esc(a)} {t} 킥오프, 분석 보기">'
        f'<span class="sc-tag">{esc(lg)} · {t} KST</span>'
        f'<span class="sc-vs">{logo(hl, h)}<i>VS</i>{logo(al, a)}</span>'
        f'</a>'
        for t, lg, hl, h, al, a in SOCCER_TODAY['matches'])
    return (f'<section class="wrap sec" id="today-soccer" aria-labelledby="tsTitle">'
            f'<div class="sec-head"><h2 class="sec-title" id="tsTitle">오늘 <span class="outline">SOCCER</span> '
            f'<span class="kr">{SOCCER_TODAY["label"]} {len(SOCCER_TODAY["matches"])}경기</span></h2>'
            f'</div>'
            f'<div class="sc-rail" role="list" tabindex="0" aria-label="오늘 축구 경기, 좌우로 넘겨 보기">{cards}</div>'
            f'<p class="sc-hint">옆으로 밀어서 전체 경기 보기 · 킥오프는 한국시간 · 확정 라인업 발표 후 분석에 반영</p></section>')


def today_analysis() -> str:
    """Keep the approved morning edition and surface newer analysis on home."""
    ed_latest = max(EDITIONS)
    pool = sorted([a for a in ARTICLES if a.kind == 'analysis' and getattr(a, 'away', '') and getattr(a, 'home', '')],
                  key=lambda a: (a.date, getattr(a, 'priority', 0)), reverse=True)
    pool = [a for a in pool if not getattr(a, 'hide_home', False)]  # front matter hide_home: true → 홈 분석 줄에서만 내림(글·목록은 유지)
    if not pool:
        raise SystemExit('홈 분석 줄에 쓸 분석 글(away/home 포함)이 없음')
    def start_kst(a):
        m = re.match(r'(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})', getattr(a, 'kst', '') or '')
        if not m:
            return None
        year = int(a.date[:4])
        return dt.datetime(year, int(m[1]), int(m[2]), int(m[3]), int(m[4]), tzinfo=dt.timezone(dt.timedelta(hours=9)))
    now_kst = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    live_specials = []  # 오늘(또는 이후) 날짜로 묶인 특집 — 홈에 경기 전부를 보여 준다
    for f in SPECIALS.get('features', []):
        sday, spicks = special_picks(f)
        if spicks and sday >= now_kst.date().isoformat():
            # 같은 날 종료된 특집 경기 프리뷰를 홈에서 계속 재노출하지 않는다.
            spicks = [a for a in spicks if (start_kst(a) and start_kst(a) >= now_kst - dt.timedelta(hours=1))
                      or (start_kst(a) is None and sday > now_kst.date().isoformat())]
            if spicks:
                live_specials.append((f, sday, spicks))
    in_special = {a.file for _, _, ps in live_specials for a in ps}
    if any(a.file not in in_special for a in pool):  # 특집 경기는 아래 특집 블록에 있으므로 위 3칸에서는 겹치지 않게 뺀다
        pool = [a for a in pool if a.file not in in_special]
    upcoming = sorted([a for a in pool if start_kst(a) and start_kst(a) >= now_kst - dt.timedelta(hours=1)], key=start_kst)
    if upcoming:  # 진행 예정 경기만 홈에 노출하고, 지난 프리뷰는 목록에 보존한다.
        picks = upcoming[:4]
        display_date = start_kst(picks[0]).date().isoformat()
    else:
        picks = []
        display_date = now_kst.date().isoformat()
    all_href = '/analysis/'
    all_label = '최신 분석 전체 →'
    feature_count = len(picks)
    header_sub = (f'{display_date.replace("-", ".")} 최신 분석 {feature_count}편' if picks
                  else '새 경기 분석 준비 중')
    hit, total = hit_rate()
    rate = f'<span data-rate title="경기 전에 남긴 예측과 실제 결과 기록">예측 {hit}/{total}</span>' if total else ''
    # 직접 받은 자료사진이 있는 글(오늘의 메인 특집)을 맨 위로 — 모든 줄은 접어 두고 사진 띠만 보이게
    picks = sorted(picks, key=lambda a: not (a.image.startswith('/assets/photos/') and (ROOT / a.image.lstrip('/')).is_file()))
    cards = ''.join(analysis_row(a, bool(upcoming) and getattr(a, 'league', '') == 'SOCCER') for a in picks)
    head = ('<div class="an-head" aria-hidden="true"><span>KST</span><span>MATCHUP</span>'
            '<span>핵심</span><span>변수</span><span>시선</span><span></span></div>')
    board = (f'<div class="an-board">{head}{cards}</div>' if picks else
             '<div class="an-board"><p class="sc-hint" style="padding:24px;margin:0">예정된 경기 프리뷰가 등록되면 이곳에 표시됩니다. 이전 경기 분석은 전체 목록과 복기 리포트에서 확인할 수 있습니다.</p></div>')
    special_blocks = ''.join(
        f'<div class="sec-head" style="margin-top:40px"><h2 class="sec-title">{esc(f["title_a"])} <span class="outline">{esc(f["title_b"])}</span> '
        f'<span class="kr">{esc(f["kr"])} {len(ps)}경기</span></h2><a class="more" href="/special/{f["id"]}/">특집 전체 →</a></div>'
        f'<div class="an-board">{head}{"".join(analysis_row(a, False) for a in ps)}</div>'
        for f, _, ps in live_specials)
    # 모닝 에디션 카드는 오늘(한국시간) 에디션일 때만 홈에 둔다 — 지난 에디션은 홈에서 내림(에디션 페이지·목록은 유지)
    show_edition = ed_latest >= now_kst.date().isoformat()
    edition_card = (f'<a class="review-link" href="/news/morning/{ed_latest}/">'
                    f'<span class="display" style="font-size:24px">MORNING EDITION</span>'
                    f'<span class="muted" style="font-size:14px">{ed_latest.replace("-", ".")} 에디션 · 전체 읽기 →</span></a>') if show_edition else ''
    foot_style = '' if show_edition else ' style="grid-template-columns:1fr"'
    return (f'<section class="wrap sec" id="today-analysis" aria-labelledby="taTitle">'
            f'<div class="sec-head"><h2 class="sec-title" id="taTitle">'
            f'SFANDOM &amp; KAIRO <span class="outline">ANALYSIS</span> '
            f'<span class="kr">{esc(header_sub)}</span>{rate}</h2>'
            f'<a class="more" href="{all_href}">{all_label}</a></div>'
            f'<div class="an-my" data-my hidden><b>MY TEAM</b><span data-my-chips></span></div>'
            f'{board}'
            f'{special_blocks}'
            f'<p class="sc-hint">경기 분석에 궁금한 점은 쪽지나 댓글로 남겨 주세요 · 킥오프는 한국시간 · 확정 라인업 발표 후 반영</p>'
            f'<div class="ta-foot"{foot_style}><a class="review-link" href="/analysis/review/">'
            f'<span class="display" style="font-size:24px">REVIEW <span class="accent">/</span> 복기 리포트</span>'
            f'<span class="muted" style="font-size:14px">경기 결과와 분석 과정을 비교합니다</span></a>'
            f'{edition_card}</div></section>')

def talk_icon() -> str:
    return ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linejoin="round" aria-hidden="true"><path d="M4 5h16v11H9l-5 4z"/></svg>')


def list_item(a: Article, h: str = 'h2') -> str:
    # 사진이 없는 글은 사진칸(자리표시 타일)을 아예 두지 않고, 대진이 있으면 글자로 'A VS B'만 적는다.
    if a.image:
        media, cls, vs = thumb(a), 'li', ''
    else:
        media, cls = '', 'li no-thumb'
        away, home = getattr(a, 'away', ''), getattr(a, 'home', '')
        vs = f'<span class="li-vs">{esc(away)} <i>VS</i> {esc(home)}</span>' if away and home else ''
    return (f'<a class="{cls}" href="{a.url}">{media}<div><span class="tag red">{esc(a.section)} · {esc(a.league)}</span>{vs}'
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


def meta_clip(text: str, limit: int = 150) -> str:
    """검색 결과·공유 미리보기용 설명문: 150자 안쪽으로, 가능하면 문장 끝에서 끊는다."""
    t = re.sub(r'\s+', ' ', text or '').strip()
    if len(t) <= limit:
        return t
    cut = t[:limit]
    ends = [m.end() for m in re.finditer(r'(?:다|요|\.|!|\?)(?=\s|$)', cut) if m.end() >= 60]
    if ends:
        return cut[:ends[-1]].strip()
    return cut[:cut.rfind(' ')].rstrip(' ,·') + '…' if ' ' in cut[40:] else cut.rstrip() + '…'


def layout(title: str, body: str, *, path: str, description: str = '', image: str = '', ld: list | None = None,
           noindex: bool = False, active: str = '', og_type: str = 'website') -> str:
    full_title = title if title.startswith('SFANDOM') else f'{title} | SFANDOM'
    desc = meta_clip(description or SITE['description'])
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
    cfg = {'root': '/', 'supabase': SITE['supabase']}
    lds = ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in (ld or []))
    robots = 'noindex,follow' if noindex else 'index,follow,max-image-preview:large'
    on_board = path == '/community/'
    on_article = path in ARTICLE_URLS
    thread_css = (f'<link rel="stylesheet" href="/assets/css/community-thread.css?v={VER}-v3">'
                  + (f'<link rel="stylesheet" href="/assets/css/community-admin.css?v={VER}-v1">' if on_board else '') if (on_board or on_article) else '')
    news_comments_css = (f'<link rel="stylesheet" href="/assets/css/news-comments.css?v={VER}-v2">' if on_article else '')
    thread_js = (f'<script src="/assets/js/community-thread.js?v={VER}-v6" defer></script>'
                 + (f'<script src="/assets/js/community-admin.js?v={VER}-v1" defer></script>' if on_board else '') if (on_board or on_article) else '')
    news_comments_js = (f'<script src="/assets/js/news-comments.js?v={VER}-v2" defer></script>' if on_article else '')
    vote_js = (f'<script src="/assets/js/game-vote.js?v={av("/assets/js/game-vote.js")}" defer></script><script src="/assets/js/my-team.js?v={av("/assets/js/my-team.js")}" defer></script>' if path == '/' else '')
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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bagel+Fat+One&family=Gowun+Dodum&family=Jua&family=Nunito:wght@500;600;700&display=swap">
<link rel="stylesheet" href="/assets/css/site.css?v={av("/assets/css/site.css")}">
{('<link rel="stylesheet" href="/assets/css/brand-story.css?v=20261013-identity-polish-v2">' if path == '/' else '')}
{('<link rel="stylesheet" href="/assets/css/about-page.css?v=20261013-purpose-v1">' if path == '/about/' else '')}
{('<link rel="stylesheet" href="/assets/css/naver-magazine.css?v=20261012-restored-thumbnails">' if path == '/magazine/' else '')}
{('<link rel="stylesheet" href="/assets/css/game-center.css?v=20261027-scores-logo-v1">' if path in ('/', '/games/') else '')}
{(f'<link rel="stylesheet" href="/assets/css/analysis-cycle.css?v={av("/assets/css/analysis-cycle.css")}">' if path in ('/analysis/', '/analysis/review/', '/analysis/mlb/2026-10-11-nlcs-dodgers-brewers-game1/') else '')}
{(f'<link rel="stylesheet" href="/assets/css/editorial-links.css?v={av("/assets/css/editorial-links.css")}">' if path.startswith(('/analysis/', '/news/', '/magazine/')) else '')}
{thread_css}{news_comments_css}
<script>window.SFANDOM={json.dumps(cfg, ensure_ascii=False)};</script>
{lds}
</head>
<body>
{header(active)}
<main id="main">
{body}
</main>
{footer()}
<script src="/assets/js/site.js?v={av("/assets/js/site.js")}" defer></script>
{thread_js}{news_comments_js}{vote_js}
</body>
</html>
'''


# ───────────────────────── 출력 ─────────────────────────
PAGES: list[dict] = []   # sitemap / search 용


# 본문이 얇은 기능 페이지(팬 보드·문의·주간 베스트)는 noindex + 사이트맵 제외(index=False). 내용이 충분해지면 두 곳을 되돌립니다.
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


def channel_chips() -> str:
    chips = '<a href="/community/" data-ch="">전체</a>' + ''.join(f'<a href="/community/?ch={quote(c)}" data-ch="{esc(c)}">{esc(c)}</a>' for c in CHANNELS)
    return f'<nav class="chips" aria-label="채널" data-chips>{chips}</nav>'


def game_threads(limit: int = 7, hide_mlb: bool = False) -> str:
    """경기 스레드: NBA 예정 경기와 MLB 챔피언십시리즈를 연결합니다."""
    rows = []
    for g in [x for x in nba_home_games() if not x.get('result')][:3]:
        tag = f'{g["away"]}@{g["home"]}'
        rows.append((f'NBA · {g["day"]}', badge(g["away"], NBA["colors"].get(g["away"], "#444"), league="nba") + '<i class="thread-vs">VS</i>' + badge(g["home"], NBA["colors"].get(g["home"], "#444"), league="nba"), tag, g['kst']))
    for d in ([] if hide_mlb else PS.get('lcs', [])):
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
    news = [a for a in ARTICLES if a.kind == 'news' and not (HOME_HIDE_MLB and a.league == 'MLB') and 'preseason' not in a.slug]  # 홈에서 프리시즌 기사 제외(글·목록은 유지)
    analysis = [a for a in ARTICLES if a.kind == 'analysis']
    hero = SITE['hero']
    g = BLOGS.get('google') or []
    hero_title = '<br>'.join(esc(x) for x in hero['title'].split('\n'))
    hero_text, hero_link = hero['text'], hero.get('link', '')
    hero_badge_en = hero.get("badge_en", "HOT ISSUE")
    hero_badge_kr = hero.get("badge_kr", "")
    hero_cta = "오늘 특집 읽기"
    # 이전 경기 날짜를 고정 노출하지 않도록 시즌 진행 상태를 빌드 시점에 반영한다.
    if hero.get("auto") and dt.datetime.now(dt.timezone(dt.timedelta(hours=9))) >= dt.datetime.fromisoformat(NBA["opening_kst"]):
        hero_badge_en = "NBA · 2026-27 REGULAR SEASON"
        hero_badge_kr = "최신 경기 일정과 확정 결과 · 한국시간"
        hero_title = "NBA 정규시즌<br>경기 일정과 결과"
        hero_text = "오늘 확인된 경기 결과와 다가오는 일정을 함께 확인하세요. 경기 정보는 외부 제공처의 마지막 확인 시각을 표시합니다."
        hero_link = "/games/"
        hero_cta = "경기 일정·결과 보기"
    if hero.get('use_latest_google_post') and g:
        hero_title, hero_text, hero_link = esc(g[0]['title']), g[0]['summary'], g[0]['link']
    wb_hit, wb_total = hit_rate()  # 리뉴얼 이후 pick을 남긴 분석과 종료 결과의 자동 대조만 센다(이전 복기 기록은 제외)
    _base = SITE.get('analysis_record_base') or {}  # 운영자가 직접 집계한 이전 누적 기록 + 이후 자동 대조
    wb_hit += int(_base.get('hit', 0))
    wb_total += int(_base.get('total', 0))
    win_band = (f'<a class="win-band" href="/analysis/review/" aria-label="분석 성공 {wb_hit}회, 전체 {wb_total}경기. 분석 기록 보기">'
                f'<span class="wb-label">ANALYSIS</span><b class="wb-main">분석 성공 <em>{wb_hit}</em><i>/{wb_total}</i></b>'
                f'<span class="wb-sub">경기 전에 남긴 전망과 실제 결과 기록 · 복기 리포트 →</span></a>') if wb_total else ''
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
                f'<p>{esc(cv.get("text", ""))}</p><div style="display:flex;gap:10px;flex-wrap:wrap"><a class="pill" href="/community/#write">팬 보드에서 얘기하기</a><a class="pill ghost" href="https://www.instagram.com/sportsfandom/" target="_blank" rel="noopener">인스타 팔로우 @sportsfandom</a></div></div></div>') if nba_media else ''
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
    season_started = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))) >= dt.datetime.fromisoformat(NBA["opening_kst"])
    home_heading = 'PRESEASON' if home_preseason else ('NBA SEASON' if season_started else 'TIP-OFF')
    home_status = (f'{sum(bool(g.get("result")) for g in home_games[:5])} FINAL · NEXT' if home_preseason
                   else ('LIVE SCHEDULE' if season_started else nba_dday()))
    home_cta = '프리시즌 일정' if home_preseason else ('정규시즌 일정·결과' if season_started else '개막 주간 일정')
    home_aria = 'NBA 프리시즌' if home_preseason else ('NBA 정규시즌' if season_started else 'NBA 개막 주간')
    tip = ''.join(nba_home_story(g) for g in home_games[:5])
    # 지난 경기 프리뷰는 홈 뉴스에서 내리고, 기사·분석 목록에는 보존한다.
    # 신규 뉴스가 발행되면 날짜순으로 우선 노출한다.
    home_pins = []
    pin_articles = [next((a for a in ARTICLES if a.slug == slug), None) for slug in home_pins]
    pin_articles = [a for a in pin_articles if a is not None]
    stale_home_slugs = {'hanshin-dena-cs-final-game2-recap', 'lg-doosan-wildcard-game1-recap'}
    home_other = [a for a in news if a.slug not in stale_home_slugs and a.slug not in home_pins]
    newer_news = [a for a in home_other if a.date > '2026-10-23']
    home_feed = newer_news + pin_articles + [a for a in home_other if a not in newer_news]
    # 홈 뉴스는 오늘(한국시간) 날짜 글만 — 지난 뉴스는 홈에서 내리고(글·전체 목록은 유지), 오늘 글이 없으면 최신순으로 되돌린다.
    today_kst = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    # 오늘 글만 남기면 오른쪽 목록이 비어 보이므로(2026-10-23 사용자 지적), 리드 1 + 목록 4 = 5건이 되도록 최신순으로 채운다.
    _today_feed = [a for a in home_feed if a.date >= today_kst]
    _fill = [a for a in home_feed if a not in _today_feed]
    home_feed = ((_today_feed + _fill)[:5]) or home_feed
    lead = home_feed[0]
    rest = home_feed[1:5]
    lead_summary = lead.excerpt
    lead_label = 'LEAD'

    nl = ''.join(f'<a class="nl" href="{a.url}">{home_news_thumb(a)}<span class="t"><span class="tag">{esc(a.league)} · {a.date_dot}</span><strong>{esc(a.headline)}</strong></span><span class="talk">{talk_icon()}토론</span></a>' for a in rest)
    lcs_cards = ''.join(lcs_card(d) for d in PS.get('lcs', []))
    lcs_html = f'''<section class="wrap sec" id="lcs" aria-labelledby="dsTitle">
  <div class="sec-head"><h2 class="sec-title" id="dsTitle">MLB <span class="outline">POSTSEASON</span> <span class="kr">챔피언십시리즈</span></h2><a class="more" href="/special/postseason-2026/">대진표 · 전체 일정 →</a></div>
  <div class="grid-4" style="grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))">{lcs_cards}</div>
</section>'''
    if HOME_HIDE_MLB:
        lcs_html = ''
    ta_html = today_analysis()
    # 홈 '오늘 SOCCER' 줄: 카드가 클릭되지 않아 일단 홈에서만 내림(삭제 아님). 다시 올리려면 True로.
    sc_html = soccer_today() if (SHOW_HOME_SOCCER and soccer_today_active()) else ''
    body = f'''
<section class="hero" aria-labelledby="heroTitle">
  <div class="hero-media">{media}</div>
  <div class="hero-shade" aria-hidden="true"></div>
  <article class="hero-copy">
    <span class="hero-badge">{esc(hero_badge_en)}<b>{esc(hero_badge_kr)}</b></span>
    <h1 id="heroTitle">{hero_title}</h1>
    <p>{esc(hero_text)}</p>
    <div style="display:flex;gap:10px;flex-wrap:wrap"><a class="pill white" href="{esc(hero_link or '/nba/')}" style="height:54px;padding:0 28px">{hero_cta if hero_link else home_cta}</a><a class="pill ghost" href="/community/#write" style="height:54px;padding:0 28px">팬 보드에서 얘기하기</a></div>
  </article>
  {credit}{reel_tag}
  <aside class="top-stories" aria-label="{home_aria}"><h2>{home_heading} <span class="nba-dday">{home_status}</span></h2><div class="tip-rail">{tip}</div><a class="more top-stories-more" href="/nba/">NBA 허브 →</a></aside>
</section>

{win_band}

{sc_html}

{ta_html}

{game_preview()}

{lcs_html}

<section class="wrap sec" aria-labelledby="newsTitle">
  <div class="sec-head"><h2 class="sec-title" id="newsTitle">NEWS<span class="accent">.</span> <span class="kr">오늘의 이야기, 함께 읽고 토론</span></h2><a class="more" href="/news/">뉴스 전체 →</a></div>
  <div class="news-grid">
    <a class="news-lead lift" href="{lead.url}">{home_news_thumb(lead, lead=True)}<div class="body"><span class="tag red">{esc(lead_label)} · {esc(lead.league)} · {lead.date_dot}</span><h3>{esc(lead.headline)}</h3><p>{esc(lead_summary)}</p><span class="talk">{talk_icon()}읽고 함께 이야기하기 →</span></div></a>
    <div class="news-list">{nl}</div>
  </div>
</section>

<section class="wrap sec" aria-labelledby="magTitle">
  <div class="sec-head"><h2 class="sec-title" id="magTitle">MAGAZINE<span class="accent">.</span></h2><a class="more" href="/magazine/">매거진 전체 →</a></div>
  {blog_grid(3, home=True)}
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
    <div class="fan-main" data-board data-size="5" data-board-tabs>
      <div class="sec-head" style="margin:0"><div class="board-tabs" role="tablist" aria-label="팬 보드 글 정렬"><button type="button" role="tab" data-board-tab="live" aria-selected="true">실시간</button><button type="button" role="tab" data-board-tab="today" aria-selected="false">투데이</button><button type="button" role="tab" data-board-tab="comments" aria-selected="false">댓글순</button></div><a class="more accent" href="/community/">전체 글 보기 →</a></div>
      <div data-board-list><div class="empty">스포츠 팬들의 경기·선수 토론을 확인할 수 있습니다. <a href="/community/">팬 보드에서 최신 글 보기 →</a></div></div>
      <a class="fan-write" href="/community/#write"><span class="fan-write-ph">오늘 경기, 무슨 얘기 하고 싶어요?</span><span class="pill">글쓰기</span></a>
    </div>
    <aside class="fan-side">
      {game_threads(hide_mlb=HOME_HIDE_MLB)}
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

{preserved_component('home-brand-story')}

{message_box()}
'''
    write('/', layout('SFANDOM | Play First. Analysis Next. — 스포츠 팬 커뮤니티', body, path='/', ld=[org_ld()], active='/'))


# ───────────────────────── 글 상세 ─────────────────────────
def related(a: Article, n: int = 5) -> list[Article]:
    same = [x for x in ARTICLES if x is not a and a.edition and x.edition == a.edition]
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
        fig = f'<figure class="figure {logo}{feature}{photo_cls(a)}"><img src="{esc(a.image)}" alt="{esc(a.image_alt)}" fetchpriority="high"{fallback_attr}>{fallback}{an_logos(a) if a.image.startswith('/assets/photos/') else ''}{cap}</figure>'
    srcs = ''.join(f'<span>{esc(s["label"])}</span>' for s in a.sources if s.get('label'))
    src_html = f'<div class="sources"><strong>출처</strong>{srcs}</div>' if srcs else ''
    credit = f'<p class="credit">{esc(a.credit)}</p>' if a.credit and not a.credit.startswith('PHOTO') else ''
    rel = ''.join(f'<a href="{x.url}"><small>{esc(x.section)} · {x.date_dot}</small>{esc(x.headline)}</a>' for x in related(a))
    ed = f'<a class="more" href="/news/morning/{a.edition}/">{a.edition.replace("-", ".")} 모닝 에디션 전체 →</a>' if a.edition in EDITIONS else ''
    topic = quote(f'[토론] {a.title.rstrip(",.")}')
    anchor_title = f'[분석 토론] {a.title.rstrip(",.")[:100]}'
    discussion_html = f'''<section class="news-comment-box" data-news-comments data-article-path="{esc(a.url)}" data-article-kind="{'news' if a.kind == 'news' else 'article'}" data-article-title="{esc(anchor_title)}" aria-label="토론">
          <h2>이 글 이야기하기</h2>
          <p class="nc-intro">이 글에 남긴 댓글과 답글은 이 아래에 바로 보이고, FAN BOARD의 전체 이야기에도 함께 표시됩니다.</p>
          <div data-discussion-mount><p class="news-comment-empty">댓글을 불러오는 중…</p></div>
          <noscript><a class="pill" href="/community/?topic={topic}#write">{talk_icon()}팬 보드에 글쓰기</a></noscript>
          <div class="nc-actions"><a class="more" href="/community/" data-news-comment-link hidden>전체 이야기에서 보기 →</a></div>
          <p class="nc-status" data-news-comment-status role="status"></p>
        </section>'''
    body = f'''
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
    </article>
    <aside class="article-aside" style="display:flex;flex-direction:column;gap:24px">
      <div class="aside-box"><h2>함께 읽기</h2>{rel}</div>
      <div class="aside-box"><h2>인스타그램</h2><a href="https://www.instagram.com/sportsfandom/" target="_blank" rel="noopener">경기 전후 핵심 한 줄과 릴스는 @sportsfandom에서 →</a></div>
    </aside>
  </div>
</div>'''
    ld = {'@context': 'https://schema.org', '@type': 'NewsArticle' if a.kind != 'magazine' else 'Article',
          'headline': a.headline[:110], 'description': a.excerpt, 'datePublished': f'{a.date}T08:00:00+09:00',
          'dateModified': f'{a.date}T08:00:00+09:00', 'inLanguage': 'ko-KR', 'mainEntityOfPage': BASE + a.url,
          'author': {'@type': 'Organization', 'name': 'SFANDOM', 'url': BASE + '/about/'},
          'publisher': {'@id': f'{BASE}/#organization', '@type': 'Organization', 'name': 'SFANDOM',
                        'logo': {'@type': 'ImageObject', 'url': f'{BASE}/assets/brand/sfandom-mark-512.png'}}}
    share = '' if is_match_card(a.__dict__) or a.image.lower().endswith('.svg') else a.image  # 대진 분석은 스코어보드 카드, 로고(SVG) 글은 글별 공유 카드가 공유 이미지 (SNS는 SVG 미리보기를 못 씀)
    if not share:  # 사진이 없는 글은 build_article_cards.py 가 만든 글별 공유 카드 사용 (없으면 대표 카드)
        card = f'/assets/share/cards/{card_name(pathlib.Path(a.file).stem, a.__dict__)}'
        share = card if (ROOT / card.lstrip('/')).exists() else ''
    if share:
        ld['image'] = [share if share.startswith('http') else f'{BASE}{share}']
    write(a.url, layout(a.headline, body, path=a.url, description=a.excerpt, image=share, og_type='article',
                        ld=[ld, breadcrumb_ld(trail)], active=section_url), lastmod=a.date,
          search={'u': a.url, 't': a.headline, 's': a.subtitle, 'k': a.section, 'd': a.date_dot, 'x': a.excerpt})


# ───────────────────────── 목록 ─────────────────────────
def item_list(items: list[Article]) -> str:
    return '<div class="list">' + ''.join(list_item(a) for a in items) + '</div>'


def page_head(title_html: str, lede: str, trail: list[tuple[str, str]], tabs: str = '') -> str:
    return f'<div class="wrap page-head">{crumbs(trail)}<h1>{title_html}</h1>{f"<p class=lede>{esc(lede)}</p>" if lede else ""}{tabs}</div>'


def tabs(items: list[tuple[str, str]], current: str) -> str:
    return '<nav class="tabs" aria-label="분류">' + ''.join(
        f'<a href="{u}"{CUR if u == current else ""}>{esc(l)}</a>' for l, u in items) + '</nav>'


def two_col(main: str, side_extra: str = '') -> str:
    return (f'<div class="wrap sec split-8-4" style="padding-top:32px"><div class="main">{main}</div>'
            f'<aside class="side"><div class="sticky-rail">{side_extra}</div></aside></div>')


def latest_box(exclude_kind: str | None = None) -> str:
    items = [a for a in ARTICLES if a.kind != exclude_kind][:6]
    return '<div class="aside-box" style="margin-top:24px"><h2>최신 글</h2>' + ''.join(
        f'<a href="{a.url}"><small>{a.section} · {a.date_dot}</small>{esc(a.headline)}</a>' for a in items) + '</div>'


def build_lists():
    news = [a for a in ARTICLES if a.kind == 'news']
    news_tabs = tabs([('전체 뉴스', '/news/'), ('모닝 에디션', '/news/morning/')], '/news/')
    write('/news/', layout('NEWS · 스포츠 뉴스', page_head('NEWS<span class="accent">.</span> <span class="kr">오늘의 이야기, 함께 읽고 토론</span>',
          '공식 기록으로 확인한 경기 소식. 모든 뉴스는 팬 보드 토론으로 이어집니다.', [('NEWS', '')], news_tabs)
          + two_col(item_list(news), latest_box('news')),
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
                           + item_list(items), latest_box()))
        write(f'/news/morning/{d}/', layout(f'모닝 에디션 {d.replace("-", ".")} · {e.get("title", "")}', ebody, path=f'/news/morning/{d}/',
              description=e.get('intro', ''), active='/news/', ld=[breadcrumb_ld([('NEWS', '/news/'), ('MORNING EDITION', '/news/morning/'), (d, '')])]), lastmod=d)
    write('/news/morning/', layout('MORNING EDITION · 모닝 에디션', page_head('MORNING <span class="accent">EDITION</span>',
          '어제 경기에서 오늘까지 남는 것만 골라 매일 아침 정리합니다.', [('NEWS', '/news/'), ('MORNING EDITION', '')],
          tabs([('전체 뉴스', '/news/'), ('모닝 에디션', '/news/morning/')], '/news/morning/'))
          + two_col('<div class="list">' + ''.join(rows) + '</div>'), path='/news/morning/',
          description='SFANDOM 모닝 에디션 전체 목록', active='/news/'))

    # 매거진: sfandomsport 네이버 블로그 최근 글 링크 전용 화면.
    # 사진/영상 썸네일 외부 URL을 렌더링하거나 Google Blogger를 동적으로 스크랩하지 않습니다.
    # 과거 SFANDOM 원문은 /analysis/ 및 개별 기사 경로에 그대로 보존합니다.
    naver_mag = render_naver_magazine(BLOGS.get('naver', []), esc, naver_player)
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
          + preserved_component('analysis-cycle-guide') + two_col('<h2 class="sec-title" style="font-size:44px">LATEST <span class="kr">최근 경기 프리뷰</span></h2>' + item_list(an)
                    + f'<section id="method" class="sec"><h2 class="sec-title" style="font-size:56px">METHOD <span class="kr">분석은 이렇게 만듭니다</span></h2><div class="prose">{method}</div></section>',
                    '<div class="aside-box" style="margin-top:24px"><h2>REVIEW</h2><a href="/analysis/review/">경기 전 전망과 실제 결과 기록 보기 →</a></div>'
                    + (f'<div class="aside-box" style="margin-top:24px"><h2>SPECIAL</h2>{special_links()}</div>' if special_links() else '')),
          path='/analysis/', description=lede, active='/analysis/'))
    write('/analysis/mlb/', layout('MLB 분석', page_head('MLB <span class="accent">ANALYSIS</span>', '선발 매치업과 순위 경쟁을 중심으로 본 MLB 경기 프리뷰.', [('ANALYSIS', '/analysis/'), ('MLB', '')],
          tabs([('전체', '/analysis/'), ('NBA', '/analysis/nba/'), ('MLB', '/analysis/mlb/'), ('복기 리포트', '/analysis/review/')], '/analysis/mlb/'))
          + two_col(item_list([a for a in an if a.league == 'MLB']), latest_box('analysis')),
          path='/analysis/mlb/', description='MLB 경기 프리뷰와 분석', active='/analysis/'))
    write('/analysis/nba/', layout('NBA 분석', page_head('NBA <span class="accent">ANALYSIS</span>', '새 시즌 주요 경기를 경기 전 구도 중심으로 정리한 NBA 프리뷰.', [('ANALYSIS', '/analysis/'), ('NBA', '')],
          tabs([('전체', '/analysis/'), ('NBA', '/analysis/nba/'), ('MLB', '/analysis/mlb/'), ('복기 리포트', '/analysis/review/')], '/analysis/nba/'))
          + two_col(item_list([a for a in an if a.league == 'NBA']), latest_box('analysis')),
          path='/analysis/nba/', description='NBA 경기 프리뷰와 분석', active='/analysis/'))
    # 자동 복기: 경기 전에 pick을 남긴 분석 중 끝난 경기를 결과와 대조해 덧붙인다(손으로 쓴 기록은 그대로 유지).
    auto_recs = []
    for a in sorted([x for x in ARTICLES if x.kind == 'analysis' and getattr(x, 'pick', '')], key=lambda x: (x.date, x.file)):
        r = game_result(a)
        if not r or not r['verdict']:
            continue
        side = a.away if a.pick == 'away' else a.home
        auto_recs.append({'no': f'#A{len(auto_recs) + 1:02d}', 'date': a.date, 'league': a.league, 'match': f'{a.away} vs {a.home}',
                          'venue': f'{getattr(a, "kst", "")} KST', 'outlook': f'{side} 우세 전망',
                          'result': f'{a.away} {r["away"]}–{r["home"]} {a.home}',
                          'detail': f'경기 전 글에 남긴 예측과 종료 결과를 자동으로 대조했습니다. 분석: {a.headline}',
                          'matched': r['verdict'] == 'hit'})
    all_recs = auto_recs[::-1] + RECORDS['records']
    updated = TODAY if auto_recs else RECORDS['updated']
    recs = ''.join(f'''<div class="record"><span class="no">{r["no"]}</span><div><span class="tag red">{r["league"]} · {r["date"].replace("-", ".")} · {esc(r["venue"])}</span><h3>{esc(r["match"])}</h3>
<p>경기 전 · {esc(r["outlook"])} → 결과 · {esc(r["result"])}. {esc(r["detail"])}</p></div><span class="verdict {"ok" if r["matched"] else "no"}">{"MATCHED" if r["matched"] else "NOT MATCHED"}</span></div>''' for r in all_recs)
    # 상단 집계는 홈 '분석 성공'과 같은 누적 기준(운영자 집계 + 자동 대조)으로 맞춘다. 아래 목록은 상세 공개분만 보여준다.
    _rb = SITE.get('analysis_record_base') or {}
    cum_total = int(_rb.get('total', 0)) + len(auto_recs)
    cum_ok = int(_rb.get('hit', 0)) + sum(r['matched'] for r in auto_recs)
    if not _rb:
        cum_total, cum_ok = len(all_recs), sum(r['matched'] for r in all_recs)
    write('/analysis/review/', layout('복기 리포트 · 경기 전 전망과 결과', page_head('REVIEW <span class="accent">/</span> <span class="kr">복기 리포트</span>', RECORDS['note'],
          [('ANALYSIS', '/analysis/'), ('REVIEW', '')], tabs([('전체', '/analysis/'), ('NBA', '/analysis/nba/'), ('MLB', '/analysis/mlb/'), ('복기 리포트', '/analysis/review/')], '/analysis/review/'))
          + preserved_component('review-cycle-guide') + editorial_index(EDITORIAL_PATHS, BY_KEY, esc, 'before-after') + two_col(f'<div class="stats" style="margin:0 0 12px"><div class="stat"><b>{cum_total}</b><span>RECORDS</span></div><div class="stat"><b>{cum_ok}</b><span>MATCHED</span></div><div class="stat"><b>{cum_total - cum_ok}</b><span>NOT MATCHED</span></div><div class="stat"><b>{updated[5:].replace("-", ".")}</b><span>UPDATED</span></div></div>'
                    + f'<div class="list">{recs}</div><p class="muted" style="font-size:14px;margin-top:20px">예상과 다른 결과도 지우지 않습니다. 어떤 전제가 틀렸는지 다음 분석에서 다시 확인합니다.</p>'),
          path='/analysis/review/', description=RECORDS['note'], active='/analysis/'))


# ───────────────────────── 허브 · 특집 ─────────────────────────
def build_hubs():
    mlb = [a for a in ARTICLES if a.league == 'MLB']
    sec = lambda kind, title, kr, anchor: (f'<section id="{anchor}" class="sec" style="padding-top:40px"><div class="sec-head"><h2 class="sec-title" style="font-size:52px">{title} <span class="kr">{kr}</span></h2></div>'
                                           + item_list([a for a in mlb if a.kind == kind][:8]) + '</section>')
    t = tabs([('뉴스', '#news'), ('분석', '#analysis'), ('매거진', '#magazine'), ('포스트시즌', '/special/postseason-2026/')], '')
    ws = world_series()
    ws_html = ('<section id="worldseries" class="sec" style="padding-top:40px"><div class="sec-head"><h2 class="sec-title" style="font-size:42px">WORLD SERIES <span class="kr">최신 전적 · 다음 경기</span></h2></div><div class="grid-4" style="grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr))">'
               + lcs_card(ws) + '</div></section>') if ws else ''
    lcs_title = ('LEAGUE CHAMPIONSHIP <span class="kr">최종 결과</span>' if ws else 'LEAGUE CHAMPIONSHIP <span class="kr">최신 전적 · 다음 경기</span>')
    live_mlb = (ws_html + f'<section id="lcs" class="sec" style="padding-top:40px"><div class="sec-head"><h2 class="sec-title" style="font-size:42px">{lcs_title}</h2></div><div class="grid-4" style="grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))">'
                + ''.join(lcs_card(d) for d in PS.get('lcs', [])) + '</div></section>')
    main = live_mlb + sec('news', 'NEWS', 'MLB 뉴스', 'news') + sec('analysis', 'ANALYSIS', '경기 프리뷰', 'analysis') + sec('magazine', 'MAGAZINE', '기획 · 스포트라이트', 'magazine')
    write('/mlb/', layout('MLB · 메이저리그', page_head('MLB<span class="accent">.</span> <span class="kr">메이저리그</span>', '포스트시즌, 모닝 에디션, 선발 매치업까지 — MLB 이야기는 여기서 시작합니다.', [('MLB', '')], t)
          + two_col(main, '<div class="aside-box" style="margin-top:24px"><h2>POSTSEASON</h2><a href="/special/postseason-2026/">2026 포스트시즌 대진표 · 일정 →</a><a href="/community/">경기 얘기는 팬 보드에서 →</a></div>'),
          path='/mlb/', description='MLB 뉴스·경기 분석·매거진', active='/mlb/'))
    # NBA 허브
    story = ''.join(f'<div class="nba-story"><b>{x["k"]}</b><h3>{esc(x["t"])}</h3><p>{esc(x["x"])}</p></div>' for x in NBA['storylines'])
    kd = ''.join(f'<div class="round"><span class="display">{esc(d)}</span><span>{esc(t)}</span></div>' for d, t in NBA['key_dates'])
    nba_arts = [a for a in ARTICLES if a.league == 'NBA']
    pre_all = NBA.get('preseason_games', [])
    pre_done = [g for g in pre_all if g.get('result')]
    preseason_finished = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))) >= dt.datetime.fromisoformat(NBA["opening_kst"])
    pre_next = [] if preseason_finished else [g for g in pre_all if not g.get('result')]
    preseason_rows = nba_cards(pre_next, preseason_anchors=True)
    past_html = (f'<details class="past-games"><summary>지난 경기 결과 {len(pre_done)}개 보기</summary><div class="nba-rail preseason-list">'
                 + nba_cards(pre_done, preseason_anchors=True) + '</div></details>') if pre_done else ''
    preseason_title = "ARCHIVE" if preseason_finished else "GAME CENTER"
    preseason_note = ("프리시즌 종료 · 확인된 결과를 기록으로 보관합니다 · 한국시간" if preseason_finished
                      else "확인된 종료 경기와 예정·확인 중 경기 구분 · 한국시간")
    preseason_block = (f'<section class="sec" id="preseason"><div class="sec-head"><h2 class="sec-title">PRESEASON <span class="outline">{preseason_title}</span></h2><span class="muted">{preseason_note}</span></div><div class="nba-stage solo"><div class="nba-rail preseason-list">{preseason_rows}</div>{past_html}</div></section>') if (preseason_rows or past_html) else ''
    nsec = lambda kind, title, kr, anchor: (f'<section id="{anchor}" class="sec"><div class="sec-head"><h2 class="sec-title">{title} <span class="kr">{kr}</span></h2></div>'
                                            + '<div class="card-grid">' + ''.join(mag_card(a) for a in nba_arts if a.kind == kind) + '</div></section>') if any(a.kind == kind for a in nba_arts) else ''
    _arts = [(k, t, nsec(k, t, kr, k)) for k, t, kr in (('news', 'NEWS', 'NBA 뉴스'), ('analysis', 'ANALYSIS', '개막전 프리뷰'), ('magazine', 'MAGAZINE', '기획 · 시즌 가이드'))]
    _arts = [x for x in _arts if x[2]]
    art_tabs = ('<div class="art-tabs" data-art-tabs><div class="art-tab-bar" role="tablist">'
                + ''.join(f'<button type="button" role="tab" data-panel="{k}" aria-selected="{"true" if i == 0 else "false"}">{ {"news": "뉴스", "analysis": "분석", "magazine": "매거진"}[k] }</button>' for i, (k, t, h) in enumerate(_arts))
                + '</div>' + ''.join(h for k, t, h in _arts) + '</div>') if _arts else ''
    nba_tabs = tabs([('프리시즌 기록' if preseason_finished else '프리시즌', '#preseason'), ('개막 주간', '#tipoff'), ('뉴스', '#news'), ('분석', '#analysis'), ('매거진', '#magazine'), ('주요 날짜', '#dates')], '')
    opening_started = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))) >= dt.datetime.fromisoformat(NBA["opening_kst"])
    nba_description = ('2026-27 정규시즌 진행 중. 최신 경기 일정·결과, 개막 주간 기록, 시즌 분석을 한국시간으로 확인합니다.'
                       if opening_started else '새 시즌 개막까지 ' + nba_dday() + '. 개막 주간 일정과 프리뷰를 한국시간으로 확인합니다.')
    nba_body = (page_head('NBA <span class="accent">2026-27</span>', nba_description, [('NBA', '')], nba_tabs)
                + f'''<div class="wrap">
{preseason_block}
<section class="sec" id="tipoff" style="padding-top:40px"><div class="sec-head"><h2 class="sec-title">TIP-OFF <span class="outline">WEEK</span></h2><span class="muted">개막 주간 · 시간은 한국시간</span></div><div class="nba-stage solo"><div class="nba-rail">{nba_cards(NBA["games"])}</div></div></section>
<section class="sec" id="stories"><div class="sec-head"><h2 class="sec-title">STORYLINES <span class="kr">개막 주간 볼거리</span></h2></div><div class="grid-4">{story}</div></section>
{art_tabs}
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



def world_series():
    """월드시리즈: 두 챔피언십시리즈 우승팀의 시리즈 카드. 이미 끝난 경기는 postseason-2026.json의 ws.games(확인된 결과),
    앞으로의 경기는 ESPN 스냅샷에서 가져온다. 시리즈 전적은 결과 문구에서 센다."""
    champs = []
    for d in PS.get('lcs', []):
        if d['hw'] == 4 or d['aw'] == 4:
            w_home = d['hw'] == 4
            champs.append((d['league'], d['home'] if w_home else d['away'], d['home_kr'] if w_home else d['away_kr'],
                           d['home_color'] if w_home else d['away_color']))
    if len(champs) != 2:
        return None
    names = {c[1] for c in champs}
    wsd = PS.get('ws') or {}
    rows = [dict(r) for r in wsd.get('games', [])]
    wd = '월화수목금토일'
    fmt = lambda t: f"{t.month:02d}.{t.day:02d} ({wd[t.weekday()]}) {t:%H:%M}"
    seen = {r['kst'] for r in rows}
    snap = sorted([g for g in game_snapshot().get('leagues', {}).get('MLB', {}).get('games', [])
                   if {g.get('away'), g.get('home')} == names], key=lambda g: g['start_kst'])
    for g in snap:
        k = fmt(dt.datetime.fromisoformat(g['start_kst']))
        if k in seen:
            continue
        row = {'g': len(rows) + 1, 'kst': k}
        if g.get('status') == 'final' and isinstance(g.get('away_score'), int) and isinstance(g.get('home_score'), int):
            row['result'] = f"{g['away']} {g['away_score']}–{g['home_score']} {g['home']}"
        rows.append(row)
    if not rows:
        return None
    wins = {n: 0 for n in names}
    for r in rows:
        m = re.match(r'(\w+) (\d+)[–-](\d+) (\w+)', r.get('result', ''))
        if m:
            wins[m.group(1) if int(m.group(2)) > int(m.group(3)) else m.group(4)] += 1
    home = wsd.get('home') or (snap[0]['home'] if snap else champs[0][1])
    hc = next(c for c in champs if c[1] == home)
    ac = next(c for c in champs if c[1] != home)
    return {'league': 'WS', 'tag': 'WORLD SERIES · 7전 4선승', 'home': hc[1], 'away': ac[1], 'home_kr': hc[2], 'away_kr': ac[2],
            'home_color': hc[3], 'away_color': ac[3], 'hs': 0, 'as': 0, 'hw': wins[hc[1]], 'aw': wins[ac[1]],
            'home_sub': f"{hc[0]} 챔피언 · 홈 어드밴티지", 'away_sub': f"{ac[0]} 챔피언", 'games': rows}


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
    return (f'<{tag} class="matchup ds {lead}{" lift" if link else ""}"{href}><span class="tag">{esc(d.get("tag") or (d["league"] + "CS · 7전 4선승"))}</span>'
            f'<div class="row">{badge(d["home"], d["home_color"], "lg")}<span class="ds-name">{esc(d["home_kr"])}<small>{esc(d.get("home_sub") or ("#" + str(d["hs"]) + " · 홈 어드밴티지"))}</small></span><span class="ds-w h">{d["hw"]}</span></div>'
            f'<div class="row">{badge(d["away"], d["away_color"], "lg")}<span class="ds-name">{esc(d["away_kr"])}<small>{esc(d.get("away_sub") or ("#" + str(d["as"])))}</small></span><span class="ds-w a">{d["aw"]}</span></div>'
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
    destination = ('/games/' if g.get("source_live_snapshot") else
                   (f'/nba/#preseason-{g["away"].lower()}-{g["home"].lower()}' if g in NBA.get('preseason_games', []) else '/nba/#tipoff'))
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
        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
        if now < dt.datetime.fromisoformat(NBA["opening_kst"]):
            return NBA["games"]
        snapshot = game_snapshot().get("leagues", {}).get("NBA", {})
        valid = [x for x in snapshot.get("games", []) if game_clock(x.get("start_kst", ""))]
        upcoming = sorted((x for x in valid if x.get("status") in ("scheduled", "live")
                           and game_clock(x["start_kst"]) >= now - dt.timedelta(minutes=20)),
                          key=lambda x: x["start_kst"])
        recent = sorted((x for x in valid if x.get("status") == "final"),
                        key=lambda x: x["start_kst"], reverse=True)
        selected = (upcoming[:5] + recent[:max(0, 5 - len(upcoming[:5]))]) if upcoming else recent[:5]
        selected.sort(key=lambda x: x["start_kst"])
        abbr = {"NY": "NYK", "GS": "GSW", "NO": "NOP", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}
        cards = []
        for x in selected:
            when = game_clock(x["start_kst"])
            finished = x["status"] == "final"
            score = (f'{x["away_score"]}–{x["home_score"]}' if finished else "")
            cards.append({"away": abbr.get(x["away"], x["away"]), "home": abbr.get(x["home"], x["home"]),
                          "day": "FINAL" if finished else ("LIVE" if x["status"] == "live" else "REGULAR SEASON"),
                          "kst": when.strftime("%m.%d") + f' ({"월화수목금토일"[when.weekday()]}) ' + when.strftime("%H:%M"),
                          "result": score, "tag": score if finished else "", "tv": "",
                          "source_live_snapshot": True})
        return cards or NBA["games"]
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
         [k('분석 전체', '/analysis/'), k('NBA 분석', '/analysis/nba/'), k('MLB 분석', '/analysis/mlb/'), k('분석 원칙', '/analysis/#method'), k('복기 리포트', '/analysis/review/', True)]
         + [k(f['kr'], f'/special/{f["id"]}/') for f in SPECIALS.get('features', []) if special_picks(f)[1]]),
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


def fan_creed() -> str:
    return ('<section class="fan-creed" aria-labelledby="fanCreedTitle">'
            '<span class="fan-creed__eyebrow">FAN BOARD · OUR CREED</span>'
            '<h2 class="fan-creed__title" id="fanCreedTitle">Connecting Fans.<br>Returning Value.</h2>'
            '<p class="fan-creed__lede">This board was built to connect sports fans '
            '&mdash; and to return the value we create to people and society.</p>'
            '<p class="fan-creed__line">When community grows, responsibility grows.</p>'
            '<p class="fan-creed__share">Share a play. Share a thought. '
            '<strong>Share it back.</strong></p>'
            '</section>')


def build_community():
    body = (page_head('FAN BOARD<span class="accent">.</span> <span class="kr">먼저 놀고</span>', '가입 없이 닉네임만으로 쓰는 팬 게시판. 경기 얘기, 직관 후기, 반론 모두 환영합니다.', [('FAN BOARD', '')])
            + f'''<div class="wrap" style="padding-top:28px">{fan_creed()}</div>
<div class="wrap" style="padding-top:28px">{channel_chips()}</div>
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
    write('/community/', layout('FAN BOARD · 팬 게시판', body, path='/community/', description='SFANDOM 팬 보드 — 가입 없이 쓰는 스포츠 팬 게시판', active='/community/', noindex=True), index=False)


def build_links():
    """인스타그램 프로필 링크용 한 화면 모음: 오늘 일정 · 최신 분석 · 팬 보드. 검색 색인에는 넣지 않는다."""
    def prio(a):
        try:
            return int(getattr(a, 'priority', 0) or 0)
        except (TypeError, ValueError):
            return 0
    latest = sorted([a for a in ARTICLES if a.kind == 'analysis'], key=lambda a: (a.date, prio(a)), reverse=True)[:6]
    ig = 'https://www.instagram.com/sportsfandom/'
    btn = lambda href, label, cls='pill': f'<a class="{cls}" href="{href}" style="height:54px;padding:0 28px;justify-content:center">{label}</a>'
    body = page_head('LINKS<span class="accent">.</span> <span class="kr">오늘 볼 것</span>',
                     'NBA·MLB·KBO 일정과 결과, 최신 경기 분석, 팬 보드를 한 곳에 모았습니다.', [('LINKS', '')]) + \
        '<div class="wrap sec" style="padding-top:28px;max-width:720px;margin-left:0">' \
        '<div style="display:grid;gap:12px">' + btn('/games/', '오늘 경기 일정·결과') + btn('/analysis/', '최신 경기 분석 전체', 'pill ghost') + \
        btn('/community/#write', '팬 보드에서 얘기하기', 'pill ghost') + btn(ig, '인스타 @sportsfandom', 'pill ghost') + '</div>' \
        '<h2 class="sec-title" style="font-size:32px;margin:40px 0 12px">LATEST <span class="kr">최신 분석</span></h2>' + item_list(latest) + '</div>'
    write('/links/', layout('LINKS 오늘 볼 것', body, path='/links/', description='SFANDOM 오늘 경기 일정, 최신 분석, 팬 보드 바로가기', noindex=True), index=False)


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
        if key == 'about':
            body = page_head(f'{en}<span class="accent">.</span> <span class="kr">{kr}</span>', lede, [(kr, '')]) + \
                f'<div class="wrap sf-about-wrap"><div class="sf-about">{frag}</div></div>'
        else:
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
          path='/contact/', description='SFANDOM 문의 양식 · 오류 제보 · 권리침해 신고', noindex=True), index=False)

    cookies = '''<div class="wrap sec" style="padding-top:36px;max-width:960px;margin-left:0"><div class="prose">
<h2>광고 게재</h2>
<p>SFANDOM은 현재 Google AdSense 심사 중이며 광고를 게재하지 않습니다. 광고 배치 및 송출 기능은 비활성화되어 있습니다. 승인 이후 광고를 운영할 경우 별도로 안내합니다.</p>
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
                                          description=f'{label} 팬 보드 인기 글', noindex=True), index=False, lastmod=sn['end'])
    latest = snaps[0]
    archive = ''.join(f'<li><a href="/weekly/{sn["id"]}/">{esc(sn["start"])} ~ {esc(sn["end"])} · 글 {sn["posts"]}편</a></li>' for sn in snaps)
    body = page_head('WEEKLY<span class="accent">.</span> <span class="kr">주간 팬 보드 베스트</span>',
                     '매주 월요일, 지난 한 주 팬 보드 인기 글을 모읍니다.', [('주간 베스트', '')]) + issue_body(latest) + \
        f'<div class="wrap prose" style="max-width:960px;margin-left:0"><h2>지난 호</h2><ul>{archive}</ul></div>'
    write('/weekly/', layout('주간 팬 보드 베스트', body, path='/weekly/', description='지난 한 주 SFANDOM 팬 보드 인기 글', noindex=True), index=False)


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
        data = data if isinstance(data.get('leagues'), dict) else {'leagues': {}}
    except (OSError, ValueError, TypeError):
        data = {'leagues': {}}
    try:  # NPB는 별도 수집기(sync_npb.py)가 채우는 파일에서 합친다
        extra = json.loads((CONTENT / 'npb-snapshot.json').read_text(encoding='utf-8')).get('leagues', {})
        if isinstance(extra, dict):
            data['leagues'].update({k: v for k, v in extra.items() if isinstance(v, dict)})
    except (OSError, ValueError, TypeError):
        pass
    return data


SCORE_LABELS = {
    'scheduled': '예정', 'live': '진행 중 · 확인 시각 기준',
    'final': '종료', 'postponed': '연기', 'cancelled': '취소',
}
SCORE_LEAGUES = (('MLB', '⚾'), ('NBA', '🏀'), ('NFL', '🏈'), ('NHL', '🏒'), ('NPB', '⚾'))


def game_clock(kst: str) -> dt.datetime | None:
    try:
        value = dt.datetime.fromisoformat(kst)
        return value if value.tzinfo else None
    except (TypeError, ValueError):
        return None


def score_team(g: dict, side: str, state: str) -> str:
    """경기 행의 팀 표시. 예정 경기는 저장소에 로고가 있는 리그(NBA·MLB)에 한해 팀 로고로, 나머지는 약자 글자로 보여 준다."""
    abbr, name = str(g.get(side, '?')), g.get(f'{side}_name', '')
    league = str(g.get('league', '')).lower()
    if state == 'scheduled' and league in ('nba', 'mlb') and league in LOGO_SOURCES and (ROOT / 'assets' / 'teams' / league / f'{abbr.lower()}.svg').exists():
        return f'<span class="sf-scores__logo" title="{esc(name)}">{badge(abbr, team_color(abbr, league), "", league=league)}</span>'
    return f'<b title="{esc(name)}">{esc(abbr)}</b>'


def game_card(g: dict, stale: bool = False, checked_at: str = '') -> str:
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
    return (f'<{row_tag} class="sf-scores__game" data-score-state="{esc(state)}" data-score-start="{esc(g["start_kst"])}" data-score-checked="{esc(checked_at)}"{link}>'
            f'<span class="sf-scores__time"><time datetime="{esc(g["start_kst"])}">{when.strftime("%m.%d %H:%M")}</time>'
            f'<small>{esc(label)}</small></span>'
            f'<span class="sf-scores__teams">{score_team(g, "away", state)}'
            f'<i aria-hidden="true">VS</i>{score_team(g, "home", state)}</span>'
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
        if brief and HOME_HIDE_MLB and league == 'MLB':
            continue
        details = snapshot.get('leagues', {}).get(league) or {}
        verified, stale = game_age(details.get('checked_at', ''))
        games = [g for g in details.get('games', []) if game_clock(g.get('start_kst', ''))]
        games.sort(key=lambda g: (g.get('start_kst', ''), g.get('id', '')))
        if brief:
            now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
            limit = 4 if league == 'MLB' else 2
            # 홈 미리보기: 앞으로 열릴(또는 진행 중인) 경기를 먼저, 모자라면 가장 최근 종료 경기로 채운다
            cutoff = now - dt.timedelta(minutes=20)
            ahead = [g for g in games if g.get('status') in ('scheduled', 'live') and game_clock(g['start_kst']) >= cutoff]
            behind = [g for g in games if g not in ahead]
            games = ahead[:limit] + behind[-(limit - len(ahead[:limit])):] if len(ahead) < limit else ahead[:limit]
            games.sort(key=lambda g: g['start_kst'])
        else:
            games = games[-50:]
        cards = ''.join(game_card(g, stale, details.get('checked_at', '')) for g in games)
        if details.get('no_games_today') and league == 'NPB' and details.get('checked_at', '')[:10] == TODAY:
            cards = '<p class="sf-scores__empty">오늘 NPB 공식 일정에 경기가 없습니다. 아래는 이전 경기 기록입니다.</p>' + cards
        if not cards:
            cards = '<p class="sf-scores__empty">이 시간대 확인된 경기 정보가 없습니다. 다음 자료 갱신을 기다려 주세요.</p>'
        note = ' · 일부 날짜 확인 지연' if details.get('coverage') == 'partial' else ''
        if details.get('error'):
            note += ' · 외부 자료 확인 지연'
        output.append(f'<section class="sf-scores__league" data-league="{league}" aria-label="{league} 경기 결과와 일정">'
                      f'<div class="sf-scores__league-head"><h3>{icon} {league}</h3>'
                      f'<small>확인 {esc(verified)}{esc(note)}</small></div>'
                      f'<div class="sf-scores__rows">{cards}</div></section>')
    return ''.join(output)


def game_preview() -> str:
    # 종목 탭: 자바스크립트가 켜지면 NBA부터 한 종목씩 보여주고, 꺼져 있으면 전 종목을 그대로 펼쳐 둡니다.
    order = ('NBA', 'NPB', 'NFL', 'NHL') if HOME_HIDE_MLB else ('NBA', 'MLB', 'NPB', 'NFL', 'NHL')
    tabs_html = ''.join(f'<button type="button" role="tab" data-score-tab="{lg}" aria-selected="{"true" if lg == order[0] else "false"}">{lg}</button>' for lg in order)
    return (f'<section class="wrap sf-scores sf-scores--preview" aria-labelledby="scorePreviewTitle" data-score-tabs>'
            f'<div class="sf-scores__heading"><div><span class="sf-scores__eyebrow">GAME CENTER · KST</span>'
            f'<h2 id="scorePreviewTitle">경기 일정 <span>·</span> 최종 결과</h2>'
            f'<p>{"NBA·NFL·NHL·NPB" if HOME_HIDE_MLB else "MLB·NBA·NFL·NHL·NPB"} · 외부 기록 제공처 확인 시각 기준</p></div>'
            f'<a class="pill" href="/games/">전체 경기 보기 →</a></div>'
            f'<div class="sf-scores__tabs" role="tablist" aria-label="종목" hidden>{tabs_html}</div>'
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
            f'NPB는 npb.jp 첫 화면 속보 기준이며 오늘 경기 위주로 갱신됩니다. KBO는 공식 사이트가 자동 수집을 허용하지 않아 이 페이지에서 제외합니다.</p></div>')
    write('/games/', layout('경기 일정·결과 | SFANDOM', body, path='/games/',
         description='MLB NBA NFL NHL 경기 일정과 결과, KST 시간 및 마지막 확인 시각.'),
         search={'u': '/games/', 't': '경기 일정·결과', 's': 'MLB NBA NFL NHL', 'k': 'GAME CENTER',
                 'd': TODAY.replace('-', '.'), 'x': '경기 스코어 및 일정 KST'})


def clean_generated():
    for d in GENERATED_DIRS:
        shutil.rmtree(ROOT / d, ignore_errors=True)


def special_picks(f: dict) -> tuple[str, list]:
    """특집(specials.json) 하나에 묶인 가장 최근 날짜의 경기 분석을 킥오프 순으로 돌려준다. 글 머리말의 special 값이 특집 id."""
    pool = [a for a in ARTICLES if getattr(a, 'special', '') == f['id'] and getattr(a, 'away', '') and getattr(a, 'home', '')]
    if not pool:
        return '', []
    day = max(a.date for a in pool)

    def when(a: Article):
        m = re.match(r'(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})', getattr(a, 'kst', '') or '')
        return tuple(int(x) for x in m.groups()) if m else (99, 99, 99, 99)
    return day, sorted([a for a in pool if a.date == day], key=when)[:f.get('count', 7)]


def special_links() -> str:
    out = ''
    for f in SPECIALS.get('features', []):
        if special_picks(f)[1]:
            out += f'<a href="/special/{f["id"]}/">{esc(f["kr"])} · {esc(f["short"])} →</a>'
    return out


def build_specials():
    """특집 페이지 /special/<id>/ — 같은 날 묶인 경기 분석을 한 화면 보드로. 특집이 늘면 specials.json에 항목만 추가한다."""
    for f in SPECIALS.get('features', []):
        day, picks = special_picks(f)
        if not picks:
            continue
        cards = ''.join(analysis_row(a, False) for a in picks)
        board = ('<div class="an-board"><div class="an-head" aria-hidden="true"><span>KST</span><span>MATCHUP</span>'
                 f'<span>핵심</span><span>변수</span><span>시선</span><span></span></div>{cards}</div>')
        url = f'/special/{f["id"]}/'
        body = (page_head(f'{esc(f["title_a"])} <span class="accent">{esc(f["title_b"])}</span> <span class="kr">{esc(f["kr"])}</span>', f['lede'],
                          [('SPECIAL', ''), (f['title_b'], '')])
                + f'<div class="wrap"><section class="sec" id="board" style="padding-top:40px"><div class="sec-head"><h2 class="sec-title">{day.replace("-", ".")} '
                  f'<span class="kr">{len(picks)}경기 · 한국시간</span></h2><a class="more" href="/analysis/">분석 전체 →</a></div>{board}</section>'
                  f'<section class="discuss"><div><h2>오늘 밤 경기 얘기는 팬 보드에서</h2><p>응원하는 팀, 기대되는 경기, 한 줄 평 모두 환영합니다.</p></div>'
                  f'<a class="pill" href="/community/?topic={quote("[축구] ")}#write">{talk_icon()}글쓰기</a></section></div>')
        ld = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': f'{f["title_a"]} {f["title_b"]} · {f["kr"]}', 'url': BASE + url, 'inLanguage': 'ko-KR'}
        write(url, layout(f'{f["title_a"]} {f["title_b"]} · {f["kr"]} ({day.replace("-", ".")})', body, path=url, description=f['lede'],
              ld=[ld, breadcrumb_ld([('SPECIAL', ''), (f['title_b'], url)])], active='/analysis/'),
              lastmod=day, search={'u': url, 't': f'{f["title_a"]} {f["title_b"]} · {f["kr"]}', 's': f['short'], 'k': 'SPECIAL', 'd': day.replace('-', '.'),
                                   'x': ' '.join(f'{a.away} {a.home}' for a in picks)})


def main():
    clean_generated()
    prepare_weekly()
    build_home()
    for a in ARTICLES:
        build_article(a)
    build_lists()
    build_hubs()
    build_specials()
    build_games()
    build_community()
    build_sitemap()
    build_static()
    build_links()
    build_feeds()
    build_weekly()
    build_meta_files()
    print(f'built {len(PAGES)} indexable pages, {len(ARTICLES)} articles')


if __name__ == '__main__':
    main()
