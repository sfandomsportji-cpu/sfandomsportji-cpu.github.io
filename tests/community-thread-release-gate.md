# SFANDOM Community — release gate (2026-10-10)

Status: FEATURE BRANCH ONLY. Do not merge to `main` until browser tests pass. Preserve approved site design.

## Expected behavior
- Any published post supports comments.
- A comment can reply to ANY published comment, including reply-to-reply-to-reply (no depth cutoff).
- Reply targets must exist, be published, and belong to the SAME post.
- UI flattens display indentation after 5 levels but preserves actual parent-child threading at unlimited depths.
- Text is rendered using `textContent`; never display user-supplied markup as HTML.
- Reports are private: public users cannot query `community_reports`.
- Publishing comments and reports is rate limited on the server.
- Old post/QUICK TALK flows and approved layout must remain unchanged.

## Read-only checks completed
- GitHub `main` commit remains `7c490bd2131d33ee3327ab6d4d29402812b56d76`.
- `comments.parent_id` self-referencing foreign key exists.
- `comments.post_id` references `posts.id`.
- RLS is active; unauthenticated SELECT on `comments` succeeds and exposes 0 rows (table currently empty).
- Edge Function `community-interact` v2 accepts nested parents without first-level-only restriction.
- JS and CSS are isolated on the feature branch and only loaded for `/community/` by the updated builder.

## Browser acceptance tests — NOT YET PERFORMED
- Open main post A and publish comment B.
- Reply C to B; reply D to C; reply E to D; verify order and hierarchy after refresh.
- Reply from two browsers with different nicknames; check near-simultaneous replies.
- Verify 15-second and 10-minute server rate limits.
- Create a report on a comment and check reports are not visible to the public.
- Test thread pagination after 100+ comments.
- Verify mobile 390px screen width, keyboard and accessibility.
- Confirm no regression: new post, channel filters, game threads, QUICK TALK.
- Confirm CSS matches approved site in 1280 / 1024 / 820 / 390 widths.
- Confirm all deployed static pages still work after rebuilding.
- Have a verified moderation workflow before opening publicly.

No production cutover without these tests and explicit deployment approval.

## Mobile stability hardening — 2026-10-10
- Fixed horizontal flex bug: reply panel now mounts INSIDE .post-body, not alongside it in .post.
- Added bounded 10px indentation at <=359px and 18px indentation at 360–600px. The actual reply hierarchy remains unlimited.
- Scoped width, wrapping, flex minimum, and form styles to prevent long names/text and iOS input zoom from breaking narrow screens.
- First expansion fetches only 40 comments; subsequent pages use a stable (created_at, id) cursor, not an offset.
- Builds each visible comment batch in a DocumentFragment to avoid repeated relayout.
- Local synthetic layout fixture (reproducing relevant selectors and 40 deep replies): Chromium horizontal-overflow checks passed at 320, 360, 375, 390, 414, 600, 760, 1024, 1280px.
- Source-level syntax checks: new community script parses, scoped CSS braces balance, GitHub main unchanged.
- NOT YET VERIFIED ON LIVE SITE: physical phones, interactions with full original CSS, measured latency on low-end phones, real Edge Function comment tests, >100-comment paging, high concurrency, accessibility. These remain release blockers.
