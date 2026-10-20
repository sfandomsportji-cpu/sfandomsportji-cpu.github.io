#!/usr/bin/env python3
"""끝난 경기의 '결과 기사' 초안을 확인된 자료만으로 만든다 (Claude 호출 없음, 비용 없음).

- 자료: src/content/games-snapshot.json (ESPN) + postseason-2026.json (시리즈 전적) + nba-2026.json (개막일).
- 대상: MLB·NBA 중 status == final 이고, 같은 날짜·같은 두 팀의 글이 아직 없는 경기.
- 문장에 쓰는 것은 점수·승패·시리즈 전적·다음 경기·출처뿐. 자료에 없는 것은 쓰지 않고 '확인 뒤 덧붙인다'고 적는다.
- 기본은 미리보기(출력만). --write 는 src/content/drafts/ 에 초안 저장, --publish 는 articles/ 에 바로 게시.
- --alerts : 자동 작업용. ① 경기가 끝나면 결과 초안, ② 경기 시작 2시간 안으로 들어오면 프리뷰 초안을 drafts/ 에 만들고
  텔레그램으로 알린다 (TELEGRAM_BOT_TOKEN·TELEGRAM_CHAT_ID 가 있을 때). 이미 알린 경기는 auto-alerts.json 에 기록해 다시 알리지 않는다.
  게시는 하지 않는다 — 초안만 만들고 사람이 확인한 뒤 올린다.
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


def existing_pairs(preview=False):
    """(날짜, 두 팀) 쌍. preview=True 면 프리뷰 글만, False 면 결과 글만 모은다."""
    seen = set()
    for p in ARTS.glob('*.md'):
        t = p.read_text(encoding='utf-8')
        d = re.search(r'^date:\s*"([^"]+)"', t, re.M)
        tm = re.search(r'^teams:\s*\[([^\]]*)\]', t, re.M)
        is_pre = bool(re.search(r'^(kicker|slug):.*(preview|프리뷰)', t, re.M | re.I))
        if d and tm and is_pre == preview:
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


def preview(g, ps):
    lg = g['league']; a, h = g['away'], g['home']
    t = datetime.fromisoformat(g['start_kst']).astimezone(KST)
    A, H = ko(lg, a), ko(lg, h)
    sn = None
    for s_ in ps.get('lcs', []) if lg == 'MLB' else []:
        if {s_['home'], s_['away']} != {a, h}:
            continue
        nxt = [x for x in s_['games'] if not x.get('result')]
        if not nxt or s_['hw'] == 4 or s_['aw'] == 4:
            continue
        lead = {s_['home']: s_['hw'], s_['away']: s_['aw']}
        top = max(lead, key=lambda k: lead[k]); low = min(lead.values())
        prior = [y['result'] for y in s_['games'] if y.get('result')]
        sn = (('NLCS' if s_['league'] == 'NL' else 'ALCS'), nxt[0]['g'], ko(lg, top), lead[top], low, prior)
    kicker = f"MLB · {sn[0]} GAME {sn[1]} PREVIEW" if sn else f"{lg} · PREVIEW"
    sub = f"{sn[0]} {sn[1]}차전, 시리즈 {sn[3]}–{sn[4]} {sn[2]} 리드" if sn and sn[3] != sn[4] else (f"{sn[0]} {sn[1]}차전" if sn else f"{A} vs {H}")
    stats = [f"{t.strftime('%m.%d %H:%M')} KST | 경기 시작"]
    if sn:
        stats.append(f"{sn[3]}–{sn[4]} | {sn[2]} 시리즈 리드")
        if sn[5]:
            stats.append("이전 경기 | " + ' · '.join(sn[5]))
    body = f"{A} 대 {H} 경기가 한국시간 {t.month}월 {t.day}일 {t.strftime('%H:%M')}에 시작한다.\n\n::: stats\n" + '\n'.join(stats) + "\n:::\n\n"
    body += "::: angle SFANDOM 체크\n선발 투수·출전 명단·부상 정보는 공식 발표를 확인한 뒤 반영한다. 확정되지 않은 선수는 적지 않는다.\n:::\n\n"
    src = g.get('source_url', '')
    body += f"공식 자료: [ESPN 경기 페이지]({src})." if src else ''
    slug = f"{a.lower()}-{h.lower()}-{t.strftime('%Y%m%d')}-preview"
    d = t.strftime('%Y-%m-%d')
    fm = ['---', 'kind: "news"', f'date: "{d}"', 'priority: 880', f'title: "{A} vs {H}"', f'subtitle: "{sub}"', f'kicker: "{kicker}"',
          f'meta: "{t.strftime("%Y.%m.%d %H:%M")} KST · {a} vs {h}"', f'league: "{lg}"', 'image: ""', 'image_alt: ""', 'credit: ""',
          f'edition: "{d}"', f'slug: "{slug}"', f'teams: ["{a}","{h}"]',
          ('sources: ' + json.dumps([{'label': 'ESPN 경기 페이지', 'url': src}], ensure_ascii=False)) if src else 'sources: []', '---']
    return slug, '\n'.join(fm) + '\n' + body + '\n'


UNSENT = []  # 텔레그램 설정이 없어 실제로는 보내지 못한 알림 — auto-alerts.json 의 unsent 에 남겨 '보낸 줄 아는' 일이 없게 한다


def notify(text):
    import os, urllib.parse, urllib.request
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN', ''), os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat:
        print('telegram: 설정 없음 — 알림은 보내지 못했습니다(초안은 만들어짐)')
        UNSENT.append(text.splitlines()[0][:120]); return True
    try:
        data = urllib.parse.urlencode({'chat_id': chat, 'text': text}).encode()
        with urllib.request.urlopen(urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=data), timeout=20) as r:
            return json.loads(r.read().decode()).get('ok') is True
    except Exception as e:  # 토큰이 로그에 찍히지 않게 예외 종류만 출력
        print(f'telegram: 발송 실패 ({type(e).__name__})'); return False


def alerts():
    snap = json.loads((C / 'games-snapshot.json').read_text(encoding='utf-8'))
    ps = json.loads((C / 'postseason-2026.json').read_text(encoding='utf-8'))
    nba = json.loads((C / 'nba-2026.json').read_text(encoding='utf-8'))
    LOG = C / 'auto-alerts.json'
    first = not LOG.exists()
    state = json.loads(LOG.read_text(encoding='utf-8')) if not first else {'recap': [], 'preview': []}
    seen_recap, seen_pre = existing_pairs(False), existing_pairs(True); now = datetime.now(KST); made = 0
    (C / 'drafts').mkdir(exist_ok=True)
    for lg in ('MLB', 'NBA'):
        for g in (snap['leagues'].get(lg, {}).get('games') or []):
            t = datetime.fromisoformat(g['start_kst']).astimezone(KST)
            key = (t.strftime('%Y-%m-%d'), frozenset({g['away'], g['home']}))
            if g.get('status') == 'final' and g.get('home_score') is not None and g['id'] not in state['recap']:
                if first or key in seen_recap:    # 처음 켤 때 · 이미 글이 있을 때는 알리지 않고 기록만
                    state['recap'].append(g['id']); continue
                slug, text = build(g, ps, nba)
                (C / 'drafts' / f"{t.strftime('%Y-%m-%d')}-{slug}.md").write_text(text, encoding='utf-8')
                title = re.search(r'^title: "(.*)"', text, re.M).group(1); sub = re.search(r'^subtitle: "(.*)"', text, re.M).group(1)
                if notify(f"[경기 종료 · 결과 초안] {title}\n{sub}\n\n초안이 만들어졌습니다. 확인 후 게시를 요청하세요.\n파일: src/content/drafts/{t.strftime('%Y-%m-%d')}-{slug}.md"):
                    state['recap'].append(g['id']); made += 1
            elif g.get('status') == 'scheduled' and g['id'] not in state['preview']:
                left = (t - now).total_seconds() / 3600
                if not (0 < left <= 2):
                    continue
                if key in seen_pre:
                    state['preview'].append(g['id']); continue
                slug, text = preview(g, ps)
                (C / 'drafts' / f"{t.strftime('%Y-%m-%d')}-{slug}.md").write_text(text, encoding='utf-8')
                title = re.search(r'^title: "(.*)"', text, re.M).group(1)
                if notify(f"[경기 2시간 전 · 프리뷰 초안] {title}\n{t.strftime('%m.%d %H:%M')} KST 시작\n\n초안이 만들어졌습니다. 선발·명단은 공식 발표 확인 뒤 반영합니다.\n파일: src/content/drafts/{t.strftime('%Y-%m-%d')}-{slug}.md"):
                    state['preview'].append(g['id']); made += 1
    try:  # 특집(오늘의 축구 7 등) 초안 — 실패해도 경기 알림은 그대로
        import auto_special
        for fid in auto_special.FEATURES:
            made += auto_special.run(fid, state, notify)
    except Exception as e:
        print(f'special: 건너뜀 ({type(e).__name__})')
    if UNSENT:
        state['unsent'] = (state.get('unsent', []) + [f"{now.strftime('%m-%d %H:%M')} {u}" for u in UNSENT])[-30:]
    LOG.write_text(json.dumps(state, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'auto-alerts: {made} new draft(s)' + (' (첫 실행: 기존 경기 기록만)' if first else ''))


def main():
    if '--alerts' in sys.argv:
        return alerts()
    snap = json.loads((C / 'games-snapshot.json').read_text(encoding='utf-8'))
    ps = json.loads((C / 'postseason-2026.json').read_text(encoding='utf-8'))
    nba = json.loads((C / 'nba-2026.json').read_text(encoding='utf-8'))
    seen = existing_pairs(False); force = '--all' in sys.argv; out = 0
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
