#!/usr/bin/env python3
"""Off-workflow GitHub Actions heartbeat checker (read-only).

Run this on a DIFFERENT scheduler/host from the monitored NBA workflow.
No publishing, no mutations. The run ledger is an external heartbeat proxy;
it does not by itself establish the accuracy of the NBA injury PDF data.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import quote
from pathlib import Path

DEFAULT_REPO = "sfandomsportji-cpu/sfandomsportji-cpu.github.io"
DEFAULT_WORKFLOW = "nba-injury-watch.yml"
REPO_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{1,100}/[a-zA-Z0-9_.-]{1,100}$")
WORKFLOW_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+\.yml$")
MAX_GAP_MINUTES = 22


def utc_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("GitHub event timestamp missing")
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("GitHub event timestamp lacks offset")
    return d.astimezone(timezone.utc)


def classify(runs: list, *, now: datetime, max_gap_minutes=MAX_GAP_MINUTES) -> dict:
    """Check latest scheduled run AND last successful verification independently."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("external clock requires timezone")
    now = now.astimezone(timezone.utc)
    if not isinstance(runs, list):
        return {"state": "INVALID_RESPONSE", "ok": False}
    candidates = [r for r in runs if isinstance(r, dict) and r.get("event") == "schedule"
                  and r.get("head_branch") == "main"]
    if not candidates:
        return {"state": "NO_SCHEDULE_RUNS", "ok": False,
                "note": "Treat as NOT_ARMED until workflow merged to default branch."}
    try:
        ordered = sorted(candidates, key=lambda r: utc_timestamp(r["created_at"]), reverse=True)
        latest = ordered[0]
        recent_success = next((r for r in ordered if r.get("status") == "completed"
                               and r.get("conclusion") == "success"), None)
        newest_at = utc_timestamp(latest["created_at"])
        latest_age = (now - newest_at).total_seconds() / 60
        success_age = ((now - utc_timestamp(recent_success["created_at"])).total_seconds() / 60
                       if recent_success else None)
        result = {
            "last_run_id": latest.get("id"),
            "last_run_created_utc": newest_at.isoformat(),
            "last_run_age_minutes": round(latest_age, 2),
            "last_run_status": latest.get("status"),
            "last_run_conclusion": latest.get("conclusion"),
            "last_success_age_minutes": round(success_age, 2)
            if success_age is not None else None,
            "max_gap_minutes": max_gap_minutes,
        }
        if latest_age < -2:
            return {"state": "FUTURE_RUN_TIME", "ok": False, **result}
        if latest_age > max_gap_minutes:
            return {"state": "SCHEDULE_SILENT", "ok": False, **result}
        if latest.get("status") == "completed" and latest.get("conclusion") != "success":
            return {"state": "LATEST_FAILED", "ok": False, **result}
        if success_age is None or success_age > max_gap_minutes:
            return {"state": "NO_RECENT_VERIFIED_RUN", "ok": False, **result}
        if latest.get("status") in ("in_progress", "queued", "waiting", "pending"):
            return {"state": "PENDING_WITH_RECENT_SUCCESS", "ok": True, **result}
        if latest.get("conclusion") == "success":
            return {"state": "OK", "ok": True, **result}
        return {"state": "UNKNOWN_RUN_STATUS", "ok": False, **result}
    except (KeyError, TypeError, ValueError) as exc:
        return {"state": "INVALID_RESPONSE", "ok": False, "error_type": type(exc).__name__}


def get_runs(repo: str, workflow: str, *, token: str | None = None) -> list:
    if not REPO_PATTERN.fullmatch(repo) or not WORKFLOW_PATTERN.fullmatch(workflow):
        raise ValueError("invalid GitHub repository/workflow parameter")
    url = (f"https://api.github.com/repos/{repo}/actions/workflows/{quote(workflow)}/runs"
           "?branch=main&event=schedule&per_page=100")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SFANDOM-independent-watchdog/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as response:
        payload = json.loads(response.read(1_500_000))
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise ValueError("GitHub run response invalid")
    return payload["workflow_runs"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=DEFAULT_REPO)
    p.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    p.add_argument("--fixture", type=Path, help="offline JSON from GitHub runs API")
    p.add_argument("--max-gap-minutes", type=float, default=MAX_GAP_MINUTES)
    args = p.parse_args(argv)
    if not 0 < args.max_gap_minutes <= 1440:
        p.error("--max-gap-minutes must be in (0, 1440]")
    try:
        if args.fixture:
            data = json.loads(args.fixture.read_text(encoding="utf-8"))
            runs = data.get("workflow_runs") if isinstance(data, dict) else data
        else:
            runs = get_runs(args.repo, args.workflow, token=os.getenv("GH_TOKEN"))
        result = classify(runs, now=datetime.now(timezone.utc),
                          max_gap_minutes=args.max_gap_minutes)
    except Exception as exc:
        result = {"state": "CHECKER_FAILED", "ok": False,
                  "error_type": type(exc).__name__}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
