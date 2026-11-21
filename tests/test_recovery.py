"""Offline tests for the independent recovery modules (no network, no site writes)."""
import ast
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "src" / "tools"
sys.path.insert(0, str(TOOLS))
import recovery_policy as rp
import safe_mode as sm
import watchdog as wd

NOW = datetime(2026, 11, 21, 13, 0, tzinfo=timezone.utc)
STDLIB_ONLY = {"argparse", "hashlib", "json", "datetime", "pathlib", "dataclasses"}


def snap(minutes_ago):
    return {"checked_at_utc": (NOW - timedelta(minutes=minutes_ago)).isoformat(),
            "players": {"x": {"official_status": "Out"}}}


class IndependenceTest(unittest.TestCase):
    def test_no_dependency_on_collector_or_clock_module(self):
        for name in ("safe_mode.py", "recovery_policy.py", "watchdog.py"):
            tree = ast.parse((TOOLS / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    mods = [node.module or ""]
                for mod in mods:
                    self.assertIn(mod.split(".")[0], STDLIB_ONLY, f"{name} imports {mod}")


class SafeModeTest(unittest.TestCase):
    def test_never_public_and_no_player_data(self):
        for minutes in (1, 80, 500):
            status = sm.evaluate(snap(minutes), NOW)
            self.assertFalse(status["public_display_allowed"])
            self.assertEqual(status["publication_status"], "NOT_APPROVED")
            self.assertEqual(status["lineup"], "unconfirmed")
            self.assertNotIn("players", status)

    def test_expired_snapshot_becomes_unknown(self):
        self.assertEqual(sm.evaluate(snap(91), NOW)["reason"], "last_known_good_expired")
        self.assertEqual(sm.evaluate(snap(30), NOW)["mode"], "AUDIT_ONLY")

    def test_missing_or_clock_reversed_is_blocked(self):
        self.assertEqual(sm.evaluate(None, NOW)["reason"], "no_valid_last_known_good")
        self.assertEqual(sm.evaluate(snap(-10), NOW)["reason"], "clock_reversal")

    def test_naive_timestamp_rejected(self):
        bad = {"checked_at_utc": "2026-11-21T12:00:00"}
        self.assertEqual(sm.evaluate(bad, NOW)["reason"], "last_known_good_timestamp_invalid")

    def test_sealed_copy_detects_tampering_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lkg.json"
            sm.seal(snap(5), path)
            self.assertIsNotNone(sm.load_sealed(path))
            data = json.loads(path.read_text(encoding="utf-8"))
            data["snapshot"]["players"]["x"]["official_status"] = "Available"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertIsNone(sm.load_sealed(path))
            path.write_text("{not json", encoding="utf-8")
            self.assertIsNone(sm.load_sealed(path))
            self.assertIsNone(sm.load_sealed(Path(tmp) / "absent.json"))

    def test_main_never_raises_and_writes_blocked_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "status.json"
            code = sm.main(["--lkg", str(Path(tmp) / "absent.json"), "--output", str(out)])
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out.read_text(encoding="utf-8"))["public_display_allowed"])


class PolicyTest(unittest.TestCase):
    def test_transient_retries_then_escalates(self):
        self.assertEqual(rp.decide("source_timeout", 1).stage, 1)
        self.assertEqual(rp.decide("source_timeout", rp.MAX_RETRIES).stage, 1)
        self.assertEqual(rp.decide("source_timeout", rp.MAX_RETRIES + 1).stage, 3)

    def test_bad_data_is_quarantined_and_alerts(self):
        for kind in ("invalid_data", "wrong_match", "partial_parse"):
            d = rp.decide(kind)
            self.assertEqual(d.stage, 2)
            self.assertIn("quarantine_new_data", d.actions)
            self.assertTrue(d.alert_operator)

    def test_unfixable_by_retry_goes_to_human_without_reparse(self):
        for kind in rp.NO_RETRY:
            self.assertNotIn("revalidate_with_known_good_parser", rp.decide(kind).actions)

    def test_system_unknown_and_long_gap_use_safe_mode(self):
        self.assertEqual(rp.decide("collector_failed").stage, 3)
        self.assertEqual(rp.decide("something_new").stage, 3)
        self.assertEqual(rp.decide("source_timeout", 1, gap_minutes=23).stage, 3)

    def test_publish_is_never_allowed_by_policy(self):
        kinds = rp.TRANSIENT | rp.BAD_DATA | rp.SYSTEM | {"unknown_kind"}
        self.assertFalse(any(rp.decide(k).publish for k in kinds))

    def test_internal_error_fails_closed(self):
        self.assertEqual(rp.decide(["unhashable"], "x", object()).stage, 3)

    def test_resume_needs_both_revalidation_and_operator(self):
        self.assertFalse(rp.may_resume_publication(True, False))
        self.assertFalse(rp.may_resume_publication(False, True))
        self.assertFalse(rp.may_resume_publication(True, None))
        self.assertTrue(rp.may_resume_publication(True, True))


class ClassifierTest(unittest.TestCase):
    def test_typed_failure_kind_wins_over_message(self):
        class Typed(ValueError):
            def __init__(self, msg, kind):
                super().__init__(msg)
                self.failure_kind = kind
        self.assertEqual(rp.classify_exception(Typed("anything at all", "wrong_match")), "wrong_match")
        self.assertEqual(rp.classify_exception(Typed("timestamp", "time_ambiguous")), "time_ambiguous")
        self.assertEqual(rp.classify_exception(Typed("x", "time_reversal")), "time_reversal")

    def test_unknown_declared_kind_is_not_trusted(self):
        class Typed(ValueError):
            failure_kind = "publish_now"
        self.assertEqual(rp.classify_exception(Typed("weird")), "unknown")
        self.assertEqual(rp.decide(rp.classify_exception(Typed("weird"))).stage, 3)

    def test_non_string_declared_kind_is_ignored(self):
        class Typed(ValueError):
            failure_kind = ["wrong_match"]
        self.assertEqual(rp.classify_exception(Typed("boom")), "unknown")

    def test_typed_kinds_route_to_stage_two_without_publishing(self):
        for kind in ("invalid_data", "wrong_match", "partial_parse",
                     "time_ambiguous", "time_reversal", "layout_changed"):
            d = rp.decide(kind)
            self.assertEqual(d.stage, 2, kind)
            self.assertFalse(d.publish)
            self.assertIn("quarantine_new_data", d.actions)

    def test_message_matching_still_works_for_untyped_errors(self):
        self.assertEqual(rp.classify_exception(ValueError("sharp row drop: a")), "partial_parse")


class WatchdogTest(unittest.TestCase):
    def test_states(self):
        ok = (NOW - timedelta(minutes=10)).isoformat()
        late = (NOW - timedelta(minutes=23)).isoformat()
        future = (NOW + timedelta(minutes=10)).isoformat()
        self.assertEqual(wd.check(ok, NOW)[0], "OK")
        self.assertEqual(wd.check(late, NOW)[0], "LATE")
        self.assertEqual(wd.check(future, NOW)[0], "FUTURE")
        self.assertEqual(wd.check(None, NOW)[0], "MISSING")
        self.assertEqual(wd.check("2026-11-21T12:00:00", NOW)[0], "INVALID")
        self.assertEqual(wd.check("garbage", NOW)[0], "INVALID")

    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            hb = Path(tmp) / "hb.json"
            self.assertEqual(wd.main(["--heartbeat", str(hb)]), 1)  # missing
            hb.write_text(json.dumps({"at_utc": datetime.now(timezone.utc).isoformat()}),
                          encoding="utf-8")
            self.assertEqual(wd.main(["--heartbeat", str(hb)]), 0)


if __name__ == "__main__":
    unittest.main()
