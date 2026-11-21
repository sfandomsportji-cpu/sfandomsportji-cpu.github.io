#!/usr/bin/env python3
"""Heartbeat watchdog. Standard library only; run it from somewhere OTHER than
the monitored workflow (another repo/service), otherwise it stops with it.

Heartbeat file: {"at_utc": "<ISO with offset>"} written after each healthy run.
Exit 0 only when OK. Any other state exits non-zero so the external runner alerts.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MAX_GAP = 22.0   # minutes; must match recovery_policy.MAX_GAP_MINUTES
CLOCK_SKEW_TOLERANCE = 2.0


def check(heartbeat_at_utc, now, max_gap=DEFAULT_MAX_GAP):
    """Return (state, gap_minutes). Never raises."""
    try:
        if heartbeat_at_utc is None:
            return "MISSING", None
        parsed = datetime.fromisoformat(str(heartbeat_at_utc).replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return "INVALID", None
        gap = (now.astimezone(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 60
        if gap < -CLOCK_SKEW_TOLERANCE:
            return "FUTURE", round(gap, 1)
        if gap > max_gap:
            return "LATE", round(gap, 1)
        return "OK", round(gap, 1)
    except Exception:
        return "INVALID", None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--heartbeat", default=".monitor/heartbeat.json")
    ap.add_argument("--max-gap-minutes", type=float, default=DEFAULT_MAX_GAP)
    args = ap.parse_args(argv)
    heartbeat = None
    try:
        heartbeat = json.loads(Path(args.heartbeat).read_text(encoding="utf-8")).get("at_utc")
    except Exception:
        pass
    state, gap = check(heartbeat, datetime.now(timezone.utc), args.max_gap_minutes)
    print(f"WATCHDOG: {state} gap_minutes={gap}")
    if state != "OK":
        print(f"::error::NBA monitor heartbeat {state}; treat player status as unconfirmed.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
