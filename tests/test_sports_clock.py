"""Offline tests for multi-sport KST calendar boundaries and DST."""
import sys
from datetime import datetime
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "tools"))
import sports_clock as clock


class SportsClockTests(unittest.TestCase):
    def test_soccer_madrid_kst_next_day(self):
        event = clock.event_clock("soccer", "official", "match-1",
                                  "2026-11-21T22:00:00+01:00", "Europe/Madrid")
        self.assertEqual(event["date_venue"], "2026-11-21")
        self.assertEqual(event["date_kst"], "2026-11-22")
        self.assertEqual(event["start_kst"][11:16], "06:00")
        self.assertTrue(event["crosses_calendar_day"])

    def test_nba_west_coast_kst_next_day(self):
        event = clock.event_clock("basketball", "nba", "401910025",
                                  "2026-11-21T20:30:00-08:00",
                                  "America/Los_Angeles")
        self.assertEqual(event["date_kst"], "2026-11-22")
        self.assertEqual(event["start_kst"][11:16], "13:30")

    def test_mlb_new_york_day_rollover(self):
        event = clock.event_clock("baseball", "mlb", "game-1",
                                  "2026-07-04T19:10:00-04:00",
                                  "America/New_York")
        self.assertEqual(event["date_kst"], "2026-07-05")
        self.assertEqual(event["start_kst"][11:16], "08:10")

    def test_kbo_already_kst(self):
        event = clock.event_clock("baseball", "kbo", "20260704-1",
                                  "2026-07-04T18:30:00+09:00", "Asia/Seoul")
        self.assertEqual(event["date_kst"], "2026-07-04")
        self.assertFalse(event["crosses_calendar_day"])

    def test_doubleheader_keeps_distinct_ids(self):
        a = clock.event_clock("baseball", "mlb", "20260704-g1",
                              "2026-07-04T13:00-04:00", "America/New_York")
        b = clock.event_clock("baseball", "mlb", "20260704-g2",
                              "2026-07-04T19:00-04:00", "America/New_York")
        self.assertNotEqual(a["event_key"], b["event_key"])
        self.assertEqual(a["date_venue"], b["date_venue"])

    def test_reject_naive_and_wrong_sport(self):
        with self.assertRaises(ValueError):
            clock.parse_aware("2026-11-21T20:30")
        with self.assertRaises(ValueError):
            clock.event_clock("tennis", "x", "1",
                              "2026-11-21T20:30Z", "Asia/Seoul")

    def test_dst_gap_rejected(self):
        with self.assertRaises(ValueError):
            clock.attach_local_clock(datetime(2026, 3, 8, 2, 30),
                                     "America/New_York")

    def test_dst_fold_requires_choice(self):
        local = datetime(2026, 11, 1, 1, 30)
        with self.assertRaises(ValueError):
            clock.attach_local_clock(local, "America/New_York")
        a = clock.attach_local_clock(local, "America/New_York", fold=0)
        b = clock.attach_local_clock(local, "America/New_York", fold=1)
        self.assertNotEqual(a.utcoffset(), b.utcoffset())

    def test_freshness_and_clock_conflict(self):
        valid = clock.freshness("2026-11-21T12:00:00Z",
                                "2026-11-21T12:05:00Z",
                                "2026-11-21T12:05:10Z")
        self.assertEqual(valid["state"], "CURRENT")
        stale = clock.freshness("2026-11-21T10:00:00Z",
                                "2026-11-21T12:05:00Z",
                                "2026-11-21T12:05:10Z")
        self.assertEqual(stale["state"], "STALE")
        bad = clock.freshness("2026-11-21T12:20:00Z",
                              "2026-11-21T12:05:00Z",
                              "2026-11-21T12:05:10Z")
        self.assertEqual(bad["state"], "BLOCKED")

    def test_scheduler_late_is_not_normal(self):
        on = clock.scheduled_run_health("2026-11-21T12:03:00Z",
                                        "2026-11-21T12:05:00Z")
        late = clock.scheduled_run_health("2026-11-21T12:03:00Z",
                                          "2026-11-21T12:19:00Z")
        self.assertEqual(on["state"], "ON_TIME")
        self.assertEqual(late["state"], "DELAYED")


if __name__ == "__main__":
    unittest.main()
