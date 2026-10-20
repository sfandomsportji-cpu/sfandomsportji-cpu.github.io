"""RSS 피드 생성 보조 모듈 (표준 라이브러리만 사용).

build.py 가 부른다. 전체 · 리그별 · 팀별 RSS 2.0 을 만들고, 글이 한 편이라도 있는 팀만 피드를 만든다.
글에는 팀 태그가 없으므로 제목·부제·meta·slug 에서 팀 이름을 찾는다 (같은 리그 글에서만, 단어 경계 기준).
"""
import datetime as dt
import html
import re

# (약자, 영어 별칭들, 한글 별칭들, 표시 이름)
MLB = [
    ('ARI', ['diamondbacks'], ['다이아몬드백스'], '애리조나 다이아몬드백스'), ('ATL', ['braves'], ['브레이브스'], '애틀랜타 브레이브스'),
    ('BAL', ['orioles'], ['오리올스'], '볼티모어 오리올스'), ('BOS', ['red sox'], ['레드삭스'], '보스턴 레드삭스'),
    ('CHC', ['cubs'], ['컵스'], '시카고 컵스'), ('CWS', ['white sox'], ['화이트삭스'], '시카고 화이트삭스'),
    ('CIN', ['reds'], ['신시내티', '레즈'], '신시내티 레즈'), ('CLE', ['guardians'], ['가디언스'], '클리블랜드 가디언스'),
    ('COL', ['rockies'], ['로키스'], '콜로라도 로키스'), ('DET', ['tigers'], ['타이거스'], '디트로이트 타이거스'),
    ('HOU', ['astros'], ['애스트로스'], '휴스턴 애스트로스'), ('KC', ['royals'], ['로열스'], '캔자스시티 로열스'),
    ('LAA', ['angels'], ['에인절스'], 'LA 에인절스'), ('LAD', ['dodgers'], ['다저스'], 'LA 다저스'),
    ('MIA', ['marlins'], ['말린스'], '마이애미 말린스'), ('MIL', ['brewers'], ['브루어스'], '밀워키 브루어스'),
    ('MIN', ['twins'], ['트윈스'], '미네소타 트윈스'), ('NYM', ['mets'], ['메츠'], '뉴욕 메츠'),
    ('NYY', ['yankees'], ['양키스'], '뉴욕 양키스'), ('ATH', ['athletics'], ['애슬레틱스'], '애슬레틱스'),
    ('PHI', ['phillies'], ['필리스'], '필라델피아 필리스'), ('PIT', ['pirates'], ['파이리츠'], '피츠버그 파이리츠'),
    ('SD', ['padres'], ['파드리스'], '샌디에이고 파드리스'), ('SF', ['giants'], ['자이언츠'], '샌프란시스코 자이언츠'),
    ('SEA', ['mariners'], ['매리너스'], '시애틀 매리너스'), ('STL', ['cardinals'], ['카디널스'], '세인트루이스 카디널스'),
    ('TB', ['rays'], ['레이스'], '탬파베이 레이스'), ('TEX', ['rangers'], ['레인저스'], '텍사스 레인저스'),
    ('TOR', ['blue jays'], ['블루제이스'], '토론토 블루제이스'), ('WSH', ['nationals'], ['내셔널스'], '워싱턴 내셔널스'),
]
NBA = [
    ('ATL', ['hawks'], ['호크스'], '애틀랜타 호크스'), ('BOS', ['celtics'], ['셀틱스'], '보스턴 셀틱스'),
    ('CLE', ['cavaliers', 'cavs'], ['캐벌리어스'], '클리블랜드 캐벌리어스'), ('NOP', ['pelicans'], ['펠리컨스'], '뉴올리언스 펠리컨스'),
    ('CHI', ['bulls'], ['불스'], '시카고 불스'), ('DAL', ['mavericks', 'mavs'], ['매버릭스'], '댈러스 매버릭스'),
    ('DEN', ['nuggets'], ['너기츠'], '덴버 너기츠'), ('GSW', ['warriors'], ['워리어스'], '골든스테이트 워리어스'),
    ('HOU', ['rockets'], ['로키츠', '로케츠'], '휴스턴 로키츠'), ('LAC', ['clippers'], ['클리퍼스'], 'LA 클리퍼스'),
    ('LAL', ['lakers'], ['레이커스'], 'LA 레이커스'), ('MIA', ['heat'], ['히트'], '마이애미 히트'),
    ('MIL', ['bucks'], ['벅스'], '밀워키 벅스'), ('MIN', ['timberwolves', 'wolves'], ['팀버울브스'], '미네소타 팀버울브스'),
    ('BKN', ['nets'], ['네츠'], '브루클린 네츠'), ('NYK', ['knicks'], ['닉스'], '뉴욕 닉스'),
    ('ORL', ['magic'], ['매직'], '올랜도 매직'), ('IND', ['pacers'], ['페이서스'], '인디애나 페이서스'),
    ('PHI', ['76ers', 'sixers'], ['식서스', '세븐티식서스'], '필라델피아 76ers'), ('PHX', ['suns'], ['선즈'], '피닉스 선즈'),
    ('POR', ['trail blazers', 'blazers'], ['블레이저스'], '포틀랜드 트레일블레이저스'), ('SAC', ['kings'], ['킹스'], '새크라멘토 킹스'),
    ('SAS', ['spurs'], ['스퍼스'], '샌안토니오 스퍼스'), ('OKC', ['thunder'], ['썬더', '선더'], '오클라호마시티 썬더'),
    ('TOR', ['raptors'], ['랩터스'], '토론토 랩터스'), ('UTA', ['jazz'], ['재즈'], '유타 재즈'),
    ('MEM', ['grizzlies'], ['그리즐리스'], '멤피스 그리즐리스'), ('WAS', ['wizards'], ['위저즈'], '워싱턴 위저즈'),
    ('DET', ['pistons'], ['피스톤스'], '디트로이트 피스톤스'), ('CHA', ['hornets'], ['호네츠'], '샬럿 호네츠'),
]
TEAMS = {'mlb': MLB, 'nba': NBA}
LEAGUE_NAME = {'all': '전체', 'mlb': 'MLB', 'nba': 'NBA', 'nfl': 'NFL', 'soccer': '축구'}


def _hay(a) -> str:
    return ' '.join([str(a.title), str(a.subtitle), str(getattr(a, 'meta', '')), str(a.slug).replace('-', ' ')]).lower()


def team_matches(a, league: str) -> list[str]:
    """글 하나가 언급하는 팀 약자들 (같은 리그 글만)."""
    if str(a.league).lower() != league:
        return []
    hay, out = _hay(a), []
    for abbr, en, kr, _ in TEAMS[league]:
        if any(re.search(rf'(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])', hay) for w in en) or any(w in hay for w in kr):
            out.append(abbr)
    return out


def _rfc822(date: str) -> str:
    d = dt.datetime.strptime(date, '%Y-%m-%d').replace(hour=9, tzinfo=dt.timezone(dt.timedelta(hours=9)))
    return d.strftime('%a, %d %b %Y %H:%M:%S +0900')


def render(base: str, path: str, title: str, desc: str, arts: list, limit: int = 30) -> str:
    e = lambda s: html.escape(str(s or ''), quote=True)
    items = ''
    for a in sorted(arts, key=lambda x: (x.date, x.file), reverse=True)[:limit]:
        link = f'{base}{a.url}'
        items += (f'<item><title>{e(a.headline)}</title><link>{e(link)}</link><guid isPermaLink="true">{e(link)}</guid>'
                  f'<pubDate>{_rfc822(a.date)}</pubDate><category>{e(a.section)}</category><category>{e(a.league)}</category>'
                  f'<description>{e(a.excerpt)}</description></item>\n')
    last = _rfc822(max((a.date for a in arts), default='2026-01-01'))
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
            f'<title>{e(title)}</title><link>{base}/</link><description>{e(desc)}</description><language>ko-KR</language>'
            f'<lastBuildDate>{last}</lastBuildDate><atom:link href="{e(base + path)}" rel="self" type="application/rss+xml"/>\n{items}</channel></rss>\n')
