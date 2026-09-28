"""SFANDOM 모닝 에디션 자동 초안 생성기.

기존 운영 규칙(README / 이전 PR)을 그대로 따릅니다.
- index.html 의 4개 슬롯만 교체:
  daily-news-slot / kairo-feature-slot / next-match-slot / player-spotlight-slot
- 교체 전 전체 스냅샷을 archive/morning/YYYY-MM-DD.html 로 보존
- 공통 레이아웃, CSS/JS, 헤더/푸터, 커뮤니티 등 다른 영역은 건드리지 않음
"""
import datetime
import os
import pathlib
import re
import sys
from zoneinfo import ZoneInfo

import anthropic

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
ARCHIVE_DIR = ROOT / "archive" / "morning"
PROMPT = ROOT / "scripts" / "edition_prompt.md"
MODEL = os.environ.get("SFANDOM_MODEL", "claude-sonnet-5")

SLOTS = ["daily-news-slot", "kairo-feature-slot", "next-match-slot", "player-spotlight-slot"]
MIN_CHARS = {
    "daily-news-slot": 2500,
    "kairo-feature-slot": 1400,
    "next-match-slot": 1400,
    "player-spotlight-slot": 1200,
}
ALLOWED_IMG =("https://www.mlbstatic.com/", "https://img.mlbstatic.com/", "assets/")
FORBIDDEN = {
    r"<\s*script": "<script>",
    r"<\s*style": "<style>",
    r"<\s*iframe": "<iframe>",
    r"\sstyle\s*=": "인라인 style",
    r"\son[a-z]+\s*=": "인라인 이벤트(onclick 등)",
    r"!important": "!important",
    r"javascript:": "javascript: 링크",
    # 작은따옴표·따옴표 없는 src/href/srcset은 아래 출처 검사를 우회하므로 금지
    r"\s(?:src|href|srcset)\s*=\s*(?![\s\"])": "큰따옴표 없는 src/href/srcset",
}
# 현재 게시본·Archive 슬롯이 쓰는 태그 + 기본 서식 태그만 허용
# (object/embed/form/meta/base/link/svg/video 등은 차단)
ALLOWED_TAGS = {
    "a", "article", "b", "blockquote", "br", "div", "em", "figcaption", "figure",
    "h2", "h3", "h4", "header", "i", "img", "li", "ol", "p", "section", "small",
    "span", "strong", "time", "ul",
}


def fail(msg: str) -> None:
    print(f"::error::{msg}")
    sys.exit(1)


def set_output(key: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def slot_pattern(sid: str) -> re.Pattern:
    # 슬롯 섹션 안에는 중첩 <section>이 없으므로 첫 </section>까지가 한 슬롯
    return re.compile(r'<section id="%s"[^>]*>.*?</section>' % re.escape(sid), re.S)


def extract_slots(html: str, where: str) -> dict:
    out = {}
    for sid in SLOTS:
        found = slot_pattern(sid).findall(html)
        if len(found) != 1:
            fail(f"{where}에서 #{sid} 슬롯이 {len(found)}개 발견됨 (정확히 1개여야 함)")
        out[sid] = found[0]
    return out


def validate(sections: dict, today_dot: str) -> None:
    joined = "\n".join(sections.values())
    for pat, name in FORBIDDEN.items():
        if re.search(pat, joined, re.I):
            fail(f"금지 요소 포함: {name}")
    for tag in sorted({t.lower() for t in re.findall(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9-]*)", joined)}):
        if tag not in ALLOWED_TAGS:
            fail(f"허용되지 않은 태그: <{tag}>")
    for tag in re.findall(r"<img\b[^>]*>", joined):
        srcs = re.findall(r'\ssrc="([^"]+)"', tag)
        # MLB 이미지 URL 자체에 쉼표(w_900,q_auto)가 있으므로 "쉼표+공백"으로만 후보를 나눔
        srcs += [u.split()[0] for s in re.findall(r'srcset="([^"]+)"', tag)
                 for u in re.split(r",\s+", s.strip()) if u.strip()]
        for src in srcs:
            if not src.strip().startswith(ALLOWED_IMG):
                fail(f"허용되지 않은 이미지 출처: {src}")
        if "portrait-safe" not in tag:
            fail("img에 portrait-safe 클래스가 없습니다.")
        for attr in ("alt=", "width=", "height=", 'loading="lazy"'):
            if attr not in tag:
                fail(f"img에 {attr} 속성이 없습니다.")
    for href in re.findall(r'href="([^"]+)"', joined):
        if not href.startswith("https://"):
            fail(f"외부 링크는 https만 허용: {href}")
    for a in re.findall(r"<a\b[^>]*>", joined):
        if 'target="_blank"' not in a or "noopener" not in a:
            fail(f'링크에 target="_blank" rel="noopener noreferrer"가 없습니다: {a[:80]}')
    # 운영 규칙: Pick 제외, 베팅 권유 금지
    bad = re.search(r"\bPICKS?\b|오늘의 픽|추천 픽|픽\s*[:：]|배당률?|베팅|토토", re.sub(r"<[^>]+>", " ", joined))
    if bad:
        fail(f"Pick/베팅 관련 표현 포함: {bad.group(0)}")
    m = re.search(r"MORNING EDITION[^<]*?(\d{4}\.\d{2}\.\d{2})", sections["daily-news-slot"])
    if not m or m.group(1) != today_dot:
        fail("Daily News의 MORNING EDITION 날짜가 오늘 날짜가 아닙니다.")
    # 롱폼 유지: 현재 게시본(약 3,700 / 2,100 / 2,100 / 1,700자)의 약 70% 이상
    for sid, sec in sections.items():
        n = len(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", sec)).strip())
        if n < MIN_CHARS[sid]:
            fail(f"#{sid} 분량 부족: {n}자 (최소 {MIN_CHARS[sid]}자)")


def check_residue(old: dict, new: dict) -> None:
    """이전 에디션 헤드라인이 새 슬롯에 남아 있으면 실패 (운영 매뉴얼 5.3)."""
    joined = "\n".join(new.values())
    for sec in old.values():
        for h in re.findall(r"<h[23][^>]*>(.*?)</h[23]>", sec, re.S):
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()
            if len(text) >= 12 and text in re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", joined)):
                fail(f"이전 에디션 헤드라인이 그대로 남아 있습니다: {text[:60]}")


def call_claude(user_msg: str) -> str:
    client = anthropic.Anthropic()
    system = PROMPT.read_text(encoding="utf-8")
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 20}]
    messages = [{"role": "user", "content": user_msg}]
    text = ""
    for _ in range(8):
        with client.messages.stream(
            model=MODEL, max_tokens=32000, system=system,
            tools=tools, messages=messages,
        ) as stream:
            resp = stream.get_final_message()
        text += "".join(b.text for b in resp.content if b.type == "text")
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        if resp.stop_reason == "max_tokens":
            fail("출력이 너무 길어 잘렸습니다.")
        return text
    fail("검색 단계가 너무 많이 반복되었습니다.")


def main() -> None:
    now = datetime.datetime.now(ZoneInfo("Asia/Seoul"))
    today_dot = now.strftime("%Y.%m.%d")
    today_dash = now.strftime("%Y-%m-%d")

    html = INDEX.read_text(encoding="utf-8")
    current = extract_slots(html, "index.html")

    m = re.search(r"MORNING EDITION[^<]*?(\d{4})\.(\d{2})\.(\d{2})", current["daily-news-slot"])
    if not m:
        # 이전 날짜를 모르면 Archive 보존을 보장할 수 없으므로 교체하지 않음
        fail("현재 게시본에서 MORNING EDITION 날짜를 찾지 못해 Archive 보존이 불가능합니다.")
    prev_date = "-".join(m.groups())
    if prev_date == today_dash:
        print("오늘 에디션이 이미 게시되어 있어 건너뜁니다.")
        set_output("changed", "false")
        return

    reference = "\n\n".join(current[s] for s in SLOTS)
    user_msg = f"""오늘은 {today_dot} KST입니다. 오늘자 SFANDOM 모닝 에디션을 작성하세요.

아래는 현재 게시 중인 4개 슬롯 HTML입니다. 태그 구조, id, class, 섹션 구성,
분량, 톤을 그대로 따르되 내용은 웹 검색으로 확인한 오늘 기준 최신 정보로 새로 쓰세요.
어제 기사 내용을 재사용하지 마세요.

<current_slots>
{reference}
</current_slots>

출력 형식 (이 두 블록만 출력):
<edition>
(4개 <section> 전체를 순서대로: {", ".join("#" + s for s in SLOTS)})
</edition>
<summary>
(승인자용 마크다운 요약: 슬롯별 헤드라인 한 줄 + 핵심 수치 + 확인한 출처 링크)
</summary>"""

    text = call_claude(user_msg)

    m_ed = re.search(r"<edition>(.*?)</edition>", text, re.S)
    if not m_ed:
        fail("응답에서 <edition> 블록을 찾지 못했습니다.")
    new = extract_slots(m_ed.group(1), "생성 결과")
    validate(new, today_dot)
    check_residue(current, new)

    # 이전 에디션 전체 스냅샷 보존 (상대경로가 깨지지 않도록 base 지정)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    snap = ARCHIVE_DIR / f"{prev_date}.html"
    if not snap.exists():
        snap_html = html.replace("<head>", '<head>\n<base href="/">', 1)
        # Archive 사본은 검색 노출 금지 (홈과 중복 방지)
        snap_html = re.sub(r'<meta name="robots" content="[^"]*"\s*/?>',
                           '<meta name="robots" content="noindex,follow" />', snap_html, count=1)
        snap.write_text(snap_html, encoding="utf-8")
    # Archive 저장 확인 전에는 원본을 교체하지 않음 (운영 매뉴얼 6.5)
    if "daily-news-slot" not in snap.read_text(encoding="utf-8"):
        fail(f"Archive 스냅샷 {snap.name} 확인 실패 — 교체를 중단합니다.")

    updated = html
    for sid in SLOTS:
        updated = updated.replace(current[sid], new[sid], 1)
    INDEX.write_text(updated, encoding="utf-8")

    m_sum = re.search(r"<summary>(.*?)</summary>", text, re.S)
    summary = m_sum.group(1).strip() if m_sum else "(요약 없음)"
    body = f"""## {today_dot} 모닝 에디션 초안

{summary}

---
**변경 범위:** index.html의 4개 슬롯만 교체 · 이전 에디션은 `archive/morning/{prev_date}.html`에 보존 · CSS/JS·레이아웃 변경 없음

**승인 방법**
- ✅ 게시: **Merge pull request** → 1~2분 뒤 sfandom.com 반영
- ✏️ 수정: Files changed에서 직접 고친 뒤 Merge
- ❌ 폐기: **Close pull request** (사이트는 기존 에디션 유지)

> 자동 작성 초안입니다. 스코어·기록·부상 정보는 출처 링크로 확인 후 승인해 주세요.
"""
    out = pathlib.Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "pr_body.md"
    out.write_text(body, encoding="utf-8")
    set_output("changed", "true")
    print("에디션 초안 작성 완료")


if __name__ == "__main__":
    main()
