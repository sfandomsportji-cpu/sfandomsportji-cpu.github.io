# SFANDOM ESPN 3-sport adapter — review only

## Purpose and trust boundary

Read-only normalization of **basketball (NBA), soccer (English Premier League example), baseball (MLB)** ESPN game-summary JSON. This module has **no HTTP fetches and no publish path**. All normalized ESPN-derived values remain secondary evidence; the official league/club announcement has priority for injury and confirmed lineup claims.

## Observed field paths

| Sport | ESPN JSON | SFANDOM meaning |
|---|---|---|
| Basketball | header.id, header.competitions[0].date | provider event ID and UTC start |
| Basketball | injuries[].team.id; injuries[].injuries[].athlete.id/status/date | ESPN-reported status, not official confirmation |
| Soccer | rosters[].team.id; rosters[].roster[].athlete.id/starter | ESPN starter flag, not verified official lineup |
| Baseball | rosters[].roster[].starter / optional battingOrder | ESPN observed batting/roster flag, not confirmed |
| Baseball | injuries[].injuries[].date/status | May be updated *after* a historical game; do not backdate |

## Real-response URLs (JSON fixtures are reduced excerpts, **not full raw responses**)

- NBA: https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=401910023
- EPL: https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event=401879233
- MLB: https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event=401908025

## Calling contract

The transport layer separately obtains JSON only where authorized, handles HTTP failures, timeouts and retention. The adapter itself is pure and has no network, site mutation, player guessing or automatic approval.

    from espn_adapter import summary_url, normalize_summary
    url = summary_url("soccer", "401879233", league="eng.1")
    record = normalize_summary("soccer", response_json,
        fetched_at="2026-11-22T00:00:00Z",
        expected_event_id="401879233", league="eng.1")
    assert record["public_display_allowed"] is False

## Fail-closed checks

Wrong game/competition ID, missing or duplicate team, wrong team/home-away pair, duplicate athlete IDs, naive times and invalid starter flags are rejected. Missing injuries do **not** imply player availability. Injuries updated after event start are tagged POST_EVENT_UPDATE; they must **not** be used to infer historical pregame status.

## Deployment gates

- **P0 NBA**: real NBA official PDF vs parser output page-by-page and player/team/status comparison.
- **P0 source validity**: ESPN access/licensing/allowed collection rate, competition-by-competition response schemas, official source mapping.
- **P0 data coverage**: fixture excerpts deliberately omit players, so no lineup or injury completeness assertion is possible.
- **P1 recovery**: integrate reviewed ESPN adapter into source collection only after independent safety / heartbeat design is validated; never automatically merge into existing PR #30/#31.
- KBL/KBO and other soccer leagues require separate real source verification, and are not implied by NBA/MLB/EPL fixtures.
- Historical ESPN injuries may contain updates later than the event. No retroactive interpretation of later changes.
- ESPN athlete IDs and official league player IDs are different namespaces until an explicit verified mapping exists.

**Only a separate operator-approved production PR may connect this to a public site or editorial publication.**
