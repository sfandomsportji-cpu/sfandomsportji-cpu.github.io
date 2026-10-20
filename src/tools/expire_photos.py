#!/usr/bin/env python3
"""자료사진 3일 보관 후 자동 삭제.

- assets/photos/ 안 파일은 처음 발견된 날(KST)을 assets/photos/manifest.json 에 기록한다.
- 기록일로부터 3일(RETAIN_DAYS)이 지나면 파일을 지우고, 그 사진을 대표 이미지로 쓰던 글은
  image / image_alt / credit 을 비우고 photo_* 줄과 '사진 안내' 문단을 함께 지운다.
  (이미지가 비면 build_article_cards.py 가 만든 공유 카드를 대신 쓴다)
- 팀 로고(assets/teams), 직접 만든 합성 로고(assets/editorial)는 대상이 아니다.
- `--all` : 기한과 무관하게 지금 있는 사진을 모두 폐기한다.
"""
import json, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PHOTOS = ROOT / 'assets' / 'photos'
MANIFEST = PHOTOS / 'manifest.json'
ARTICLES = ROOT / 'src' / 'content' / 'articles'
RETAIN_DAYS = 3
KST = timezone(timedelta(hours=9))


def strip_article(path, gone):
    text = path.read_text(encoding='utf-8')
    m = re.match(r'(---\n)(.*?)(\n---\n)(.*)\Z', text, re.S)
    if not m:
        return False
    fm, body = m.group(2), m.group(4)
    hit = re.search(r'^image:\s*"(/assets/photos/[^"]+)"', fm, re.M)
    if not (hit and hit.group(1) in gone) and not any(g in body for g in gone):
        return False
    lines = []
    for ln in fm.split('\n'):
        if re.match(r'image:\s', ln):
            ln = 'image: ""'
        elif re.match(r'image_alt:\s', ln):
            ln = 'image_alt: ""'
        elif re.match(r'credit:\s', ln):
            ln = 'credit: ""'
        elif ln.startswith('photo_'):
            continue
        lines.append(ln)
    paras = re.split(r'\n{2,}', body)
    def clean(p):
        if p.startswith('::: split'):  # 분할 블록은 통째로 지우지 않고 사진 줄만 뺀다
            return '\n'.join(l for l in p.split('\n') if not (l.startswith('@photo') and any(g in l for g in gone)))
        return None if ('사진 안내' in p or any(g in p for g in gone)) else p
    paras = [q for q in map(clean, paras) if q is not None]
    path.write_text(m.group(1) + '\n'.join(lines) + m.group(3) + '\n\n'.join(paras).rstrip('\n') + '\n', encoding='utf-8')
    return True


def main():
    PHOTOS.mkdir(parents=True, exist_ok=True)
    today = datetime.now(KST).date()
    reg = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {}
    files = sorted(p.name for p in PHOTOS.iterdir() if p.is_file() and p.name != 'manifest.json')
    for n in files:
        reg.setdefault(n, today.isoformat())
    force = '--all' in sys.argv
    expired = [n for n in files if force or (today - datetime.fromisoformat(reg[n]).date()).days >= RETAIN_DAYS]
    gone = {f'/assets/photos/{n}' for n in expired}
    changed = [p.name for p in sorted(ARTICLES.glob('*.md')) if gone and strip_article(p, gone)]
    for n in expired:
        (PHOTOS / n).unlink()
    reg = {k: v for k, v in reg.items() if k in files and k not in expired}
    MANIFEST.write_text(json.dumps(reg, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(f'Photos: {len(files)} found, {len(expired)} expired, {len(changed)} articles cleaned.')


if __name__ == '__main__':
    main()
