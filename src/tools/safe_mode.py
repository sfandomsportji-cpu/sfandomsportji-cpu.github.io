#!/usr/bin/env python3
"""Independent last-resort safe mode for the NBA injury audit pipeline.

Design rules (see docs/PR30-COLLABORATIVE-REVIEW.md):
- Standard library only. Never import sports_clock or the collector, so a bug
  there cannot disable the safety net.
- UTC arithmetic only. KST is a display concern and stays out of this module.
- Never raises from main(): any internal error still yields a blocked status.
- Never publishes. Output always has public_display_allowed=False and no
  player-level status; only the audit snapshot (kept sealed elsewhere) does.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TTL_MINUTES = 90
MESSAGE_KO = "현재 출전 정보를 확인하지 못했어요."


def parse_utc(value):
    """Parse an ISO timestamp into aware UTC. Naive or invalid -> ValueError."""
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp has no UTC offset")
    return parsed.astimezone(timezone.utc)


def digest(snapshot):
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def seal(snapshot, path):
    """Store a verified snapshot with its hash (last-known-good copy)."""
    atomic_write(path, {"sha256": digest(snapshot), "snapshot": snapshot})


def load_sealed(path):
    """Return the sealed snapshot, or None if missing, corrupt or tampered."""
    try:
        sealed = json.loads(Path(path).read_text(encoding="utf-8"))
        snapshot = sealed["snapshot"]
        if sealed["sha256"] != digest(snapshot):
            return None
        parse_utc(snapshot["checked_at_utc"])
        return snapshot
    except Exception:
        return None


def blocked_status(now, reason, last_checked_utc=None, age_minutes=None):
    return {
        "league": "NBA",
        "mode": "SAFE_MODE",
        "publication_status": "NOT_APPROVED",
        "public_display_allowed": False,
        "player_status": "확인 불가",
        "lineup": "unconfirmed",
        "message_ko": MESSAGE_KO,
        "reason": reason,
        "evaluated_at_utc": now.astimezone(timezone.utc).isoformat(),
        "last_verified_at_utc": last_checked_utc,
        "last_verified_age_minutes": age_minutes,
        "requires_operator_approval_to_resume": True,
    }


def evaluate(lkg, now, ttl_minutes=DEFAULT_TTL_MINUTES):
    """Status for display layers. Player-level data is never included."""
    if lkg is None:
        return blocked_status(now, "no_valid_last_known_good")
    try:
        checked = parse_utc(lkg["checked_at_utc"])
    except Exception:
        return blocked_status(now, "last_known_good_timestamp_invalid")
    age = (now.astimezone(timezone.utc) - checked).total_seconds() / 60
    if age < 0:
        return blocked_status(now, "clock_reversal", checked.isoformat(), round(age, 1))
    if age > ttl_minutes:
        return blocked_status(now, "last_known_good_expired",
                              checked.isoformat(), round(age, 1))
    # Within TTL the snapshot is only an audit aid: still not public, not approved.
    status = blocked_status(now, "within_ttl_audit_only", checked.isoformat(), round(age, 1))
    status["mode"] = "AUDIT_ONLY"
    return status


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lkg", default=".monitor/last_known_good.sealed.json")
    ap.add_argument("--output", default=".monitor/safe_status.json")
    ap.add_argument("--ttl-minutes", type=int, default=DEFAULT_TTL_MINUTES)
    args = ap.parse_args(argv)
    now = datetime.now(timezone.utc)
    try:
        status = evaluate(load_sealed(args.lkg), now, args.ttl_minutes)
    except Exception as exc:  # last line of defence: still blocked
        status = blocked_status(now, "safe_mode_internal_error:" + type(exc).__name__)
    try:
        atomic_write(args.output, status)
    except Exception:
        pass
    print("SAFE_MODE:", status["mode"], status["reason"], "publish=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
