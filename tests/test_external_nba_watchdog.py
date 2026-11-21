"""Offline independent watchdog tests (no GitHub network or site changes)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "tools"))
import external_nba_watchdog as wd

NOW = datetime(2026, 11, 22, 0, 0, tzinfo=timezone.utc)


def run(minutes_ago, *, conclusion="success", status="completed", event="schedule",
        head_branch="main", run_id=1):
    return {
        "id": run_id,
        "event": event,
        "head_branch": head_branch,
        "created_at": (NOW - timedelta(minutes=minutes_ago)).isoformat(),
        "status": status,
        "conclusion": conclusion,
    }


class WatchdogScheduleTests(unittest.TestCase):
    def test_recent_scheduled_success_is_ok(self):
        out = wd.classify([run(9)], now=NOW)
        self.assertTrue(out["ok"])
        self.assertEqual(out["state"], "OK")

    def test_recent_pending_with_recent_success_is_ok_not_verified(self):
        out = wd.classify([run(2, run_id=2, status="in_progress", conclusion=None),
                           run(12, run_id=1)], now=NOW)
        self.assertTrue(out["ok"])
        self.assertEqual(out["state"], "PENDING_WITH_RECENT_SUCCESS")

    def test_schedule_silence_is_detected(self):
        out = wd.classify([run(23)], now=NOW)
        self.assertEqual(out["state"], "SCHEDULE_SILENT")
        self.assertFalse(out["ok"])

    def test_last_run_failed_is_detected(self):
        out = wd.classify([run(3, conclusion="failure"),
                           run(10, run_id=2)], now=NOW)
        self.assertEqual(out["state"], "LATEST_FAILED")

    def test_missing_success_despite_recent_attempt(self):
        out = wd.classify([run(2, status="in_progress", conclusion=None),
                           run(23, run_id=2)], now=NOW)
        self.assertEqual(out["state"], "NO_RECENT_VERIFIED_RUN")

    def test_pull_request_run_does_not_count_as_heartbeat(self):
        out = wd.classify([run(1, event="pull_request")], now=NOW)
        self.assertEqual(out["state"], "NO_SCHEDULE_RUNS")

    def test_future_run_time_is_rejected(self):
        out = wd.classify([run(-10)], now=NOW)
        self.assertEqual(out["state"], "FUTURE_RUN_TIME")

    def test_malformed_api_payload_fails_closed(self):
        self.assertEqual(wd.classify([{"event": "schedule", "head_branch": "main",
                                       "created_at": "not-time"}], now=NOW)["state"],
                         "INVALID_RESPONSE")
        self.assertEqual(wd.classify(None, now=NOW)["state"], "INVALID_RESPONSE")

    def test_validation_rejects_repository_name_injection(self):
        with self.assertRaises(ValueError):
            wd.get_runs("owner/repo?token=bad", "nba-injury-watch.yml")


if __name__ == "__main__":
    unittest.main()
