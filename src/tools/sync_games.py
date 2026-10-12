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
    rows = (snapshot.get("leagues", {}).get("NBA") or {}).get("games") or []
    verified = {}
    for e in rows:
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
