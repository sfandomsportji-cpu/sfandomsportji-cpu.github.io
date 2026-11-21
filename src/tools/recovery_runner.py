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


def save_evidence(captured, directory):
    """Keep the rejected PDF and extracted rows, named by content hash, for later audit."""
    evidence = {"pdf_saved": False, "rows_saved": False}
    pdf = captured.get("pdf")
    if isinstance(pdf, (bytes, bytearray)) and pdf:
        digest = hashlib.sha256(pdf).hexdigest()
        path = Path(directory) / f"rejected_{digest[:16]}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes(pdf))
        evidence.update(pdf_saved=True, pdf_sha256=digest, pdf_bytes=len(pdf),
                        pdf_file=path.name, source_url=captured.get("url"))
        reported = captured.get("reported")
        if reported is not None:
            evidence["report_at"] = reported.isoformat()
    rows = captured.get("rows")
    if isinstance(rows, dict):
        raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=2)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        path = Path(directory) / f"rejected_{digest[:16]}.rows.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw + "\n", encoding="utf-8")
        evidence.update(rows_saved=True, rows_count=len(rows),
                        rows_sha256=digest, rows_file=path.name)
    return evidence


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
    ap.add_argument("--evidence-dir", default=".monitor/quarantine")
    ap.add_argument("--failures", type=int, default=1,
                    help="consecutive failures so far, including this one")
    args = ap.parse_args(argv)
    now = datetime.now(timezone.utc)
    captured = {}
    collector = None
    originals = {}
    try:
        collector = importlib.import_module("nba_injury_monitor")
        originals = {"fetch_official": collector.fetch_official,
                     "parse_pdf": collector.parse_pdf}

        def recording_fetch(*a, **k):
            url, reported, pdf = originals["fetch_official"](*a, **k)
            captured.update(url=url, reported=reported, pdf=pdf)
            return url, reported, pdf

        def recording_parse(pdf_bytes, **k):
            rows = originals["parse_pdf"](pdf_bytes, **k)
            captured["rows"] = rows
            return rows

        collector.fetch_official = recording_fetch
        collector.parse_pdf = recording_parse
        collector.main(["--previous", args.previous, "--output", args.output,
                        "--changes", args.changes])
        return 0
    except Exception as exc:  # includes ImportError of the collector itself
        kind = ("collector_failed" if isinstance(exc, ImportError)
                else policy.classify_exception(exc))
        decision = policy.decide(kind, args.failures)
        record = quarantine_record(exc, decision, now, args.failures)
        try:
            record["evidence"] = save_evidence(captured, args.evidence_dir)
        except Exception as save_exc:
            record["evidence"] = {"pdf_saved": False, "rows_saved": False,
                                  "error": type(save_exc).__name__}
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
    finally:
        if collector is not None and originals:
            collector.fetch_official = originals["fetch_official"]
            collector.parse_pdf = originals["parse_pdf"]


if __name__ == "__main__":
    raise SystemExit(run())
