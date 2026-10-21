#!/usr/bin/env python3
"""games-snapshot.json(ESPN 확인값)으로 손으로 고치던 값을 자동 반영합니다.

- postseason-2026.json: 챔피언십시리즈 경기 결과 · 시리즈 전적 · 다음 경기 시간
- nba-2026.json: 프리시즌 종료 경기의 점수, 확인 시각 문구
- site.json: 홈 첫 화면(hero) 문구 (hero.auto 가 true 일 때만)

원칙: 종료(final)로 확인된 경기만 결과로 적고, 시간만 지난 경기는 결과로 추정하지 않습니다.
스냅샷에 없는 경기는 건드리지 않으며, 바꿀 내용이 없으면 파일을 다시 쓰지 않습니다.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
SNAPSHOT = CONTENT / "games-snapshot.json"
POST = CONTENT / "postseason-2026.json"
NBA = CONTENT / "nba-2026.json"
SITE = ROOT / "site.json"
KST = dt.timezone(dt.timedelta(hours=9))
DAYS = "월화수목금토일"
NBA_CODE = {"NY": "NYK", "GS": "GSW", "NO": "NOP", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}
LEAGUE_NAME = {"NL": "NLCS", "AL": "ALCS"}


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_if_changed(path: pathlib.Path, data) -> bool:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    print(f"updated {path.relative_to(ROOT)}")
    return True


def when(g: dict) -> dt.datetime:
    return dt.datetime.fromisoformat(g["start_kst"]).astimezone(KST)


def kst_label(t: dt.datetime) -> str:
    return f"{t.month}.{t.day} ({DAYS[t.weekday()]}) {t:%H:%M}"


def checked_label(stamp: str) -> str:
    t = dt.datetime.fromisoformat(stamp).astimezone(KST)
    return f"{t.year}년 {t.month}월 {t.day}일 {t:%H:%M} KST"


def result_text(g: dict) -> str:
    a, h = int(g["away_score"]), int(g["home_score"])
    return f"{g['away']} {a}–{h} {g['home']}" if a > h else f"{g['home']} {h}–{a} {g['away']}"


def is_final(g: dict) -> bool:
    return g.get("status") == "final" and g.get("away_score") is not None and g.get("home_score") is not None


# ── 챔피언십시리즈 ─────────────────────────────────────────────
def sync_lcs(snap: dict) -> list[dict]:
    data = load(POST)
    mlb = (snap.get("leagues", {}).get("MLB") or {}).get("games", [])
    now = dt.datetime.now(KST)
    summary = []
    for series in data.get("lcs", []):
        pair = {series["home"], series["away"]}
        games = sorted((g for g in mlb if {g.get("away"), g.get("home")} == pair), key=when)
        done = [e for e in series["games"] if e.get("result")]
        for g in games:
            if not is_final(g):
                continue
            text, t = result_text(g), when(g)
            day = f"{t.month}.{t.day} "
            if any(e.get("id") == g["id"] or (e["result"] == text and e["kst"].startswith(day)) for e in done):
                continue
            if max(sum(e["result"].split()[0] == s for e in done) for s in pair) >= 4:
                break
            done.append({"g": len(done) + 1, "kst": kst_label(t), "result": text, "id": g["id"]})
        hw = sum(e["result"].split()[0] == series["home"] for e in done)
        aw = len(done) - hw
        entries = list(done)
        if max(hw, aw) < 4:
            upcoming = [g for g in games if g.get("status") in ("scheduled", "live") and when(g) >= now - dt.timedelta(hours=6)]
            if upcoming:
                entries.append({"g": len(done) + 1, "kst": kst_label(when(upcoming[0]))})
            else:
                old = [e for e in series["games"] if not e.get("result")]
                if old:
                    entries.append({**old[0], "g": len(done) + 1})
        series["games"], series["hw"], series["aw"] = entries, hw, aw
        summary.append(series)
    checked = (snap.get("leagues", {}).get("MLB") or {}).get("checked_at")
    if checked:
        data["updated"] = dt.datetime.fromisoformat(checked).astimezone(KST).strftime("%Y-%m-%d")
    save_if_changed(POST, data)
    return summary


# ── 홈 첫 화면 ─────────────────────────────────────────────────
def _order(e: dict) -> tuple:
    month, day = e["kst"].split()[0].split(".")
    return int(month), int(day), e["kst"].split()[-1]


def hero_for(series: list[dict]) -> dict | None:
    last = None
    for s in series:
        finals = [e for e in s["games"] if e.get("result")]
        if finals and (last is None or _order(finals[-1]) > _order(last[1])):
            last = (s, finals[-1])
    if not last:
        return None
    s, e = last
    name = LEAGUE_NAME.get(s["league"], "LCS")
    kr = {s["home"]: s["home_kr"], s["away"]: s["away_kr"]}
    winner = e["result"].split()[0]
    score = e["result"].split()[1]
    wl = e["result"].split()
    said = f"{kr[wl[0]]} {score} {kr[wl[2]]}"
    lead_code = s["home"] if s["hw"] >= s["aw"] else s["away"]
    lead, trail = max(s["hw"], s["aw"]), min(s["hw"], s["aw"])
    status = f"시리즈 {s['hw']}–{s['aw']} 동률" if lead == trail else f"시리즈 {lead}–{trail} {kr[lead_code]} 리드"
    nxt = next((x for x in s["games"] if not x.get("result")), None)
    if lead >= 4:
        return {"badge_en": f"MLB · {name} FINAL", "badge_kr": f"{name} 우승 · 시리즈 {lead}–{trail}",
                "art": f"{name} · FINAL", "title": f"{kr[lead_code]}, 월드시리즈 진출\n{name} {lead}–{trail}",
                "text": f"{name} 최종 전적 {lead}승 {trail}패, {kr[lead_code]} 월드시리즈 진출. 마지막 경기 결과는 {said}입니다."}
    if trail == 0 and lead >= 2 and winner == lead_code:
        title = f"{kr[winner]}, {name} {lead}연승\n시리즈 {lead}–0 리드"
    else:
        title = f"{kr[winner]}, {name} {e['g']}차전 승리\n{status}"
    tail = f" 다음 {nxt['g']}차전은 한국시간 {nxt['kst']}에 열립니다." if nxt else ""
    return {"badge_en": f"MLB · {name} GAME {e['g']} FINAL",
            "badge_kr": f"{name} {e['g']}차전 결과 · 경기 {score} / {status}",
            "art": f"{name} · FINAL", "title": title,
            "text": f"{name} {e['g']}차전 경기 결과는 {said}, {status.replace('시리즈 ', '시리즈 전적은 ', 1)}입니다.{tail}"}


def sync_hero(series: list[dict]) -> None:
    site = load(SITE)
    hero = site.get("hero", {})
    if not hero.get("auto"):
        return
    new = hero_for(series)
    if new:
        hero.update(new)
        save_if_changed(SITE, site)


# ── NBA 프리시즌 ───────────────────────────────────────────────
def sync_nba(snap: dict) -> None:
    league = snap.get("leagues", {}).get("NBA") or {}
    if not league.get("games"):
        return
    data = load(NBA)
    index = {}
    for g in league["games"]:
        if is_final(g):
            index[(NBA_CODE.get(g["away"], g["away"]), NBA_CODE.get(g["home"], g["home"]), when(g).strftime("%m.%d"))] = g
    for row in data.get("preseason_games", []):
        if row.get("result"):
            continue
        month, day = row["kst"].split()[0].split(".")
        g = index.get((row["away"], row["home"], f"{int(month):02d}.{int(day):02d}"))
        if g:
            a, h = int(g["away_score"]), int(g["home_score"])
            text = f"{row['away']} {a}–{h} {row['home']}"
            row.update({"day": "FINAL", "tag": f"종료 · {text}", "result": text, "away_score": a, "home_score": h})
    # 정규시즌 개막 주간 카드: 종료 경기만 점수를 붙이고 day(OPENING NIGHT 등)·기존 태그는 유지
    for row in data.get("games", []):
        if row.get("result"):
            continue
        month, day = row["kst"].split()[0].split(".")
        g = index.get((row["away"], row["home"], f"{int(month):02d}.{int(day):02d}"))
        if g:
            a, h = int(g["away_score"]), int(g["home_score"])
            text = f"{row['away']} {a}–{h} {row['home']}"
            tag = f"종료 · {text}" + (f" · {row['tag']}" if row.get("tag") else "")
            row.update({"tag": tag, "result": text, "away_score": a, "home_score": h})
    if league.get("checked_at") and league.get("coverage") == "complete":
        finals = sum(1 for r in data.get("preseason_games", []) if r.get("result"))
        data["preseason_note"] = (f"{checked_label(league['checked_at'])} 확인: 프리시즌 종료 {finals}경기 반영. "
                                  "최종 결과는 ESPN 스코어보드 기준이며, 예정 경기는 경기 전 상태 유지. 경기 시간은 한국시간(KST).")
    save_if_changed(NBA, data)


def main() -> None:
    snap = load(SNAPSHOT)
    series = sync_lcs(snap)
    sync_hero(series)
    sync_nba(snap)


if __name__ == "__main__":
    main()
