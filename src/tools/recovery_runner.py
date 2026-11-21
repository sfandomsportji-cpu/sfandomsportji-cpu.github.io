#!/usr/bin/env python3
"""Run the NBA collector; on any failure classify, quarantine evidence, fail closed.

Writes .monitor/quarantine.json (why it failed, which stage, what the policy
decided) and then the stage-3 stale record via injury_failover. The collector's
own files are never touched on failure: the rejected data is dropped, the last
known-good file stays as it was, and nothing is published.

Exit code 0 only when the collector verified a new snapshot; 1 otherwise.
"""
import argparse
import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recovery_policy as policy


def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def quarantine_record(exc, decision, now, failures):
    return {
        "at_utc": now.isoformat(),
        "kind": decision.kind,
        "stage": decision.stage,
        "actions": list(decision.actions),
        "reason": decision.reason,
        "consecutive_failures": failures,
        "error_type": type(exc).__name__,
        "error_message": str(exc)[:300],
        "error_sha256": hashlib.sha256(str(exc).encode("utf-8")).hexdigest(),
        "alert_operator": decision.alert_operator,
        "publish": False,
        "new_data_used": False,
    }


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--previous", default=".monitor/previous.json")
    ap.add_argument("--output", default=".monitor/current.json")
    ap.add_argument("--changes", default=".monitor/changes.json")
    ap.add_argument("--incident", default=".monitor/incident.json")
    ap.add_argument("--quarantine", default=".monitor/quarantine.json")
    ap.add_argument("--failures", type=int, default=1,
                    help="consecutive failures so far, including this one")
    args = ap.parse_args(argv)
    now = datetime.now(timezone.utc)
    try:
        collector = importlib.import_module("nba_injury_monitor")
        collector.main(["--previous", args.previous, "--output", args.output,
                        "--changes", args.changes])
        return 0
    except Exception as exc:  # includes ImportError of the collector itself
        kind = ("collector_failed" if isinstance(exc, ImportError)
                else policy.classify_exception(exc))
        decision = policy.decide(kind, args.failures)
        record = quarantine_record(exc, decision, now, args.failures)
        try:
            _write(args.quarantine, record)
        except Exception:
            pass
        print(f"RECOVERY: kind={decision.kind} stage={decision.stage} publish=False",
              file=sys.stderr)
        try:
            failover = importlib.import_module("injury_failover")
            failover.main(["--previous", args.previous, "--output", args.output,
                           "--incident", args.incident])
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
