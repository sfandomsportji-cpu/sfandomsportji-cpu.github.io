#!/usr/bin/env python3
"""NPB 공식 사이트(npb.jp) 첫 화면의 오늘 경기 속보 줄에서 일정·점수를 받아 npb-snapshot.json 에 보관합니다.

- robots.txt 가 허용할 때만 받습니다. 실패하면 이전 값을 그대로 둡니다.
- 왼쪽(첫 번째) 팀이 홈입니다.
- 점수가 숫자이고 '試合終了'가 확인된 경기만 final 로 적습니다. 그 밖은 scheduled/live 입니다.
- KBO 는 공식 사이트가 자동 수집을 금지(robots.txt)하고 있어 대상이 아닙니다.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import pathlib
import re
import urllib.request
import urllib.robotparser
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "content" / "npb-snapshot.json"
KST = dt.timezone(dt.timedelta(hours=9))  # 일본 표준시와 한국 시간은 같은 UTC+9 입니다.
URL = "https://npb.jp/"
UA = "SFANDOM-site-scoreboard/1.0 (https://sfandom.com/)"
KEEP_DAYS = 10
TEAMS = {
    "阪神タイガース": ("HAN", "Hanshin Tigers"), "横浜DeNAベイスターズ": ("DeNA", "Yokohama DeNA BayStars"),
    "読売ジャイアンツ": ("YOM", "Yomiuri Giants"), "広島東洋カープ": ("HIR", "Hiroshima Carp"),
    "東京ヤクルトスワローズ": ("YAK", "Tokyo Yakult Swallows"), "中日ドラゴンズ": ("CHU", "Chunichi Dragons"),
    "福岡ソフトバンクホークス": ("SB", "Fukuoka SoftBank Hawks"), "北海道日本ハムファイターズ": ("NIP", "Hokkaido Nippon-Ham Fighters"),
    "オリックス・バファローズ": ("ORI", "Orix Buffaloes"), "東北楽天ゴールデンイーグルス": ("RAK", "Tohoku Rakuten Golden Eagles"),
    "千葉ロッテマリーンズ": ("LOT", "Chiba Lotte Marines"), "埼玉西武ライオンズ": ("SEI", "Saitama Seibu Lions"),
}


def fetch() -> str:
    # robotparser.read()에는 타임아웃 인수가 없어 공식 사이트 장애 시 빌드 전체가 지연된다.
    rp = urllib.robotparser.RobotFileParser("https://npb.jp/robots.txt")
    robots_request = urllib.request.Request("https://npb.jp/robots.txt", headers={"User-Agent": UA})
    with urllib.request.urlopen(robots_request, timeout=10) as r:
        rp.parse(r.read(200_000).decode("utf-8", "replace").splitlines())
    if not rp.can_fetch(UA, URL):
        raise RuntimeError("robots.txt 불허")
    request = urllib.request.Request(URL, headers={"User-Agent": UA})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=15) as r:
                return r.read(1_500_000).decode("utf-8", "replace")
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt:
                raise
            print(f"NPB 일시적 연결 실패, 1회 재시도: {exc!r}")
    raise RuntimeError("NPB 응답 없음")


def parse(page: str, today: dt.date) -> list[dict]:
    start = page.find('id="header_score"')
    if start < 0:
        # 공식 사이트는 경기가 없는 날 점수 블록 대신 "N월N일(요일)의 시합 없음"을 출력한다.
        # 해당 날짜를 정확히 확인한 경우에만 정상적인 0경기로 처리한다.
        today_no_games = rf'{today.month}月{today.day}日[（(][^）)]*[）)]の試合はありません'
        if re.search(today_no_games, page):
            print(f"NPB {today.isoformat()}: 공식 홈페이지에 오늘 경기 없음")
            return []
        raise ValueError("header_score 블록 없음 (오늘 경기 없음 표기도 확인되지 않음)")
    block = page[start:start + 12000]
    date_m = re.search(r'<div class="score_box date"><div>(\d{4})<br>(\d{1,2})/(\d{1,2})', block)
    if not date_m:
        raise ValueError("날짜 없음")
    day = dt.date(int(date_m[1]), int(date_m[2]), int(date_m[3]))
    if day != today:
        raise ValueError(f"표시된 NPB 점수 날짜 {day}가 점검 날짜 {today}와 다름")
    games = []
    for m in re.finditer(r'<div class="score_box">\s*<a href="(/scores/[^"]+)">(.*?)</a>\s*</div>', block, re.S):
        href, inner = m[1], m[2]
        names = re.findall(r'alt="([^"]+)"', inner)
        score = re.search(r'class="score">(.*?)</div>', inner, re.S)
        state = re.search(r'class="state">(.*?)</div>', inner, re.S)
        if len(names) < 2 or not score or not state or names[0] not in TEAMS or names[1] not in TEAMS:
            continue
        score_t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", score[1]))).strip()
        state_t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", state[1]))).strip()
        nums = re.fullmatch(r"(\d+)\s*[-–－]\s*(\d+)", score_t)
        time_m = re.search(r"(\d{1,2}):(\d{2})", state_t)
        status, a, h = "scheduled", None, None
        if nums:  # npb.jp 는 홈 팀을 왼쪽에 적는다: 왼쪽 점수 = 홈
            h, a = int(nums[1]), int(nums[2])
            status = "final" if "終了" in state_t else "live"
        if status != "final" and not time_m:
            if status == "scheduled":
                continue
        hour, minute = (int(time_m[1]), int(time_m[2])) if time_m else (0, 0)
        start_dt = dt.datetime.combine(day, dt.time(hour, minute), tzinfo=KST)
        home, away = TEAMS[names[0]], TEAMS[names[1]]
        if "中止" in state_t or "ノーゲーム" in state_t:
            status = "cancelled"
        games.append({
            "id": "NPB-" + href.strip("/").replace("/", "-"), "league": "NPB",
            "start_kst": start_dt.isoformat(timespec="minutes"),
            "away": away[0], "home": home[0], "away_name": away[1], "home_name": home[1],
            "status": status, "away_score": a, "home_score": h, "source_url": "https://npb.jp" + href,
        })
    if not games:
        raise ValueError("header_score 블록은 있지만 확인 가능한 경기 없음 (HTML 구조 확인 필요)")
    return games


def main() -> None:
    now = dt.datetime.now(KST)
    try:
        old = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = {"leagues": {"NPB": {"games": []}}}
    prev = old.get("leagues", {}).get("NPB", {}).get("games", [])
    try:
        fresh = parse(fetch(), now.date())
        error = ""
    except Exception as exc:  # 이전에 확인한 값은 지우지 않는다
        print(f"NPB 수집 실패: {exc!r} — 이전 값 유지")
        fresh, error = [], str(exc)[:80]
    merged = {g["id"]: g for g in prev}
    for g in fresh:
        old_g = merged.get(g["id"])
        # 경기 중·종료 화면에는 시작 시각이 없으니, 이전에 받은 시작 시각을 유지한다
        if old_g and g["status"] != "scheduled" and old_g.get("start_kst", "")[11:16] != "00:00":
            g["start_kst"] = old_g["start_kst"]
        merged[g["id"]] = g
    cutoff = (now - dt.timedelta(days=KEEP_DAYS)).isoformat(timespec="minutes")
    games = sorted((g for g in merged.values() if g["start_kst"] >= cutoff), key=lambda g: (g["start_kst"], g["id"]))
    league = {"checked_at": now.isoformat(timespec="minutes") if not error else old.get("leagues", {}).get("NPB", {}).get("checked_at", ""),
              "last_attempt_at": now.isoformat(timespec="minutes"),
              "coverage": "complete" if not error else "partial", "failed_dates": [],
              "games": games,
              # 지난 날짜에 확인한 '오늘 경기 없음'을 다음날에도 재사용하면 잘못된 안내가 된다.
              "no_games_today": (not bool(fresh)) if not error else False}
    if error:
        league["error"] = error
    text = json.dumps({"provider": "npb.jp 첫 화면 속보", "leagues": {"NPB": league}}, ensure_ascii=False, indent=2) + "\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
        OUT.write_text(text, encoding="utf-8")
        print(f"updated {OUT.name}: {len(games)} games")


if __name__ == "__main__":
    main()
