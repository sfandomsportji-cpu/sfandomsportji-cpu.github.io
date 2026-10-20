"""주간 인기 글 스냅샷 (표준 라이브러리만 사용).

지난 한 주(월~일, 한국시간) 팬 보드 글을 '댓글 수'로만 순위를 매긴다. 외부 카운터·조회수는 쓰지 않는다.
빌드가 Supabase 공개 읽기 API 에서 한 번 읽어 src/content/weekly/<연도>-w<주차>.json 로 저장하고,
이미 있는 주는 다시 읽지 않는다. 글이 MIN_POSTS 편 미만이거나 읽기에 실패하면 아무것도 만들지 않는다.
저장하는 것: 제목(머리말 제외) · 채널 · 닉네임 · 댓글 수 · 작성일. 본문은 저장하지 않는다.
"""
import datetime as dt
import json
import re
import urllib.parse
import urllib.request

KST = dt.timezone(dt.timedelta(hours=9))
MIN_POSTS = 3
TOP_N = 10
QUICK = '[한줄]'


def last_week(today: dt.date):
    """오늘 이전에 끝난 마지막 월~일 주: (iso연도, 주차, 월요일, 다음 월요일)."""
    monday = today - dt.timedelta(days=today.weekday())
    start = monday - dt.timedelta(days=7)
    y, w, _ = start.isocalendar()
    return y, w, start, monday


def split_title(title: str):
    m = re.match(r'^\[([^\]]{1,20})\]\s*(.*)$', title or '')
    return (m.group(1), m.group(2).strip()) if m else ('자유', (title or '').strip())


def make_snapshot(year, week, start, end, posts, comment_counts):
    """posts: [{id,title,nickname,created_at}], comment_counts: {id: n}. 순위는 댓글 수 → 최신순."""
    rows = []
    for p in posts:
        if str(p.get('title', '')).startswith(QUICK):
            continue
        ch, title = split_title(p.get('title', ''))
        if not title:
            continue
        rows.append({'channel': ch, 'title': title[:90], 'nickname': str(p.get('nickname') or '익명')[:20],
                     'comments': int(comment_counts.get(p['id'], 0)), 'created': str(p.get('created_at', ''))[:10]})
    if len(rows) < MIN_POSTS:
        return None
    rows.sort(key=lambda r: (r['comments'], r['created']), reverse=True)
    chans = {}
    for r in rows:
        chans[r['channel']] = chans.get(r['channel'], 0) + 1
    return {'id': f'{year}-w{week:02d}', 'start': start.isoformat(), 'end': (end - dt.timedelta(days=1)).isoformat(),
            'posts': len(rows), 'comments': sum(r['comments'] for r in rows),
            'channels': dict(sorted(chans.items(), key=lambda kv: -kv[1])), 'top': rows[:TOP_N]}


def _get(cfg, path):
    req = urllib.request.Request(cfg['url'] + path, headers={'apikey': cfg['key'], 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_snapshot(cfg, year, week, start, end):
    """Supabase 에서 지난 주 글·댓글을 읽어 스냅샷을 만든다. 실패하면 None."""
    a = dt.datetime.combine(start, dt.time(), KST).isoformat()
    b = dt.datetime.combine(end, dt.time(), KST).isoformat()
    q = urllib.parse.quote
    try:
        posts = _get(cfg, f'/rest/v1/posts?select=id,title,nickname,created_at&status=eq.published'
                          f'&created_at=gte.{q(a)}&created_at=lt.{q(b)}&order=created_at.desc&limit=500')
        counts = {}
        ids = [p['id'] for p in posts]
        for i in range(0, len(ids), 50):
            chunk = ','.join(ids[i:i + 50])
            for c in _get(cfg, f'/rest/v1/comments?select=post_id&post_id=in.({chunk})&limit=2000'):
                counts[c['post_id']] = counts.get(c['post_id'], 0) + 1
    except Exception as e:  # 네트워크·권한·스키마 문제: 빌드를 막지 않는다
        print(f'weekly: 건너뜀 ({type(e).__name__})')
        return None
    return make_snapshot(year, week, start, end, posts, counts)
