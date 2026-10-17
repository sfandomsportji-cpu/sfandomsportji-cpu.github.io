#!/usr/bin/env python3
"""특집(src/content/specials.json) 자동 초안 — 하루에 한 번, 오늘 밤 볼 만한 경기를 골라 프리뷰 초안을 만든다 (Claude 호출 없음, 비용 없음).

- 지금은 soccer-7(오늘의 축구 7). 특집이 늘면 FEATURES 에 항목을 더하고 specials.json 에 페이지 정보를 추가한다.
- 흐름: ESPN 경기 일정(확인된 자료) → '재미 점수'로 7경기 선정 → src/content/drafts/ 에 글 초안 7개 → 텔레그램 알림.
  게시는 하지 않는다. 사람이 초안을 확인하고 게시를 요청하면 articles/ 로 옮긴다(--publish).
- 초안 문장에는 킥오프(KST)·경기장·ESPN이 준 전적만 쓴다. 선발·부상·상대전적은 확정 자료를 확인한 뒤 덧붙인다고 적고 추측하지 않는다.
- 하루 한 번만 만든다: auto-alerts.json 의 special 항목에 '축구 하루(KST 18시~다음날 10시)' 단위로 기록한다.
- 일정을 못 받으면(네트워크·API 오류) 아무것도 만들지 않고 다음 실행에서 다시 시도한다.
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / 'src' / 'content'
KST = timezone(timedelta(hours=9))
API = 'https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={day}'
UA = 'SFANDOM-special-draft/1.0 (https://sfandom.com/)'

# 특집별 설정. window_start: 그날 KST 몇 시부터 / hours: 몇 시간 구간을 '오늘 밤'으로 볼지 / run_from: 몇 시 이후에 초안을 만들지
FEATURES = {
    'soccer-7': {
        'count': 7, 'window_start': 18, 'hours': 16, 'run_from': 12, 'run_until': 23, 'max_per_league': 3,
        'leagues': {  # ESPN 리그 코드: (표시 이름, 가중치)
            'uefa.champions': ('UEFA CHAMPIONS LEAGUE', 10), 'eng.1': ('PREMIER LEAGUE', 8), 'esp.1': ('LA LIGA', 8),
            'ger.1': ('BUNDESLIGA', 8), 'ita.1': ('SERIE A', 8), 'fra.1': ('LIGUE 1', 7), 'uefa.europa': ('UEFA EUROPA LEAGUE', 6),
            'uefa.europa.conf': ('UEFA CONFERENCE LEAGUE', 4), 'kor.1': ('K LEAGUE 1', 6),
        },
    },
}

# 이름만 알면 되는 대형 구단(재미 점수 가산). 영문 표기는 ESPN displayName 기준.
BIG = {'Real Madrid', 'Barcelona', 'Atlético Madrid', 'Atletico Madrid', 'Manchester City', 'Manchester United', 'Liverpool', 'Arsenal', 'Chelsea',
       'Tottenham Hotspur', 'Newcastle United', 'Aston Villa', 'Bayern Munich', 'Borussia Dortmund', 'Bayer Leverkusen', 'RB Leipzig',
       'Inter Milan', 'AC Milan', 'Juventus', 'Napoli', 'Roma', 'Paris Saint-Germain', 'Marseille', 'Lyon', 'Monaco',
       'Jeonbuk Hyundai Motors', 'Ulsan HD', 'FC Seoul'}
KO = {'Real Madrid': '레알 마드리드', 'Barcelona': '바르셀로나', 'Atlético Madrid': '아틀레티코 마드리드', 'Atletico Madrid': '아틀레티코 마드리드',
      'Manchester City': '맨체스터 시티', 'Manchester United': '맨체스터 유나이티드', 'Liverpool': '리버풀', 'Arsenal': '아스널', 'Chelsea': '첼시',
      'Tottenham Hotspur': '토트넘', 'Newcastle United': '뉴캐슬', 'Aston Villa': '애스턴 빌라', 'Everton': '에버턴', 'Brentford': '브렌트퍼드',
      'Bayern Munich': '바이에른 뮌헨', 'Borussia Dortmund': '도르트문트', 'Bayer Leverkusen': '레버쿠젠', 'RB Leipzig': '라이프치히',
      'Inter Milan': '인테르', 'AC Milan': 'AC 밀란', 'Juventus': '유벤투스', 'Napoli': '나폴리', 'Roma': '로마', 'Paris Saint-Germain': '파리 생제르맹',
      'Marseille': '마르세유', 'Lyon': '리옹', 'Monaco': '모나코', 'Real Betis': '레알 베티스', 'Espanyol': '에스파뇰', 'Strasbourg': '스트라스부르'}


def ko(name):
    return KO.get(name, name)


def wa(word):
    """받침 유무에 따라 와/과."""
    c = ord(word[-1]) - 0xAC00
    return word + ('과' if 0 <= c < 11172 and c % 28 else '와')


def fetch(code, day):
    req = urllib.request.Request(API.format(code=code, day=day), headers={'User-Agent': UA, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read(3_000_000)
        data = json.loads(body)
        return data if isinstance(data.get('events'), list) else None
    except Exception as e:  # 네트워크·형식 오류는 건너뛰고 다음 실행에서 다시
        print(f'special: {code} {day} 실패 ({type(e).__name__})')
        return None


def parse_record(summary):
    """ESPN 전적 문자열 'W-D-L' → (승점, 경기 수). 형식이 다르면 None."""
    m = re.fullmatch(r'\s*(\d+)-(\d+)-(\d+)\s*', summary or '')
    if not m:
        return None
    w, d, l = map(int, m.groups())
    return 3 * w + d, w + d + l, (w, d, l)


def parse_event(code, label, weight, ev):
    try:
        start = datetime.fromisoformat(str(ev['date']).replace('Z', '+00:00')).astimezone(KST)
        comp = ev['competitions'][0]
        side = {c['homeAway']: c for c in comp['competitors']}
        st = ev.get('status', {}).get('type', {})
        if st.get('state') != 'pre':
            return None
        out = {'id': f"{code}-{ev['id']}", 'code': code, 'label': label, 'weight': weight, 'start': start,
               'venue': (comp.get('venue') or {}).get('fullName', ''),
               'url': next((l['href'] for l in ev.get('links', []) if str(l.get('href', '')).startswith('https://www.espn.com/')), '')}
        for k in ('home', 'away'):
            t = side[k]['team']
            recs = side[k].get('records') or []
            rec = next((parse_record(r.get('summary')) for r in recs if parse_record(r.get('summary'))), None)
            out[k] = {'name': str(t.get('displayName', t.get('name', '?')))[:60], 'abbr': str(t.get('abbreviation', '')).upper()[:6], 'rec': rec}
        return out
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def fun_score(g):
    """재미 점수 — 적중 가능성이 아니라 '볼 만한가'. 리그 비중 + 대형 구단 + 승점 페이스가 높고 비슷한 매치업(접전 기대) + 밤 시간대."""
    s = g['weight']
    s += 3 * sum(g[k]['name'] in BIG for k in ('home', 'away'))
    ra, rh = g['away']['rec'], g['home']['rec']
    if ra and rh and ra[1] and rh[1]:
        pa, ph = ra[0] / ra[1], rh[0] / rh[1]
        s += 2 * (pa + ph) / 2            # 둘 다 잘하는 팀일수록 (경기당 승점 평균, 최대 3)
        s += 3 - 3 * min(abs(pa - ph), 3) / 3   # 승점 페이스가 비슷할수록 접전
    hour = g['start'].hour
    if hour >= 21 or hour <= 2:           # 한국 저녁~새벽 시청 시간대
        s += 1
    return round(s, 2)


def pick(games, count, max_per_league):
    ranked = sorted(games, key=lambda g: -fun_score(g))
    chosen, per = [], {}
    for g in ranked:
        if per.get(g['code'], 0) >= max_per_league:
            continue
        chosen.append(g)
        per[g['code']] = per.get(g['code'], 0) + 1
        if len(chosen) == count:
            break
    for g in ranked:  # 리그 상한 때문에 모자라면 점수 순으로 채운다
        if len(chosen) >= count:
            break
        if g not in chosen:
            chosen.append(g)
    return sorted(chosen, key=lambda g: g['start'])


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def rec_text(r):
    return f"{r[2][0]}승 {r[2][1]}무 {r[2][2]}패(승점 {r[0]})" if r else ''


def draft(feature_id, g, day):
    t, h, a = g['start'], g['home'], g['away']
    kst = t.strftime('%m.%d %H:%M')
    slug = f"{slugify(h['name'])}-{slugify(a['name'])}-{day.replace('-', '')}"
    lines = [f"{wa(ko(h['name']))} {ko(a['name'])}의 {g['label'].title()} 경기가 한국시간 {t.month}월 {t.day}일 {t.strftime('%H:%M')}에 열린다."]
    if g['venue']:
        lines[0] += f" 경기장은 {g['venue']}."
    if h['rec'] and a['rec']:
        lines.append(f"ESPN 집계 전적은 {ko(h['name'])} {rec_text(h['rec'])}, {ko(a['name'])} {rec_text(a['rec'])}다.")
    stats = [f"{t.strftime('%H:%M')} KST | {t.month}월 {t.day}일 · {g['venue'] or '경기장 확인 중'}"]
    if h['rec'] and a['rec']:
        stats.append(f"{h['rec'][0]}점 vs {a['rec'][0]}점 | 홈 · 원정 승점(ESPN 전적)")
    body = '\n\n'.join(lines) + '\n\n::: stats\n' + '\n'.join(stats) + '\n:::\n\n'
    body += ("::: angle KAIRO VIEW\n선발 명단·부상·최근 흐름은 공식 발표와 신뢰할 수 있는 자료를 확인한 뒤 덧붙인다. "
             "확정되지 않은 선수 이름은 적지 않는다.\n:::\n\n")
    if g['url']:
        body += f"일정 확인: [ESPN 경기 페이지]({g['url']})."
    fm = ['---', 'kind: "analysis"', f'date: "{day}"', f'edition: "{day}"', 'priority: 500',
          f'title: "{ko(h["name"])} vs {ko(a["name"])}"', f'subtitle: "{g["label"].title()} · 경기 전 프리뷰 초안"',
          f'kicker: "SFANDOM & KAIRO · {g["label"]}"', f'meta: "{t.strftime("%Y.%m.%d %H:%M")} KST · {a["name"].upper()} vs {h["name"].upper()} · 경기 전 프리뷰"',
          'league: "SOCCER"', 'image: ""', 'image_alt: ""', 'credit: ""', f'slug: "{slug}"', f'special: "{feature_id}"',
          f'away: "{(a["abbr"] or a["name"]).upper()}"', f'home: "{(h["abbr"] or h["name"]).upper()}"', f'kst: "{kst}"',
          'glance: [["핵심", "확인 중"], ["변수", "확인 중"], ["시선", "확인 중"]]',
          'sources: ' + json.dumps([{'label': 'ESPN 경기 페이지', 'url': g['url']}] if g['url'] else [], ensure_ascii=False), '---']
    return slug, '\n'.join(fm) + '\n' + body + '\n'


def soccer_day(now):
    """'오늘 밤' 기준 날짜(KST). 새벽 0~9시는 전날 축구 하루로 본다."""
    return (now - timedelta(hours=10)).date() if now.hour < 10 else now.date()


WEEKEND_DAYS = {4, 5, 6}  # 특집은 금(12시 발행)·토·일에만 — 평일에는 초안을 만들지 않는다


def already_published(feature_id, day):
    """그날 이 특집 글이 이미 articles/ 에 있으면 True — 직접 올린 날에는 자동 초안을 또 만들지 않는다."""
    for p in (C / 'articles').glob(f'{day}-*.md'):
        head = p.read_text(encoding='utf-8').split('---', 2)[1] if p.read_text(encoding='utf-8').startswith('---') else ''
        if re.search(rf'^special:\s*"{re.escape(feature_id)}"', head, re.M):
            return True
    return False


def run(feature_id, state, notify, now=None, fetcher=fetch):
    """초안을 만들었으면 만든 개수, 아직 할 때가 아니거나 자료가 없으면 0."""
    cfg = FEATURES[feature_id]
    now = now or datetime.now(KST)
    if not (cfg['run_from'] <= now.hour < cfg['run_until']):
        return 0
    day = soccer_day(now).isoformat()
    if soccer_day(now).weekday() not in WEEKEND_DAYS:
        return 0
    done = state.setdefault('special', {})
    if done.get(feature_id) == day:
        return 0
    if already_published(feature_id, day):  # 이미 올린 날: 기록만 하고 알리지 않는다
        done[feature_id] = day
        return 0
    start = datetime.fromisoformat(day + 'T00:00:00+09:00').replace(hour=cfg['window_start'])
    end = start + timedelta(hours=cfg['hours'])
    games, seen, failed = [], set(), 0
    for code, (label, weight) in cfg['leagues'].items():
        for d in [(start + timedelta(days=i)).strftime('%Y%m%d') for i in (-1, 0, 1)]:  # ESPN 날짜 기준이 달라도 놓치지 않게 앞뒤 하루씩
            data = fetcher(code, d)
            if data is None:
                failed += 1
                continue
            for ev in data['events']:
                g = parse_event(code, label, weight, ev)
                if g and g['id'] not in seen and start <= g['start'] < end:
                    seen.add(g['id']); games.append(g)
    if len(games) < 3:
        print(f'special: {feature_id} 경기 {len(games)}개(실패 {failed}) — 다음 실행에서 다시 시도')
        return 0
    chosen = pick(games, cfg['count'], cfg['max_per_league'])
    (C / 'drafts').mkdir(exist_ok=True)
    names = []
    for g in chosen:
        slug, text = draft(feature_id, g, day)
        (C / 'drafts' / f'special-{feature_id}-{day}-{slug}.md').write_text(text, encoding='utf-8')
        names.append(f"{g['start'].strftime('%H:%M')} {ko(g['home']['name'])} vs {ko(g['away']['name'])}")
    if notify(f"[특집 초안 · {feature_id}] {day} 오늘의 경기 {len(chosen)}개를 골랐습니다.\n\n" + '\n'.join(names)
              + "\n\n초안이 만들어졌습니다. 확인 후 게시를 요청하세요. (선발·부상은 확정 자료 확인 뒤 덧붙입니다)"):
        done[feature_id] = day
    return len(chosen)


def publish(feature_id):
    """초안(drafts/special-<id>-*.md)을 articles/ 로 옮긴다. 사람이 확인한 뒤에만 쓴다."""
    n = 0
    for p in sorted((C / 'drafts').glob(f'special-{feature_id}-*.md')):
        name = p.name.split(f'special-{feature_id}-', 1)[1]
        (C / 'articles' / name).write_text(p.read_text(encoding='utf-8'), encoding='utf-8')
        p.unlink()
        n += 1
    print(f'special: {n}개 게시 파일 이동')


if __name__ == '__main__':
    if '--publish' in sys.argv:
        publish(sys.argv[sys.argv.index('--publish') + 1])
