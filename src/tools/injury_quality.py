#!/usr/bin/env python3
"""NBA report audit gates. Pure checks; never publish or fetch external data.

A valid-looking subset is not necessarily a complete NBA injury report.
Flag suspicious drops within the same official report date instead of claiming
that missing players are suddenly available.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
import re

STATUSES = {"Out", "Available", "Probable", "Questionable", "Doubtful"}
GAME = re.compile(r"^[A-Z]{2,3}@[A-Z]{2,3}$")


class DataQualityError(ValueError):
    """Fail closed: incoming data requires a manual re-check."""


def validate_rows(players: dict) -> dict:
    """Structural/semantic checks independent from the PDF layout parser."""
    if not isinstance(players, dict) or not players:
        raise DataQualityError("empty injury table")
    keys_seen = set()
    groups = Counter()
    for key, row in players.items():
        if not isinstance(row, dict):
            raise DataQualityError("unexpected player row")
        try:
            game_date, matchup, team, player = (row[name] for name in
                ("game_date", "matchup", "team", "player"))
            status = row["official_status"]
            state = row["state"]
        except KeyError as exc:
            raise DataQualityError("missing required player field") from exc
        if not all(isinstance(x, str) and x.strip() for x in
                   (key, game_date, matchup, team, player, status, state)):
            raise DataQualityError("empty player identity or status")
        try:
            date.fromisoformat(game_date)
        except ValueError as exc:
            raise DataQualityError("invalid game date") from exc
        if not GAME.fullmatch(matchup) or "," not in player or len(team) < 3:
            raise DataQualityError("ambiguous game/team/player identity")
        if status not in STATUSES:
            raise DataQualityError("unrecognized injury status")
        if row.get("lineup") != "not_verified":
            raise DataQualityError("injury status must not assert a starting lineup")
        expected_key = "|".join((game_date, matchup, team, player))
        if key != expected_key or key in keys_seen:
            raise DataQualityError("player key does not match source identity")
        keys_seen.add(key)
        groups[(game_date, matchup, team)] += 1
    return {"rows": len(players), "game_team_groups": len(groups)}


def coverage_alerts(previous: dict, players: dict, report_at_et: str) -> list[str]:
    """Conservative within-day anomaly detection. No auto publish if flagged.

    A new reporting day is not compared to the previous day's list; player
    absences do NOT prove availability in either case.
    """
    if not isinstance(previous, dict) or not previous.get("players"):
        return []
    old_report_at = previous.get("report_at_et")
    if not old_report_at:
        return []
    try:
        same_day = datetime.fromisoformat(old_report_at).date() == (
            datetime.fromisoformat(report_at_et).date()
        )
    except (TypeError, ValueError):
        raise DataQualityError("cannot compare previous report timestamps")
    if not same_day:
        return []
    old_counts = Counter()
    new_counts = Counter()
    for item in previous["players"].values():
        if isinstance(item, dict):
            old_counts[(item.get("game_date"), item.get("matchup"), item.get("team"))] += 1
    for item in players.values():
        new_counts[(item["game_date"], item["matchup"], item["team"])] += 1
    alerts = []
    for group, before in old_counts.items():
        after = new_counts[group]
        if before >= 4 and after * 2 < before:
            alerts.append(f"sharp row drop: {group[0]} {group[1]} {group[2]} ({before}->{after})")
    return alerts


def validate_snapshot(previous: dict, players: dict, report_at_et: str) -> dict:
    metrics = validate_rows(players)
    alerts = coverage_alerts(previous, players, report_at_et)
    if alerts:
        raise DataQualityError("; ".join(alerts[:5]))
    return {"state": "PASSED", **metrics, "coverage_alerts": []}
