#!/usr/bin/env python3
"""Independent NBA safe mode. Only Python standard library; NEVER publishes.

Runs even when the PDF parser, sports_clock or other project imports break.
A previous snapshot is kept solely for audit and is always marked stale.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile

KST = timezone(timedelta(hours=9), name="KST")
MESSAGE = "현재 출전 정보를 확인하지 못했어요."


def fallback(previous: dict, now: datetime) -> dict:
    """Produce a fail-closed, visibly stale audit record."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("safe-mode clock must be timezone-aware")
    previous = previous if isinstance(previous, dict) else {}
    prior_players = previous.get("players")
    if not isinstance(prior_players, dict):
        prior_players = {}
    return {
        "league": "NBA",
        "source": "last-known official NBA report (audit only)",
        "publication_status": "NOT_APPROVED",
        "freshness": "STALE",
        "public_display_allowed": False,
        "review_required": True,
        "message_ko": MESSAGE,
        "checked_at_utc": now.astimezone(timezone.utc).isoformat(),
        "checked_at_kst": now.astimezone(KST).isoformat(),
        "players": prior_players,
        "previous_source_url": previous.get("source_url"),
        "previous_checked_at_utc": previous.get("checked_at_utc"),
        "previous_report_at_utc": previous.get("report_at_utc"),
    }


def write_json_atomic(path: str | Path, value: dict) -> None:
    """Never leave a partially written JSON file behind."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=path.name + ".", suffix=".tmp", delete=False
        ) as handle:
            tmp_name = handle.name
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.unlink(tmp_name)


def load_previous(path: str | Path) -> tuple[dict, str | None]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return {}, "INVALID_PREVIOUS_TYPE"
        return value, None
    except FileNotFoundError:
        return {}, "NO_PREVIOUS_DATA"
    except (ValueError, OSError, UnicodeError):
        return {}, "CORRUPTED_PREVIOUS_DATA"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", default=".monitor/previous.json")
    parser.add_argument("--output", default=".monitor/current.json")
    parser.add_argument("--incident", default=".monitor/incident.json")
    args = parser.parse_args(argv)
    previous, previous_error = load_previous(args.previous)
    now = datetime.now(timezone.utc)
    data = fallback(previous, now)
    incident = {
        "at_utc": now.isoformat(),
        "status": "STALE",
        "level": 3,
        "previous_error": previous_error,
        "message_ko": MESSAGE,
        "publish": False,
    }
    write_json_atomic(args.output, data)
    write_json_atomic(args.incident, incident)
    print("THIRD_LEVEL_FAILOVER: STALE / NOT_APPROVED / NO_PUBLISH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
