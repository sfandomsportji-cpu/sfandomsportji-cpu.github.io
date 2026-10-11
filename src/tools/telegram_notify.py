#!/usr/bin/env python3
"""새 글을 텔레그램 채널로 보낸다 (표준 라이브러리만 사용).

- 환경변수 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 가 없으면 아무것도 하지 않고 정상 종료한다 (GitHub Secrets 에만 둔다).
- 보낸 글 주소는 src/content/telegram-sent.json 에 기록해 같은 글을 두 번 보내지 않는다 (개인 정보는 저장하지 않음).
- 기록 파일이 없으면 지금 있는 글을 전부 '이미 보냄'으로 기록만 하고 보내지 않는다 (처음 켤 때 86편이 쏟아지는 것 방지).
- 한 번에 최대 MAX_PER_RUN 편만 보내고 나머지는 다음 실행으로 넘긴다. 실패하면 기록하지 않고 멈춘다.
- 사이트가 배포될 시간을 주려고 보내기 전에 WAIT_SECONDS 만큼 기다린다.
"""
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request

SRC = pathlib.Path(__file__).resolve().parents[1]
LOG = SRC / 'content' / 'telegram-sent.json'
MAX_PER_RUN = 5
WAIT_SECONDS = 120


def pending(articles, sent):
    return [a for a in sorted(articles, key=lambda x: (x.date, x.file)) if a.url not in sent]


def message(base, a):
    return f'[{a.section} · {a.league}] {a.headline}\n\n{a.excerpt}\n\n{base}{a.url}'


def send(token, chat_id, text):
    data = urllib.parse.urlencode({'chat_id': chat_id, 'text': text}).encode()
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode()).get('ok') is True


def main():
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN', ''), os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat:
        print('telegram: 설정 없음, 건너뜀')
        return
    sys.path.insert(0, str(SRC))
    sys.dont_write_bytecode = True
    import build  # noqa: E402  (글 목록과 주소만 사용, 페이지는 쓰지 않음)
    arts = build.ARTICLES
    if not LOG.exists():
        LOG.write_text(json.dumps(sorted(a.url for a in arts), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'telegram: 첫 실행 — 기존 글 {len(arts)}편을 보냄 처리만 하고 발송 안 함')
        return
    sent = set(json.loads(LOG.read_text(encoding='utf-8')))
    todo = pending(arts, sent)[:MAX_PER_RUN]
    if not todo:
        print('telegram: 새 글 없음')
        return
    time.sleep(WAIT_SECONDS)
    for a in todo:
        try:
            ok = send(token, chat, message(build.BASE, a))
        except Exception as e:  # 토큰이 로그에 찍히지 않게 예외 종류만 출력
            print(f'telegram: 발송 실패 ({type(e).__name__}) — 중단')
            break
        if not ok:
            print('telegram: 발송 거절 — 중단')
            break
        sent.add(a.url)
        LOG.write_text(json.dumps(sorted(sent), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'telegram: 보냄 {a.url}')
        time.sleep(1.5)


if __name__ == '__main__':
    main()
