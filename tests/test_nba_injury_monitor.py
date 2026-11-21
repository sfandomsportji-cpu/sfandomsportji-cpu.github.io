"""Offline safety checks: no live NBA network request or website mutation."""
import sys
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "tools"))
import nba_injury_monitor as m


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
            ("", "", "", "", "Unknown, Person", "Not Sure", ""),
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
