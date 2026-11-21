"""Fault injection: when the collector fails, is new data quarantined and nothing published?

Offline only. The collector's fetch/parse are patched to fail in realistic ways; the
runner then follows the workflow's order (collector -> classify -> quarantine record ->
stale failover). Each scenario checks what is left on disk.
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "src" / "tools"
sys.path.insert(0, str(TOOLS))
import nba_injury_monitor as m
import recovery_runner as rr

URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-21_08_30AM.pdf"


def row(i, status="Out"):
    return {"game_date": "2026-11-21", "matchup": "MIL@PHI", "team": "Milwaukee Bucks",
            "player": f"Player, N{i}", "official_status": status,
            "state": status.lower(), "lineup": "not_verified"}


def rows(n, status="Out"):
    return {f"2026-11-21|MIL@PHI|Milwaukee Bucks|Player, N{i}": row(i, status) for i in range(n)}


def previous_snapshot(now):
    return {"checked_at_utc": (now - timedelta(minutes=10)).isoformat(),
            "report_at_et": "2026-11-21T08:00:00-05:00",
            "source_url": URL, "players": rows(5)}


class FaultInjectionTest(unittest.TestCase):
    def run_case(self, effect, expected_kind, expected_stage):
        now = datetime.now(timezone.utc)
        reported = now - timedelta(minutes=15)
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            prev = base / "previous.json"
            prev.write_text(json.dumps(previous_snapshot(now)), encoding="utf-8")
            before = prev.read_bytes()
            argv = ["--previous", str(prev), "--output", str(base / "current.json"),
                    "--changes", str(base / "changes.json"),
                    "--incident", str(base / "incident.json"),
                    "--quarantine", str(base / "quarantine.json")]
            fetch = effect.get("fetch", (URL, reported, b"%PDF-1.7"))
            with patch.object(m, "fetch_official",
                              **({"side_effect": fetch} if isinstance(fetch, Exception)
                                 else {"return_value": fetch})):
                parse = effect.get("parse")
                if isinstance(parse, Exception):
                    ctx = patch.object(m, "parse_pdf", side_effect=parse)
                else:
                    ctx = patch.object(m, "parse_pdf", return_value=parse)
                with ctx:
                    code = rr.run(argv)
            self.assertEqual(code, 1, "failure must be reported to the workflow")
            self.assertEqual(prev.read_bytes(), before, "last known-good file must be untouched")
            self.assertFalse((base / "changes.json").exists(), "no change list from rejected data")
            quarantine = json.loads((base / "quarantine.json").read_text(encoding="utf-8"))
            self.assertEqual(quarantine["kind"], expected_kind)
            self.assertEqual(quarantine["stage"], expected_stage)
            self.assertFalse(quarantine["publish"])
            self.assertFalse(quarantine["new_data_used"])
            self.assertTrue(quarantine["error_message"])
            current = json.loads((base / "current.json").read_text(encoding="utf-8"))
            self.assertEqual(current["freshness"], "STALE")
            self.assertFalse(current["public_display_allowed"])
            self.assertEqual(current["publication_status"], "NOT_APPROVED")
            self.assertEqual(current["players"], previous_snapshot(now)["players"],
                             "only the previous verified rows may be carried, for audit")
            return quarantine

    def test_source_unreachable(self):
        q = self.run_case({"fetch": RuntimeError("NBA official source unavailable: a:OSError")},
                          "source_timeout", 1)
        self.assertIn("try_official_alternate_source", q["actions"])

    def test_unknown_status_in_pdf(self):
        self.run_case({"parse": {"k": row(1, "Weird")}}, "invalid_data", 2)

    def test_sharp_row_drop_is_partial_parse(self):
        self.run_case({"parse": rows(1)}, "partial_parse", 2)

    def test_empty_parse(self):
        self.run_case({"parse": ValueError("no unambiguous player statuses parsed; previous data retained")},
                      "partial_parse", 2)

    def test_layout_change(self):
        self.run_case({"parse": ValueError("NBA PDF page count outside safety bounds")},
                      "layout_changed", 2)

    def test_dst_ambiguity_not_retried(self):
        q = self.run_case({"fetch": ValueError("ambiguous local time (DST fold); specify fold")},
                          "time_ambiguous", 2)
        self.assertNotIn("revalidate_with_known_good_parser", q["actions"])

    def test_stale_source(self):
        old = datetime.now(timezone.utc) - timedelta(hours=3)
        self.run_case({"fetch": (URL, old, b"%PDF-1.7"), "parse": rows(5)}, "stale_source", 2)

    def test_unexpected_crash_goes_to_safe_mode(self):
        self.run_case({"parse": KeyError("boom")}, "unknown", 3)

    def test_success_leaves_no_quarantine(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            prev = base / "previous.json"
            prev.write_text(json.dumps(previous_snapshot(now)), encoding="utf-8")
            with patch.object(m, "fetch_official",
                              return_value=(URL, now - timedelta(minutes=15), b"%PDF-1.7")), \
                    patch.object(m, "parse_pdf", return_value=rows(5)):
                code = rr.run(["--previous", str(prev), "--output", str(base / "current.json"),
                               "--changes", str(base / "changes.json"),
                               "--incident", str(base / "incident.json"),
                               "--quarantine", str(base / "quarantine.json")])
            self.assertEqual(code, 0)
            self.assertFalse((base / "quarantine.json").exists())
            current = json.loads((base / "current.json").read_text(encoding="utf-8"))
            self.assertEqual(current["publication_status"], "NOT_APPROVED")
            self.assertFalse(current["public_display_allowed"])


if __name__ == "__main__":
    unittest.main()
