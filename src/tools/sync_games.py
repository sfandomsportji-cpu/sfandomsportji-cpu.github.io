#!/usr/bin/env python3
"""Refresh SFANDOM KST game snapshot from an external scoreboard.
This provider is a secondary source; scores are never inferred from kickoff time.
A failed request keeps previously verified data and records freshness clearly.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "content" / "games-snapshot.json"
KST = dt.timezone(dt.timedelta(hours=9))
SOURCES = {
    "MLB": "baseball/mlb",
    "NBA": "basketball/nba",
    "NFL": "football/nfl",
    "NHL": "hockey/nhl",
}
API_HOSTS = ("site.api.espn.com", "site.web.api.espn.com")
API = "https://{}/apis/site/v2/sports/{}/scoreboard?dates={}"
STATUS = {"pre": "scheduled", "in": "live", "post": "final"}
USER_AGENT = "SFANDOM-site-scoreboard/1.0 (https://sfandom.com/)"
# ESPN과 사이트가 다르게 쓰는 NBA 약자. 이 표가 없으면 해당 팀 경기는 영원히 '확인 중'에 머뭅니다.
NBA_CODE = {"NY": "NYK", "GS": "GSW", "NO": "NOP", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}


def read_previous() -> dict:
    try:
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"provider": "ESPN scoreboard", "updated_at": None, "leagues": {}}


def fetch_one(league: str, endpoint: str, date: dt.date) -> tuple[str, str, dict | None]:
    day = date.strftime("%Y%m%d")
    for host in API_HOSTS:
        request = urllib.request.Request(
            API.format(host, endpoint, day),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                body = response.read(2_500_001)
                if len(body) > 2_500_000:
                    raise ValueError("scoreboard response too large")
            value = json.loads(body)
            if not isinstance(value.get("events"), list):
                raise ValueError("scoreboard events list missing")
            return league, day, value
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            code = getattr(exc, "code", "unknown")
            print(f"[{league}] {day}: {host} error ({type(exc).__name__}, HTTP {code}); trying alternate")
    return league, day, None

def parse_event(league: str, event: dict) -> dict | None:
    try:
        event_id = str(event["id"])
        if not event_id.isdigit():
            return None
        start = dt.datetime.fromisoformat(str(event["date"]).replace("Z", "+00:00"))
        if start.tzinfo is None:
            return None
        start_kst = start.astimezone(KST)
        competition = event["competitions"][0]
        competitors = {c["homeAway"]: c for c in competition["competitors"]}
        away, home = competitors["away"], competitors["home"]
        away_code = str(away["team"]["abbreviation"]).upper().strip()
        home_code = str(home["team"]["abbreviation"]).upper().strip()
        if not (1 <= len(away_code) <= 5 and 1 <= len(home_code) <= 5):
            return None
        state = event.get("status", {}).get("type", {})
        name = str(state.get("name", "")).upper()
        if "POSTPONED" in name:
            status = "postponed"
        elif "CANCELED" in name or "CANCELLED" in name:
            status = "cancelled"
        else:
            status = STATUS.get(state.get("state"), "unconfirmed")
        if status == "unconfirmed":
            return None
        away_score = home_score = None
        if status in ("live", "final"):
            av, hv = away.get("score"), home.get("score")
            if av is None or hv is None:
                return None
            away_score, home_score = int(av), int(hv)
            if not (0 <= away_score <= 300 and 0 <= home_score <= 300):
                return None
        links = event.get("links") or []
        url = next((str(x.get("href", "")) for x in links
                    if str(x.get("href", "")).startswith("https://www.espn.com/")), "")
        return {
            "id": f"{league}-{event_id}",
            "league": league,
            "start_kst": start_kst.isoformat(timespec="minutes"),
            "away": away_code,
            "home": home_code,
            "away_name": str(away["team"].get("displayName", away_code))[:90],
            "home_name": str(home["team"].get("displayName", home_code))[:90],
            "status": status,
            "away_score": away_score,
            "home_score": home_score,
            "source_url": url,
        }
    except (KeyError, TypeError, ValueError, IndexError, OverflowError):
        return None


def add_new_preseason_cards(data: dict, rows: list) -> bool:
    """개막 전까지, ESPN이 확인한 새 프리시즌 경기를 카드 목록에 추가합니다(지난 경기·다른 날짜 중복은 넣지 않음)."""
    try:
        opening = dt.datetime.fromisoformat(data["opening_kst"]).date()
    except (KeyError, TypeError, ValueError):
        return False
    if data.get("home_mode") != "preseason":
        return False
    logos = ROOT.parent / "assets" / "teams" / "nba"
    weekdays = "월화수목금토일"
    cards = data.setdefault("preseason_games", [])
    added = False
    for e in rows:
        try:
            d = dt.datetime.fromisoformat(e["start_kst"])
        except (KeyError, TypeError, ValueError):
            continue
        away, home = e.get("away"), e.get("home")
        if d.date() >= opening or e.get("status") not in ("scheduled", "live", "final"):
            continue
        if not ((logos / f"{str(away).lower()}.svg").exists() and (logos / f"{str(home).lower()}.svg").exists()):
            continue  # NBA 팀끼리의 경기만(해외 구단 등은 제외)
        near = any(g.get("away") == away and g.get("home") == home
                   and abs((dt.date(2026, *map(int, g["kst"].split(" ")[0].split("."))) - d.date()).days) <= 1
                   for g in cards if re_kst_ok(g))
        if near:
            continue
        card = {"day": "PRESEASON", "away": away, "home": home,
                "kst": f"{d.month}.{d.day} ({weekdays[d.weekday()]}) {d:%H:%M}", "tv": "KST"}
        if e["status"] == "final" and isinstance(e.get("away_score"), int) and isinstance(e.get("home_score"), int):
            av, hv = e["away_score"], e["home_score"]
            card.update({"day": "FINAL", "away_score": av, "home_score": hv,
                         "result": f"{away} {av}–{hv} {home}", "tag": f"종료 · {away} {av}–{hv} {home}"})
        elif e["status"] == "live":
            card.update({"day": "LIVE", "tag": "진행 중 · 기록 제공처 확인 시각 기준"})
        cards.append(card)
        added = True
    return added


def re_kst_ok(card: dict) -> bool:
    import re
    return bool(re.match(r"\d{1,2}\.\d{1,2} ", str(card.get("kst", ""))))


def refresh_nba_cards(snapshot: dict, now: dt.datetime) -> None:
    """Update legacy NBA preseason cards only from confirmed ESPN event status.
    Keep previews and historical results when no matching verified record is available.
    """
    import re

    card_file = ROOT / "content" / "nba-2026.json"
    try:
        original = card_file.read_text(encoding="utf-8")
        data = json.loads(original)
    except (OSError, ValueError):
        return
    rows = [dict(e, away=NBA_CODE.get(e.get("away"), e.get("away")), home=NBA_CODE.get(e.get("home"), e.get("home")))
            for e in ((snapshot.get("leagues", {}).get("NBA") or {}).get("games") or [])]
    # 공개 스냅샷은 최근 경기만 담으므로, 카드에 남은 '확인 중' 경기는 지난 날짜를 따로 조회해 풀어 줍니다.
    # 이 조회 결과는 카드 갱신에만 쓰고 스냅샷에는 넣지 않습니다.
    older = []
    for back in (2, 3, 4):
        _lg, _day, payload = fetch_one("NBA", SOURCES["NBA"], now.date() - dt.timedelta(days=back))
        for ev in (payload or {}).get("events", []):
            parsed = parse_event("NBA", ev)
            if parsed:
                older.append(dict(parsed, away=NBA_CODE.get(parsed["away"], parsed["away"]),
                                  home=NBA_CODE.get(parsed["home"], parsed["home"])))
    verified = {}
    for e in older + rows:
        try:
            d = dt.datetime.fromisoformat(e["start_kst"])
            verified[(e["away"], e["home"], d.month, d.day)] = e
        except (KeyError, TypeError, ValueError):
            continue
    changed = False
    for g in data.get("preseason_games", []):
        m = re.match(r"(\d{1,2})\.(\d{1,2}).*?(\d{2}):(\d{2})", g.get("kst", ""))
        if not m:
            continue
        month, day, hour, minute = (int(x) for x in m.groups())
        e = verified.get((g.get("away"), g.get("home"), month, day))
        try:
            start = dt.datetime(2026, month, day, hour, minute, tzinfo=KST)
        except ValueError:
            continue
        if e and e.get("status") == "final":
            av, hv = e.get("away_score"), e.get("home_score")
            if not isinstance(av, int) or not isinstance(hv, int):
                continue
            updated = {"day": "FINAL", "away_score": av, "home_score": hv,
                       "result": f'{g["away"]} {av}–{hv} {g["home"]}',
                       "tag": f'종료 · {g["away"]} {av}–{hv} {g["home"]}'}
        elif e and e.get("status") == "live":
            updated = {"day": "LIVE", "tag": "진행 중 · 기록 제공처 확인 시각 기준"}
        elif e and e.get("status") in ("postponed", "cancelled"):
            updated = {"day": "DELAYED", "tag": "연기" if e["status"] == "postponed" else "취소"}
        elif start < now - dt.timedelta(minutes=25) and not g.get("result"):
            updated = {"day": "CHECKING", "tag": "경기 상태 확인 중"}
        else:
            continue
        for key, value in updated.items():
            if g.get(key) != value:
                g[key] = value
                changed = True
        if e and e.get("status") != "final" and "result" in g:
            g.pop("result")
            changed = True
    if add_new_preseason_cards(data, rows):
        changed = True
    if changed:
        card_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
        print("[NBA] legacy hub cards reconciled with confirmed game states")


def refresh() -> None:
    now = dt.datetime.now(KST)
    prior = read_previous()
    days = [now.date() + dt.timedelta(days=d) for d in (-1, 0, 1, 2)]
    jobs = [(lg, endpoint, day) for lg, endpoint in SOURCES.items() for day in days]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        answers = list(pool.map(lambda j: fetch_one(*j), jobs))

    grouped: dict[str, list] = {lg: [] for lg in SOURCES}
    for league, date, payload in answers:
        grouped[league].append((date, payload))

    updated = {"provider": "ESPN scoreboard (secondary)",
               "updated_at": now.isoformat(timespec="minutes"), "leagues": {}}
    successful = 0
    for league in SOURCES:
        rows = grouped[league]
        good = [d for d, value in rows if value is not None]
        failed = [d for d, value in rows if value is None]
        old = (prior.get("leagues") or {}).get(league, {})
        if not good:
            updated["leagues"][league] = {
                **old, "error": "자료 제공처 연결 실패 · 마지막 확인 정보",
            }
            continue
        ids = {}
        for _day, payload in rows:
            if payload is None:
                continue
            for e in payload.get("events", []):
                parsed = parse_event(league, e)
                if parsed:
                    ids[parsed["id"]] = parsed
        # Limit public cards to a recent window. Do not turn elapsed fixtures into finals.
        lower = now - dt.timedelta(hours=36)
        upper = now + dt.timedelta(hours=66)
        events = [g for g in ids.values()
                  if lower <= dt.datetime.fromisoformat(g["start_kst"]) <= upper]
        events.sort(key=lambda g: (g["start_kst"], g["id"]))
        # An incomplete date fetch is not allowed to erase previously verified events.
        if failed and old.get("games"):
            for prev in old["games"]:
                if prev.get("id") not in ids and prev.get("start_kst"):
                    try:
                        when = dt.datetime.fromisoformat(prev["start_kst"])
                        if lower <= when <= upper:
                            events.append(prev)
                    except ValueError:
                        pass
            events.sort(key=lambda g: (g["start_kst"], g["id"]))
        updated["leagues"][league] = {
            "checked_at": now.isoformat(timespec="minutes"),
            "coverage": "partial" if failed else "complete",
            "failed_dates": failed,
            "games": events[:55],
        }
        successful += 1
        print(f"[{league}] {len(events)} games; failed dates: {len(failed)}")
    if not successful:
        print("No fresh provider data. Keeping previous snapshot and failing gracefully.")
        return
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    draft = SNAPSHOT.with_suffix(".json.tmp")
    draft.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    draft.replace(SNAPSHOT)
    refresh_nba_cards(updated, now)


if __name__ == "__main__":
    refresh()
