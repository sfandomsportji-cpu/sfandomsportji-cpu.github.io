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


## Review follow-up: typed errors, injury age, confirmation and quarantine

**P1 — stable recovery classification contract:** Every `ESPNAdapterError` has a `failure_kind` string. Examples: `wrong_match` (wrong event/team), `time_ambiguous` (naive clock), `time_reversal` (future injury update), and `invalid_data` (duplicate/invalid player). **Use the attribute, not English error text.** The PR #31 recovery-policy maintainer owns classifier integration; this PR intentionally does not edit that branch.

**P1 — official confirmation remains external:** ESPN normalization adds `lineup_confirmation_state="UNVERIFIED"`. A future independent official-source verification layer may transition to `OFFICIAL_CONFIRMED`, `CONFLICT`, or `REVOKED` only after validating an authoritative source, event ID, player/team mapping, and publication time. The adapter itself cannot confirm lineups or publish. An ESPN `starter=true` flag does not grant approval.

**P2 — age warnings:** An ESPN injury `date` more than **7 days** before collection triggers `STALE_ESPN_REPORT` and `STALE_ESPN_INJURIES`. No update timestamp triggers `UNDATED_ESPN_REPORT`; a post-event update stays `POST_EVENT_UPDATE` even when stale. Seven days is an *initial warning threshold*, not a medical or league-validity rule. Old reports may still describe a genuine long-term absence; **never infer recovery or availability from age**.

**P2 — fail-closed scope:** A malformed/mismatched roster or injury row fails normalization for the **entire event**, rather than partially accepting a possibly wrong lineup. This is deliberate for pre-production accuracy. Raw input can be quarantined for investigation; per-row exceptions would require a separately reviewed completeness policy.

### Integration snippet for PR #31 (not wired in this branch)

```python
kind = getattr(exc, "failure_kind", None)
if kind not in (recovery_policy.BAD_DATA | recovery_policy.SYSTEM | recovery_policy.TRANSIENT):
    kind = recovery_policy.classify_exception(exc)
decision = recovery_policy.decide(kind)
# No branch here changes publication_status or public_display_allowed.
```

**Integration status:** Typed error API + offline tests are added, but PR #31's classifier, publication approval, heartbeat, and the live NBA PDF comparison remain independent open work.
