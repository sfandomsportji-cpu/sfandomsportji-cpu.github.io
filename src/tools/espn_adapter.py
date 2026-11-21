#!/usr/bin/env python3
"""Read-only ESPN summary normalizer for basketball, soccer and baseball.

No network, filesystem writes or publication operations. This deliberately does
NOT call an ESPN starter indicator an officially confirmed lineup and does
NOT treat an absent injury entry as availability.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

SPORT_LEAGUES = {
    "basketball": "nba",
    "soccer": "eng.1",  # caller may set a validated ESPN soccer competition code
    "baseball": "mlb",
}
SPORT_NAMES = frozenset(SPORT_LEAGUES)
TOKEN = re.compile(r"^[a-zA-Z0-9._-]{1,64}$")
EVENT_ID = re.compile(r"^[0-9]{1,24}$")
KST = ZoneInfo("Asia/Seoul")
UTC = timezone.utc
SOURCE = "ESPN_SITE_API_SECONDARY"


class ESPNAdapterError(ValueError):
    """Unsafe or incomplete ESPN payload: do not approve or publish."""


def summary_url(sport: str, event_id: str, league: str | None = None) -> str:
    """Build only a fixed-host ESPN summary URL, never accept arbitrary hosts."""
    if sport not in SPORT_NAMES:
        raise ESPNAdapterError("unsupported sport")
    league = league or SPORT_LEAGUES[sport]
    if not TOKEN.fullmatch(league) or not EVENT_ID.fullmatch(str(event_id)):
        raise ESPNAdapterError("unsafe league or ESPN event id")
    if sport != "soccer" and league != SPORT_LEAGUES[sport]:
        raise ESPNAdapterError("unexpected league for sport")
    return ("https://site.api.espn.com/apis/site/v2/sports/"
            f"{sport}/{league}/summary?{urlencode({'event': str(event_id)})}")


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ESPNAdapterError("timestamp missing")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ESPNAdapterError("invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ESPNAdapterError("offset required for ESPN timestamp")
    return dt.astimezone(UTC)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ESPNAdapterError(f"missing {label}")
    return value.strip()


def _id(value: object, label: str) -> str:
    result = str(value) if value is not None else ""
    if not EVENT_ID.fullmatch(result):
        raise ESPNAdapterError(f"missing/invalid {label}")
    return result


def _list(value: object, label: str) -> list:
    if not isinstance(value, list):
        raise ESPNAdapterError(f"invalid {label} list")
    return value


def _event(payload: dict, expected_event_id: str | None) -> tuple[str, dict]:
    if not isinstance(payload, dict):
        raise ESPNAdapterError("JSON root must be object")
    header = payload.get("header")
    if not isinstance(header, dict):
        raise ESPNAdapterError("summary header missing")
    comps = _list(header.get("competitions"), "header.competitions")
    if not comps or not isinstance(comps[0], dict):
        raise ESPNAdapterError("summary competition missing")
    comp = comps[0]
    event_id = _id(header.get("id"), "header.id")
    if _id(comp.get("id"), "competition.id") != event_id:
        raise ESPNAdapterError("competition id does not match event id")
    if expected_event_id is not None and event_id != _id(expected_event_id, "expected event id"):
        raise ESPNAdapterError("wrong game response")
    return event_id, comp


def _teams(competition: dict) -> tuple[list[dict], dict[str, str]]:
    raw = _list(competition.get("competitors"), "competitors")
    if len(raw) != 2:
        raise ESPNAdapterError("expected two competing teams")
    teams, ids, sides = [], set(), set()
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("team"), dict):
            raise ESPNAdapterError("missing competitor team")
        t = item["team"]
        team_id = _id(t.get("id"), "team.id")
        competitor_id = _id(item.get("id"), "competitor.id")
        side = item.get("homeAway")
        if team_id != competitor_id or team_id in ids or side not in ("home", "away") or side in sides:
            raise ESPNAdapterError("invalid/duplicate team id or side")
        ids.add(team_id)
        sides.add(side)
        teams.append({"team_id": team_id, "name": _text(t.get("displayName"), "team name"),
                      "abbreviation": t.get("abbreviation"), "home_away": side})
    return teams, {x["team_id"]: x["home_away"] for x in teams}


def _injuries(payload: dict, team_sides: dict[str, str], event_time: datetime,
              fetched_at: datetime) -> tuple[list[dict], bool]:
    """ESPN injuries may reflect today, even when summary is an old game."""
    if "injuries" not in payload:
        return [], False
    groups = _list(payload["injuries"], "injuries")
    result = []
    seen = set()
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("team"), dict):
            raise ESPNAdapterError("invalid injury group")
        team_id = _id(group["team"].get("id"), "injury team.id")
        if team_id not in team_sides:
            raise ESPNAdapterError("injury attached to a team outside this game")
        for row in _list(group.get("injuries"), "injuries[].injuries"):
            if not isinstance(row, dict) or not isinstance(row.get("athlete"), dict):
                raise ESPNAdapterError("invalid injury player")
            player_id = _id(row["athlete"].get("id"), "injury athlete.id")
            key = (team_id, player_id)
            if key in seen:
                raise ESPNAdapterError("duplicate injury player in same team")
            seen.add(key)
            updated = parse_timestamp(row["date"]) if row.get("date") else None
            if updated and updated > fetched_at + timedelta(minutes=2):
                raise ESPNAdapterError("injury timestamp is in the future")
            # Never project later updates backwards onto an older event.
            after_event = updated is not None and updated > event_time
            result.append({
                "team_id": team_id, "athlete_id": player_id,
                "athlete_name": _text(row["athlete"].get("displayName"), "injury athlete name"),
                "espn_status_raw": _text(row.get("status"), "ESPN injury status"),
                "source_updated_utc": updated.isoformat() if updated else None,
                "injury_type_raw": row.get("details", {}).get("type") if isinstance(row.get("details"), dict) else None,
                "espn_return_date_raw": row.get("details", {}).get("returnDate") if isinstance(row.get("details"), dict) else None,
                "applicability": "POST_EVENT_UPDATE" if after_event else "ESPN_REPORTED_NOT_OFFICIAL",
                "official_status_verified": False,
            })
    return result, True


def _roster_entries(payload: dict, sport: str, team_sides: dict[str, str]) -> tuple[list[dict], bool]:
    """ESPN starter=true is an observed ESPN flag, not a league announcement."""
    if "rosters" not in payload:
        return [], False
    groups = _list(payload["rosters"], "rosters")
    records = []
    seen = set()
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("team"), dict):
            raise ESPNAdapterError("invalid roster group")
        team_id = _id(group["team"].get("id"), "roster team id")
        if team_id not in team_sides or group.get("homeAway") != team_sides[team_id]:
            raise ESPNAdapterError("roster assigned to wrong game team")
        for row in _list(group.get("roster"), "rosters[].roster"):
            if not isinstance(row, dict) or not isinstance(row.get("athlete"), dict):
                raise ESPNAdapterError("invalid roster player")
            athlete_id = _id(row["athlete"].get("id"), "roster athlete id")
            key = team_id, athlete_id
            if key in seen:
                raise ESPNAdapterError("duplicate roster player")
            seen.add(key)
            starter = row.get("starter")
            if starter is not None and not isinstance(starter, bool):
                raise ESPNAdapterError("ESPN starter flag must be bool or absent")
            order = row.get("battingOrder")
            if order is not None and (isinstance(order, bool) or str(order) not in {str(i) for i in range(1, 10)}):
                raise ESPNAdapterError("invalid batting order")
            if order is not None and sport != "baseball":
                raise ESPNAdapterError("batting order in non-baseball payload")
            pos = row.get("position") if isinstance(row.get("position"), dict) else {}
            records.append({
                "team_id": team_id, "athlete_id": athlete_id,
                "athlete_name": _text(row["athlete"].get("displayName"), "roster athlete name"),
                "espn_starter_flag": starter,
                "espn_batting_order": int(order) if order is not None else None,
                "position_raw": pos.get("abbreviation"),
                "official_lineup_confirmed": False,
            })
    return records, True


def normalize_summary(sport: str, payload: dict, *, fetched_at: str,
                      expected_event_id: str | None = None, league: str | None = None) -> dict:
    """Normalize an ESPN summary response into a safe, auditable record.

    All lineup/injury claims remain unapproved. Absent data stays absent.
    No I/O; caller is responsible for collection, licensing and source archiving.
    """
    if sport not in SPORT_NAMES:
        raise ESPNAdapterError("unsupported sport")
    league = league or SPORT_LEAGUES[sport]
    if not TOKEN.fullmatch(league) or (sport != "soccer" and league != SPORT_LEAGUES[sport]):
        raise ESPNAdapterError("invalid sport/league combination")
    fetched = parse_timestamp(fetched_at)
    event_id, competition = _event(payload, expected_event_id)
    at_utc = parse_timestamp(competition.get("date"))
    teams, team_sides = _teams(competition)
    injuries, has_injuries_section = _injuries(payload, team_sides, at_utc, fetched)
    roster, has_rosters_section = _roster_entries(payload, sport, team_sides)
    warnings = ["ESPN is a secondary source; no league-confirmed lineup or injury claim"]
    if not has_injuries_section:
        warnings.append("NO_INJURY_SECTION: absence does not mean Available")
    if not has_rosters_section:
        warnings.append("NO_ROSTER_SECTION: lineup not available from this payload")
    if any(x["applicability"] == "POST_EVENT_UPDATE" for x in injuries):
        warnings.append("POST_EVENT_INJURY_UPDATES: cannot reconstruct historical pregame injury status")
    return {
        "sport": sport, "league": league, "provider": SOURCE,
        "event_id": event_id, "event_key": f"{sport}|espn|{league}|{event_id}",
        "event_at_utc": at_utc.isoformat(),
        "event_at_kst": at_utc.astimezone(KST).isoformat(),
        "date_kst": at_utc.astimezone(KST).date().isoformat(),
        "fetched_at_utc": fetched.isoformat(),
        "provider_event_status_raw": (competition.get("status") or {}).get("type", {}).get("name")
        if isinstance(competition.get("status"), dict) else None,
        "teams": teams, "injuries": injuries, "roster": roster,
        "injury_section_present": has_injuries_section,
        "roster_section_present": has_rosters_section,
        "official_lineup_confirmed": False,
        "publication_status": "NOT_APPROVED",
        "public_display_allowed": False,
        "warnings": warnings,
    }
