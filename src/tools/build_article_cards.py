#!/usr/bin/env python3
"""글별 1200x630 공유 미리보기 카드(PNG)를 만든다.

- 대상: src/content/articles/*.md 중 front matter `image`가 비어 있는 글.
- 출력: assets/share/cards/<파일명>-<해시6>.png  (제목이 바뀌면 해시가 바뀌어 새 카드가 생기고, 옛 카드는 지운다)
- 파일명 규칙은 card_name() 하나만 쓰고, build.py 가 이 함수를 import 해서 같은 파일을 찾는다.
- 한글 폰트(Noto Sans CJK KR)가 없으면 카드를 만들지 않고 정상 종료한다 (build.py 는 대표 카드로 대체).
"""
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTICLES = ROOT / 'src' / 'content' / 'articles'
OUT = ROOT / 'assets' / 'share' / 'cards'
MARK = ROOT / 'assets' / 'brand' / 'sfandom-mark-512.png'
W, H = 1200, 630
FONT_FILES = ['/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
              '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
SECTION = {'news': 'NEWS', 'analysis': 'ANALYSIS', 'magazine': 'MAGAZINE'}


def load_font(size, bold=True):
    from PIL import ImageFont
    path = Path(FONT_FILES[0 if bold else 1])
    if not path.exists():
        return None
    for i in range(6):
        try:
            f = ImageFont.truetype(str(path), size, index=i)
        except OSError:
            return None
        if 'KR' in ' '.join(f.getname()):
            return f
    return None


def front_matter(path):
    m = re.match(r'---\n(.*?)\n---\n', path.read_text(encoding='utf-8'), re.S)
    fm = {}
    for line in m.group(1).splitlines() if m else []:
        if ':' not in line:
            continue
        k, v = line.split(':', 1)
        v = v.strip()
        try:
            fm[k.strip()] = json.loads(v)
        except json.JSONDecodeError:
            fm[k.strip()] = v
    return fm


def card_key(fm):
    headline = f"{fm.get('title', '')} {fm.get('subtitle', '')}".strip()
    return hashlib.sha1(f"{headline}|{fm.get('league', 'MLB')}|{fm.get('kind', 'news')}".encode()).hexdigest()[:6]


def card_name(stem, fm):
    """build.py 도 이 함수로 파일명을 찾는다 (PIL 없이 import 가능)."""
    return f'{stem}-{card_key(fm)}.png'


def wrap(draw, text, font, width, max_lines):
    lines, cur = [], ''
    for word in text.split(' '):
        trial = (cur + ' ' + word).strip()
        if draw.textlength(trial, font=font) <= width:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = word
        while draw.textlength(cur, font=font) > width:  # 공백 없는 긴 낱말
            k = len(cur)
            while k > 1 and draw.textlength(cur[:k], font=font) > width:
                k -= 1
            lines.append(cur[:k]); cur = cur[k:]
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and draw.textlength(lines[-1] + '…', font=font) > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + '…'
    return lines


def render(fm, dest):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (W, H), '#090C17')
    px = im.load()
    for y in range(H):
        for x in range(W):
            g = max(0.0, 1 - ((x - 1020)**2 / 870000 + (y - 80)**2 / 480000))
            r = max(0.0, 1 - ((x - 250)**2 / 430000 + (y - 620)**2 / 500000))
            px[x, y] = (int(9 + 13*g + 5*r), int(12 + 11*g), int(23 + 28*g + 6*r))
    d = ImageDraw.Draw(im, 'RGBA')
    d.polygon([(900, 0), (1200, 0), (1200, 630), (1100, 630)], fill=(200, 16, 46, 22))
    d.rectangle((0, 0, 14, H), fill=(215, 27, 54, 255))
    if MARK.exists():
        mark = Image.open(MARK).convert('RGBA').resize((64, 64), Image.Resampling.LANCZOS)
        im.paste(mark, (70, 52), mark)
    d.text((148, 58), 'SFANDOM', font=load_font(40), fill=(249, 250, 253, 255))
    badge = f"{SECTION.get(fm.get('kind', 'news'), 'NEWS')}  ·  {fm.get('league', 'MLB')}"
    bf = load_font(24)
    bw = d.textlength(badge, font=bf)
    d.rounded_rectangle((1130 - bw - 40, 56, 1130, 108), radius=26, fill=(215, 27, 54, 255))
    d.text((1130 - bw - 20, 66), badge, font=bf, fill=(255, 255, 255, 255))
    title, sub = str(fm.get('title', '')).strip(), str(fm.get('subtitle', '')).strip()
    tf, sf = load_font(72), load_font(40, bold=False)
    tl = wrap(d, title, tf, 1060, 2)
    y = 170
    for line in tl:
        d.text((70, y), line, font=tf, fill=(249, 250, 253, 255)); y += 92
    y += 14
    for line in wrap(d, sub, sf, 1060, 2 if len(tl) < 2 else 1):
        d.text((70, y), line, font=sf, fill=(245, 65, 85, 255)); y += 56
    d.line((70, 548, 1130, 548), fill=(245, 245, 245, 50), width=2)
    d.text((70, 563), 'sfandom.com', font=load_font(26), fill=(224, 228, 237, 255))
    date = str(fm.get('date', '')).replace('-', '.')
    dw = d.textlength(date, font=load_font(26, bold=False))
    d.text((1130 - dw, 563), date, font=load_font(26, bold=False), fill=(167, 180, 199, 255))
    im.save(dest, 'PNG', optimize=True)


def main():
    if load_font(20) is None:
        print('Noto Sans CJK KR 없음: 글별 카드 생성을 건너뜁니다.')
        return
    OUT.mkdir(parents=True, exist_ok=True)
    keep, made = set(), 0
    for p in sorted(ARTICLES.glob('*.md')):
        fm = front_matter(p)
        if str(fm.get('image', '')).strip():
            continue
        name = card_name(p.stem, fm)
        keep.add(name)
        if not (OUT / name).exists():
            render(fm, OUT / name); made += 1
    for old in OUT.glob('*.png'):
        if old.name not in keep:
            old.unlink()
    print(f'Article cards: {len(keep)} total, {made} new.')


if __name__ == '__main__':
    main()
