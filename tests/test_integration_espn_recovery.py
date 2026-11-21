"""Actual offline integration: ESPN JSON -> recovery runner -> quarantine file.

Tests intentionally run the same runner CLI used by collectors. No ESPN network,
no production site writes, no public approval and no feature branch merge.
"""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "tools"))
import recovery_runner as runner

FIXTURES = ROOT / "tests" / "fixtures"
AT = "2026-11-22T00:00:00Z"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def cli(name, sport, event_id, data, *, age=None):
    """Use a temp sandbox and assert a previous official snapshot is untouched."""
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        fixture = base / "payload.json"
        fixture.write_text(json.dumps(data), encoding="utf-8")
        previous = base / "previous.json"
        previous.write_bytes(b"EXISTING_UNCHANGED_OFFICIAL_SNAPSHOT")
        current = base / "current.json"
        changes = base / "changes.json"
        quarantine = base / "quarantine.json"
        args = [
            "--espn-fixture", str(fixture),
            "--espn-sport", sport,
            "--espn-event-id", event_id,
            "--espn-fetched-at", AT,
            "--previous", str(previous),
            "--output", str(current),
            "--changes", str(changes),
            "--quarantine", str(quarantine),
        ]
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()) as output:
            code = runner.run(args)
        q = json.loads(quarantine.read_text(encoding="utf-8")) if quarantine.exists() else None
        assert previous.read_bytes() == b"EXISTING_UNCHANGED_OFFICIAL_SNAPSHOT"
        assert not current.exists(), "ESPN must not modify official NBA snapshot"
        assert not changes.exists(), "ESPN must not modify official NBA changes"
        return code, q, output.getvalue()


class RealAdapterRunnerTest(unittest.TestCase):
    def check_rejected(self, sport, event_id, data, expected_kind, stage):
        code, q, _ = cli("test", sport, event_id, data)
        self.assertEqual(code, 1)
        self.assertIsNotNone(q, "runner must write quarantine record")
        self.assertEqual(q["kind"], expected_kind)
        self.assertEqual(q["stage"], stage)
        self.assertFalse(q["publish"])
        self.assertFalse(q["new_data_used"])
        self.assertFalse(q["current_snapshot_written"])
        self.assertFalse(q["raw_espn_json_saved"])
        self.assertEqual(q["source"], "ESPN_SITE_API_SECONDARY")
        self.assertEqual(q["sport"], sport)
        self.assertEqual(q["event_id_requested"], event_id)
        self.assertEqual(len(q["input_sha256"]), 64)
        return q

    def test_wrong_game_is_stage_two_and_writes_quarantine(self):
        self.check_rejected("basketball", "000001",
                            load_fixture("espn_nba_summary_excerpt.json"),
                            "wrong_match", 2)

    def test_duplicate_soccer_roster_is_stage_two(self):
        data = load_fixture("espn_soccer_summary_excerpt.json")
        data["rosters"][0]["roster"].append(
            deepcopy(data["rosters"][0]["roster"][0]))
        self.check_rejected("soccer", "401879233", data, "invalid_data", 2)

    def test_naive_timestamp_is_stage_two(self):
        data = load_fixture("espn_mlb_summary_excerpt.json")
        data["injuries"][0]["injuries"][0]["date"] = "2026-11-21T10:00:00"
        self.check_rejected("baseball", "401908025", data, "time_ambiguous", 2)

    def test_future_timestamp_is_stage_two(self):
        data = load_fixture("espn_nba_summary_excerpt.json")
        data["injuries"][0]["injuries"][0]["date"] = "2026-11-23T00:00Z"
        self.check_rejected("basketball", "401910023", data, "time_reversal", 2)

    def test_tampered_soccer_team_is_wrong_match(self):
        data = load_fixture("espn_soccer_summary_excerpt.json")
        data["rosters"][0]["team"]["id"] = "99"
        self.check_rejected("soccer", "401879233", data, "wrong_match", 2)

    def test_missing_injury_section_does_not_become_available(self):
        data = load_fixture("espn_nba_summary_excerpt.json")
        data.pop("injuries")
        code, q, output = cli("nba", "basketball", "401910023", data)
        self.assertEqual(code, 0)
        self.assertIsNone(q)
        self.assertIn("OFFLINE_AUDIT_ONLY", output)
        self.assertIn('"publish": false', output)

    def test_each_sport_success_is_audit_only_no_quarantine(self):
        for sport, file, event_id in [
            ("basketball", "espn_nba_summary_excerpt.json", "401910023"),
            ("soccer", "espn_soccer_summary_excerpt.json", "401879233"),
            ("baseball", "espn_mlb_summary_excerpt.json", "401908025"),
        ]:
            with self.subTest(sport=sport):
                code, q, output = cli("ok", sport, event_id, load_fixture(file))
                self.assertEqual(code, 0)
                self.assertIsNone(q)
                self.assertIn('"publish": false', output)

    def test_unclassified_internal_error_is_stage_three(self):
        # No player record exists. Its stable category is invalid_data (stage 2).
        data = load_fixture("espn_nba_summary_excerpt.json")
        data["header"]["competitions"] = None
        self.check_rejected("basketball", "401910023", data, "invalid_data", 2)

    def test_missing_fixture_triggers_safe_mode_without_writing_site_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            qpath = root / "quarantine.json"
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                code = runner.run([
                    "--espn-fixture", str(root / "missing.json"),
                    "--espn-sport", "soccer",
                    "--espn-event-id", "401879233",
                    "--espn-fetched-at", AT,
                    "--quarantine", str(qpath),
                ])
            self.assertEqual(code, 1)
            q = json.loads(qpath.read_text(encoding="utf-8"))
            self.assertEqual(q["stage"], 3)
            self.assertEqual(q["kind"], "unknown")
            self.assertFalse(q["publish"])
            self.assertFalse(q["current_snapshot_written"])
            self.assertIsNone(q["input_sha256"])

    def test_nba_workflow_uses_integrated_runner_not_legacy_path(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "nba-injury-watch.yml").read_text(encoding="utf-8")
        self.assertIn("python src/tools/recovery_runner.py", workflow)
        self.assertIn(".monitor/quarantine.json", workflow)
        self.assertNotIn("python src/tools/nba_injury_monitor.py", workflow)
        self.assertNotIn(".monitor/quarantine/*.pdf", workflow)

    def test_bad_json_is_partial_parse_stage_two(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "garbled.json"
            path.write_text("{not json", encoding="utf-8")
            qpath = root / "q.json"
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                code = runner.run([
                    "--espn-fixture", str(path), "--espn-sport", "basketball",
                    "--espn-event-id", "401910023", "--espn-fetched-at", AT,
                    "--quarantine", str(qpath),
                ])
            self.assertEqual(code, 1)
            q = json.loads(qpath.read_text(encoding="utf-8"))
            self.assertEqual(q["kind"], "partial_parse")
            self.assertEqual(q["stage"], 2)
            self.assertFalse(q["publish"])


if __name__ == "__main__":
    unittest.main()
