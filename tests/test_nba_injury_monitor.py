"""Offline safety checks: no live NBA network request or website mutation."""
import sys
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "tools"))
import nba_injury_monitor as m
import injury_failover as f


class FakePage:
    width = 1000.0
    starts = (30, 150, 250, 350, 530, 720, 825)

    def __init__(self, rows):
        self.words = []
        for index, cells in enumerate(rows):
            y = index * 18.0 + 80.0
            for col, value in enumerate(cells):
                for n, token in enumerate(value.split()):
                    self.words.append({"top": y, "x0": self.starts[col] + n * 18,
                                       "text": token})

    def extract_words(self, **_kwargs):
        return self.words


class MonitorSafetyTest(unittest.TestCase):
    def test_pdf_rows_and_no_lineup_claim(self):
        first = FakePage([
            ("11/21/2026", "01:00", "MIL@PHI", "Milwaukee Bucks",
             "Dieng, Ousmane", "Out", "Injury"),
            ("", "", "", "", "Jones, Kam", "Probable", ""),
            ("", "", "", "Philadelphia 76ers", "Maxey, Tyrese", "Questionable", ""),
            ("", "", "POR@NYK", "Portland Trail Blazers",
             "Avdija, Deni", "Available", ""),
            ("", "", "", "New York Knicks", "NOT YET SUBMITTED", "", ""),
        ])
        rows = m.parse_pages([first])
        self.assertEqual(len(rows), 4)
        statuses = {item["player"]: item["official_status"] for item in rows.values()}
        self.assertEqual(statuses["Dieng, Ousmane"], "Out")
        self.assertEqual(statuses["Jones, Kam"], "Probable")
        self.assertEqual(statuses["Maxey, Tyrese"], "Questionable")
        self.assertEqual(statuses["Avdija, Deni"], "Available")
        self.assertTrue(all(row["lineup"] == "not_verified" for row in rows.values()))

    def test_new_unknown_player_status_blocks_entire_pdf(self):
        page = FakePage([
            ("11/21/2026", "01:00", "MIL@PHI", "Milwaukee Bucks",
             "Unknown, Person", "Not Sure", "Unrecognized status"),
        ])
        with self.assertRaises(m.injury_quality.DataQualityError):
            m.parse_pages([page])

    def test_parsing_continues_on_new_page(self):
        one = FakePage([("11/21/2026", "08:00", "LAC@DAL",
                          "LA Clippers", "Beal, Bradley", "Out", "")])
        two = FakePage([("", "", "", "Dallas Mavericks",
                          "Martin, Caleb", "Available", "")])
        rows = m.parse_pages([one, two])
        self.assertEqual(len(rows), 2)

    def test_unparseable_document_fails_closed(self):
        with self.assertRaises(ValueError):
            m.parse_pages([FakePage([("", "", "", "",
                                     "NOT YET SUBMITTED", "", "")])])

    def test_only_exact_official_pdf_links(self):
        now = datetime(2026, 11, 21, 14, 0, tzinfo=timezone.utc)
        html = ('<a href="https://ak-static.cms.nba.com/referee/injury/'
                'Injury-Report_2026-11-21_08_30AM.pdf">latest</a>'
                '<a href="https://evil.example/referee/injury/'
                'Injury-Report_2026-11-21_10_00AM.pdf">bad</a>'
                '<a href="https://ak-static.cms.nba.com/referee/injury/'
                'Injury-Report_2026-11-21_07_30AM.pdf">older</a>')
        url, when = m.choose_latest(html, m.LISTINGS[0], now)
        self.assertIn("08_30AM", url)
        self.assertEqual(when.hour, 8)

    def test_dst_duplicate_and_missing_et_report_times_blocked(self):
        # PDF name carries Eastern clock time but no UTC offset.
        # DST transition at 1:30AM in November has two possible UTC instants.
        for tail in ("2026-11-01_01_30AM", "2026-03-08_02_30AM"):
            url = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_" + tail + ".pdf"
            with self.subTest(url=url), self.assertRaises(ValueError):
                m.report_datetime(url)

    def test_gap_recovers_with_new_baseline_but_remains_unapproved(self):
        import json
        import tempfile
        from unittest.mock import patch
        now = datetime.now(timezone.utc)
        reported = now - timedelta(minutes=15)
        key = "2026-11-21|MIL@PHI|Milwaukee Bucks|Dieng, Ousmane"
        value = {
            "game_date": "2026-11-21", "matchup": "MIL@PHI",
            "team": "Milwaukee Bucks", "player": "Dieng, Ousmane",
            "official_status": "Out", "state": "out",
            "lineup": "not_verified",
        }
        previous = {
            "checked_at_utc": (now - timedelta(minutes=35)).isoformat(),
            "source_url": "https://ak-static.cms.nba.com/referee/injury/previous.pdf",
            "players": {key: value},
        }
        url = ("https://ak-static.cms.nba.com/referee/injury/"
               "Injury-Report_2026-11-21_08_30AM.pdf")
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            prev = base / "prev.json"
            result = base / "current.json"
            changes = base / "changes.json"
            prev.write_text(json.dumps(previous), encoding="utf-8")
            with patch.object(m, "fetch_official", return_value=(url, reported, b"%PDF-1.7")):
                with patch.object(m, "parse_pdf", return_value={key: value}):
                    self.assertEqual(
                        m.main(["--previous", str(prev), "--output", str(result),
                                "--changes", str(changes)]), 0)
            report = json.loads(result.read_text(encoding="utf-8"))
            self.assertTrue(report["schedule_gap_alert"])
            self.assertTrue(report["review_required"])
            self.assertEqual(report["publication_status"], "NOT_APPROVED")
            self.assertEqual(report["freshness"], "CURRENT")

    def test_stale_report_is_not_accepted(self):
        now = datetime(2026, 11, 21, 16, 0, tzinfo=timezone.utc)
        html = ('<a href="https://ak-static.cms.nba.com/referee/injury/'
                'Injury-Report_2026-11-21_07_00AM.pdf">old</a>')
        with self.assertRaises(ValueError):
            m.choose_latest(html, m.LISTINGS[0], now)

    def test_changes_do_not_infer_absence_as_available(self):
        key = "2026-11-21|LAC@DAL|Dallas Mavericks|Martin, Caleb"
        player = {"official_status": "Out"}
        old = {"players": {key: player}}
        changes, baseline = m.compare(old, {"players": {}})
        self.assertFalse(baseline)
        self.assertEqual(changes, [])

    def test_failover_has_no_publish_path_and_preserves_previous_as_stale(self):
        from datetime import datetime, timezone
        old = {"source_url": "https://ak-static.cms.nba.com/old.pdf",
               "checked_at_utc": "2026-11-21T11:00:00+00:00",
               "players": {"some-player": {"official_status": "Out"}}}
        result = f.fallback(old, datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(result["freshness"], "STALE")
        self.assertEqual(result["publication_status"], "NOT_APPROVED")
        self.assertFalse(result["public_display_allowed"])
        self.assertEqual(result["previous_checked_at_utc"], old["checked_at_utc"])
        self.assertEqual(result["players"], old["players"])

    def test_workflow_has_read_only_permissions_and_no_publish_commands(self):
        wf = (Path(__file__).resolve().parents[1] /
              ".github/workflows/nba-injury-watch.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", wf)
        self.assertNotIn("contents: write", wf)
        self.assertNotIn("git push", wf)
        self.assertNotIn("src/build.py", wf)
        self.assertIn("3,13,23,33,43,53 * * * *", wf)

    def test_diff_and_first_baseline(self):
        key = "2026-11-21|LAC@DAL|Dallas Mavericks|Martin, Caleb"
        previous = {"players": {key: {"official_status": "Questionable"}}}
        current = {"players": {key: {"official_status": "Available"}}}
        changes, baseline = m.compare(previous, current)
        self.assertFalse(baseline)
        self.assertEqual(changes[0]["type"], "changed")
        self.assertEqual(changes[0]["before"], "Questionable")
        changes2, baseline2 = m.compare({}, current)
        self.assertEqual(changes2, [])
        self.assertTrue(baseline2)


if __name__ == "__main__":
    unittest.main()
