"""Safety tests for NBA data-identity and partial-document quarantine."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "tools"))
import injury_quality as q
import nba_injury_monitor as monitor


def row(date="2026-11-21", matchup="MIL@PHI", team="Milwaukee Bucks",
        player="Dieng, Ousmane", status="Out"):
    return {
        "game_date": date, "matchup": matchup, "team": team,
        "player": player, "official_status": status,
        "state": status.lower(), "lineup": "not_verified",
    }


def player_set(players):
    return {
        "|".join((x["game_date"], x["matchup"], x["team"], x["player"])): x
        for x in players
    }


class QualityGateTests(unittest.TestCase):
    def test_valid_official_rows_pass_without_claiming_starting_lineup(self):
        players = player_set([
            row(player="Dieng, Ousmane", status="Out"),
            row(player="Jones, Kam", status="Probable"),
            row(team="Philadelphia 76ers", player="Maxey, Tyrese", status="Questionable"),
        ])
        summary = q.validate_snapshot({}, players, "2026-11-20T19:15:00-05:00")
        self.assertEqual(summary["state"], "PASSED")
        self.assertEqual(summary["rows"], 3)

    def test_bad_key_is_not_associated_with_another_player(self):
        players = {"2026-11-21|MIL@PHI|Milwaukee Bucks|Other, Person": row()}
        with self.assertRaises(q.DataQualityError):
            q.validate_rows(players)

    def test_new_unrecognized_status_is_quarantined(self):
        players = player_set([row(status="New Unexpected Status")])
        with self.assertRaises(q.DataQualityError):
            q.validate_rows(players)

    def test_status_row_without_team_is_fatal_instead_of_ignored(self):
        class FakePage:
            width = 1000
            def extract_words(self, **kwargs):
                # Header row is intentionally missing the team and game.
                return [{"top": 80, "x0": 530, "text": "Dieng,"},
                        {"top": 80, "x0": 560, "text": "Ousmane"},
                        {"top": 80, "x0": 720, "text": "Out"}]
        with self.assertRaises(q.DataQualityError):
            monitor.parse_pages([FakePage()])

    def test_partial_document_drops_more_than_half_same_team_rows(self):
        before = player_set([row(player=f"Player, {n}") for n in range(6)])
        after = player_set([row(player="Player, 0")])
        previous = {
            "report_at_et": "2026-11-20T19:15:00-05:00",
            "players": before,
        }
        with self.assertRaises(q.DataQualityError):
            q.validate_snapshot(previous, after, "2026-11-20T19:45:00-05:00")

    def test_new_report_day_not_compared_to_prior_day(self):
        before = player_set([row(player=f"Player, {n}") for n in range(6)])
        after = player_set([row(player="Player, 0")])
        previous = {
            "report_at_et": "2026-11-19T19:15:00-05:00",
            "players": before,
        }
        checked = q.validate_snapshot(previous, after, "2026-11-20T08:15:00-05:00")
        self.assertEqual(checked["state"], "PASSED")

    def test_missing_entry_never_infers_available(self):
        before = player_set([row(player=f"Player, {n}") for n in range(3)])
        after = player_set([row(player="Player, 1")])
        previous = {
            "report_at_et": "2026-11-20T19:15:00-05:00",
            "players": before,
        }
        checked = q.validate_snapshot(previous, after, "2026-11-20T19:30:00-05:00")
        self.assertEqual(checked["rows"], 1)
        self.assertNotIn("Available", [v["official_status"] for v in after.values()])


if __name__ == "__main__":
    unittest.main()
