"""Offline ESPN adapter tests from filtered live-source JSON excerpts."""
import json
import sys
import unittest
from pathlib import Path
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "tools"))
import espn_adapter as a

FIXTURES = Path(__file__).parent / "fixtures"
CAPTURE_AT = "2026-11-22T00:00:00Z"  # test clock only, not a claim of fetch time


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ESPNAdapterTests(unittest.TestCase):
    def test_nba_ids_and_injury_not_official(self):
        result = a.normalize_summary("basketball", fixture("espn_nba_summary_excerpt.json"),
                                     fetched_at=CAPTURE_AT, expected_event_id="401910023")
        self.assertEqual(result["date_kst"], "2026-11-22")
        self.assertEqual([x["home_away"] for x in result["teams"]], ["home", "away"])
        self.assertEqual(len(result["injuries"]), 3)
        self.assertEqual(result["injuries"][0]["espn_status_raw"], "Day-To-Day")
        self.assertFalse(result["injuries"][0]["official_status_verified"])
        self.assertFalse(result["official_lineup_confirmed"])
        self.assertFalse(result["public_display_allowed"])
        self.assertFalse(result["roster_section_present"])

    def test_soccer_espn_starter_is_not_official_lineup(self):
        result = a.normalize_summary("soccer", fixture("espn_soccer_summary_excerpt.json"),
                                     fetched_at=CAPTURE_AT, expected_event_id="401879233", league="eng.1")
        self.assertEqual(result["date_kst"], "2026-11-21")
        self.assertTrue(result["roster"][0]["espn_starter_flag"])
        self.assertFalse(result["roster"][0]["official_lineup_confirmed"])
        self.assertFalse(result["injury_section_present"])
        self.assertIn("NO_INJURY_SECTION", " ".join(result["warnings"]))

    def test_baseball_old_match_cannot_inherit_new_injury(self):
        result = a.normalize_summary("baseball", fixture("espn_mlb_summary_excerpt.json"),
                                     fetched_at=CAPTURE_AT, expected_event_id="401908025")
        self.assertEqual(result["date_kst"], "2026-10-16")
        self.assertTrue(all(x["applicability"] == "POST_EVENT_UPDATE" for x in result["injuries"]))
        self.assertEqual(len(result["roster"]), 3)
        self.assertFalse(result["official_lineup_confirmed"])
        self.assertIn("POST_EVENT_INJURY_UPDATES", " ".join(result["warnings"]))

    def test_unknown_sport_and_url_injection_blocked(self):
        with self.assertRaises(a.ESPNAdapterError):
            a.summary_url("football", "401879233")
        with self.assertRaises(a.ESPNAdapterError):
            a.summary_url("soccer", "401879233&include=admin")
        with self.assertRaises(a.ESPNAdapterError):
            a.summary_url("soccer", "401879233", league="https://fake.example")
        self.assertEqual(a.summary_url("baseball", "401908025"),
                         "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event=401908025")

    def test_wrong_event_fails_closed(self):
        with self.assertRaisesRegex(a.ESPNAdapterError, "wrong game"):
            a.normalize_summary("basketball", fixture("espn_nba_summary_excerpt.json"),
                                fetched_at=CAPTURE_AT, expected_event_id="1")

    def test_mismatched_competition_id_fails(self):
        data = fixture("espn_nba_summary_excerpt.json")
        data["header"]["competitions"][0]["id"] = "401910024"
        with self.assertRaisesRegex(a.ESPNAdapterError, "does not match"):
            a.normalize_summary("basketball", data, fetched_at=CAPTURE_AT)

    def test_duplicate_team_and_injury_players_fail(self):
        data = fixture("espn_nba_summary_excerpt.json")
        data["header"]["competitions"][0]["competitors"][1]["team"]["id"] = "20"
        with self.assertRaises(a.ESPNAdapterError):
            a.normalize_summary("basketball", data, fetched_at=CAPTURE_AT)
        data = fixture("espn_nba_summary_excerpt.json")
        data["injuries"][0]["injuries"].append(deepcopy(data["injuries"][0]["injuries"][0]))
        with self.assertRaisesRegex(a.ESPNAdapterError, "duplicate injury"):
            a.normalize_summary("basketball", data, fetched_at=CAPTURE_AT)

    def test_missing_injury_does_not_mean_available(self):
        data = fixture("espn_nba_summary_excerpt.json")
        del data["injuries"]
        result = a.normalize_summary("basketball", data, fetched_at=CAPTURE_AT)
        self.assertFalse(result["injury_section_present"])
        self.assertEqual(result["injuries"], [])
        self.assertFalse(any(x.get("espn_status_raw") == "Available" for x in result["injuries"]))

    def test_invalid_starter_flag_and_roster_team_rejected(self):
        data = fixture("espn_soccer_summary_excerpt.json")
        data["rosters"][0]["roster"][0]["starter"] = "true"
        with self.assertRaisesRegex(a.ESPNAdapterError, "starter flag"):
            a.normalize_summary("soccer", data, fetched_at=CAPTURE_AT)
        data = fixture("espn_soccer_summary_excerpt.json")
        data["rosters"][0]["team"]["id"] = "3"
        with self.assertRaisesRegex(a.ESPNAdapterError, "wrong game team"):
            a.normalize_summary("soccer", data, fetched_at=CAPTURE_AT)

    def test_timestamp_requires_timezone(self):
        with self.assertRaisesRegex(a.ESPNAdapterError, "offset"):
            a.parse_timestamp("2026-11-21T12:30:00")

    def test_future_injury_timestamp_rejected(self):
        data = fixture("espn_nba_summary_excerpt.json")
        data["injuries"][0]["injuries"][0]["date"] = "2030-01-01T00:00Z"
        with self.assertRaisesRegex(a.ESPNAdapterError, "future"):
            a.normalize_summary("basketball", data, fetched_at=CAPTURE_AT)

    def test_all_three_sports_remain_nonpublishing(self):
        for sport, name in (("basketball", "espn_nba_summary_excerpt.json"),
                            ("soccer", "espn_soccer_summary_excerpt.json"),
                            ("baseball", "espn_mlb_summary_excerpt.json")):
            with self.subTest(sport=sport):
                result = a.normalize_summary(sport, fixture(name), fetched_at=CAPTURE_AT)
                self.assertEqual(result["publication_status"], "NOT_APPROVED")
                self.assertFalse(result["public_display_allowed"])
                self.assertFalse(result["official_lineup_confirmed"])


if __name__ == "__main__":
    unittest.main()
