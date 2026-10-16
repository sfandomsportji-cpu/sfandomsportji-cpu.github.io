#!/usr/bin/env python3
"""끝난 경기의 '결과 기사' 초안을 확인된 자료만으로 만든다 (Claude 호출 없음, 비용 없음).

- 자료: src/content/games-snapshot.json (ESPN) + postseason-2026.json (시리즈 전적) + nba-2026.json (개막일).
- 대상: MLB·NBA 중 status == final 이고, 같은 날짜·같은 두 팀의 글이 아직 없는 경기.
- 문장에 쓰는 것은 점수·승패·시리즈 전적·다음 경기·출처뿐. 자료에 없는 것은 쓰지 않고 '확인 뒤 덧붙인다'고 적는다.
- 기본은 미리보기(출력만). --write 는 src/content/drafts/ 에 초안 저장, --publish 는 articles/ 에 바로 게시.
"""
import json, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / 'src' / 'content'
KST = timezone(timedelta(hours=9))
NAMES = json.loads((C / 'team-names-ko.json').read_text(encoding='utf-8'))
ARTS = C / 'articles'


def josa(word, pair):
    """받침 유무에 따라 이/가, 은/는, 을/를 중 하나를 붙인다."""
    last = word[-1]
    code = ord(last) - 0xAC00
    has = 0 <= code < 11172 and code % 28 != 0
    return word + (pair[0] if has else pair[1])


def ko(lg, ab):
    return NAMES.get(lg, {}).get(ab, ab)


def existing_pairs():
    seen = set()
    for p in ARTS.glob('*.md'):
        t = p.read_text(encoding='utf-8')
        d = re.search(r'^date:\s*"([^"]+)"', t, re.M)
        tm = re.search(r'^teams:\s*\[([^\]]*)\]', t, re.M)
        if d and tm:
            seen.add((d.group(1), frozenset(x.strip(' "') for x in tm.group(1).split(','))))
    return seen


def series_note(g, ps):
    for s in ps.get('lcs', []):
        for x in s['games']:
            if x.get('id') == g['id']:
                lead = {s['home']: s['hw'], s['away']: s['aw']}
                done = s['hw'] == 4 or s['aw'] == 4
                a, b = sorted(lead, key=lambda k: -lead[k])
                nxt = [y for y in s['games'] if not y.get('result')]
                return {'name': 'NLCS' if s['league'] == 'NL' else 'ALCS', 'g': x['g'], 'lead': (a, lead[a], lead[b]),
                        'done': done, 'next': nxt[0]['kst'] if nxt else ''}
    return None


def build(g, ps, nba):
    lg = g['league']; a, h = g['away'], g['home']
    as_, hs = g['away_score'], g['home_score']
    win, lose = (h, a) if hs > as_ else (a, h)
    ws, ls = max(hs, as_), min(hs, as_)
    t = datetime.fromisoformat(g['start_kst']).astimezone(KST)
    kst = t.strftime('%Y.%m.%d %H:%M KST')
    sn = series_note(g, ps) if lg == 'MLB' else None
    pre = lg == 'NBA' and t < datetime.fromisoformat(nba.get('opening_kst', '2099-01-01T00:00+09:00'))
    W, L = ko(lg, win), ko(lg, lose)
    kicker = {'MLB': f"MLB · {sn['name']} GAME {sn['g']} RECAP" if sn else 'MLB · RESULT', 'NBA': 'NBA · PRESEASON RECAP' if pre else 'NBA · RESULT'}[lg]
    if sn:
        la, lw, ll = sn['lead']
        sub = (f"{ko(lg, la)}, {sn['name']} {lw}승 {ll}패로 월드시리즈 진출" if sn['done'] else f"{sn['name']} {sn['g']}차전, 시리즈 {lw}–{ll} {ko(lg, la)} 리드")
    else:
        sub = f"{ws - ls}점 차 승리"
    title = f"{W} {ws}–{ls} {L}"
    lines = [f"{josa(W, '이가')} 한국시간 {t.month}월 {t.day}일 {t.strftime('%H:%M')} 열린 경기에서 {josa(L, '을를')} 꺾었다. 최종 스코어는 {W} {ws}, {L} {ls}."]
    stats = [f"{ws}–{ls} | {W} 승리", f"{ws - ls}점 차 | {'프리시즌' if pre else '최종'}"]
    if sn:
        la, lw, ll = sn['lead']
        stats.append(f"{lw}–{ll} | {ko(lg, la)} {'최종 전적' if sn['done'] else '시리즈 리드'}")
        if sn['next']:
            stats.append(f"다음 경기 | {sn['next']} KST")
    src = g.get('source_url', '')
    body = '\n'.join(lines) + '\n\n::: stats\n' + '\n'.join(stats) + '\n:::\n\n'
    body += "::: angle SFANDOM 체크\n이닝별·쿼터별 점수, 선수 기록, 투수 기록은 공식 박스스코어 확인 뒤 이 기사에 덧붙인다.\n:::\n\n"
    body += f"공식 자료: [ESPN 경기 페이지]({src})." if src else ''
    slug = f"{win.lower()}-{lose.lower()}-{t.strftime('%Y%m%d')}-recap"
    fm = ['---', 'kind: "news"', f'date: "{t.strftime("%Y-%m-%d")}"', 'priority: 900', f'title: "{title}"', f'subtitle: "{sub}"',
          f'kicker: "{kicker}"', f'meta: "{kst} · {a} {as_}–{hs} {h}"', f'league: "{lg}"', 'image: ""', 'image_alt: ""', 'credit: ""',
          f'edition: "{t.strftime("%Y-%m-%d")}"', f'slug: "{slug}"', f'teams: ["{a}","{h}"]',
          'sources: ' + json.dumps([{'label': 'ESPN 경기 페이지', 'url': src}], ensure_ascii=False) if src else 'sources: []', '---']
    return slug, '\n'.join(fm) + '\n' + body + '\n'


def main():
    snap = json.loads((C / 'games-snapshot.json').read_text(encoding='utf-8'))
    ps = json.loads((C / 'postseason-2026.json').read_text(encoding='utf-8'))
    nba = json.loads((C / 'nba-2026.json').read_text(encoding='utf-8'))
    seen = existing_pairs(); force = '--all' in sys.argv; out = 0
    for lg in ('MLB', 'NBA'):
        for g in (snap['leagues'].get(lg, {}).get('games') or []):
            if g.get('status') != 'final' or g.get('home_score') is None:
                continue
            key = (datetime.fromisoformat(g['start_kst']).astimezone(KST).strftime('%Y-%m-%d'), frozenset({g['away'], g['home']}))
            if key in seen and not force:
                continue
            slug, text = build(g, ps, nba); out += 1
            d = datetime.fromisoformat(g['start_kst']).astimezone(KST).strftime('%Y-%m-%d')
            name = f'{d}-{slug}.md'
            if '--publish' in sys.argv:
                (ARTS / name).write_text(text, encoding='utf-8')
            elif '--write' in sys.argv:
                (C / 'drafts').mkdir(exist_ok=True); (C / 'drafts' / name).write_text(text, encoding='utf-8')
            else:
                print('────', name); print(text)
    print(f'{out} article(s)')


if __name__ == '__main__':
    main()
