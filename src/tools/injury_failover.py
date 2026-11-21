#!/usr/bin/env python3
"""Third-line fallback: preserve a last-known snapshot, never mark it fresh."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from sports_clock import KST, parse_aware


def fallback(previous, now):
    report = {
        "league": "NBA",
        "source": "last-known official NBA report",
        "publication_status": "NOT_APPROVED",
        "freshness": "STALE",
        "public_display_allowed": False,
        "message_ko": "현재 출전 정보를 확인하지 못했어요.",
        "checked_at_utc": now.isoformat(),
        "checked_at_kst": now.astimezone(KST).isoformat(),
        "players": {},
        "previous_source_url": None,
        "previous_checked_at_utc": None,
    }
    if previous and previous.get("players"):
        report["players"] = previous["players"]  # audit only, not public
        report["previous_source_url"] = previous.get("source_url")
        report["previous_checked_at_utc"] = previous.get("checked_at_utc")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--previous", default=".monitor/previous.json")
    ap.add_argument("--output", default=".monitor/current.json")
    ap.add_argument("--incident", default=".monitor/incident.json")
    args = ap.parse_args()
    previous = {}
    p = Path(args.previous)
    if p.is_file():
        try:
            previous = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass  # fail closed; no prior state
    now = datetime.now(timezone.utc)
    result = fallback(previous, now)
    for name, payload in ((args.output, result),
                          (args.incident, {
                              "at_utc": now.isoformat(),
                              "status": "STALE",
                              "level": 3,
                              "message_ko": result["message_ko"],
                              "publish": False,
                          })):
        output = Path(name)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print("THIRD_LEVEL_FAILOVER: STALE/NO_PUBLISH")


if __name__ == "__main__":
    main()
