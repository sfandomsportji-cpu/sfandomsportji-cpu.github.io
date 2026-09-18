# SFANDOM Community v1

This directory is the open development area for the SFANDOM community renewal.

## Phase 1
- Replace the current bottom slogan area with a compact fan board.
- Show **10 posts per page** with numbered pagination.
- Keep the existing global navigation, visitor counter, analysis area, and production layout untouched.
- Keep copy short and put the board before decorative features.
- Do **not** include a video lounge or video upload flow in Phase 1.
- Use local preview data only until a protected persistence layer is reviewed.

## Safety gate
- No production credentials, API keys, access tokens, session secrets, private user data, raw moderation evidence, or IP addresses in GitHub.
- No anonymous public write endpoint is connected from the production page in Phase 1.
- Cloud persistence must be reviewed separately for abuse controls, moderation, authentication/rate limiting, and rollback before activation.
- Production merge requires review of the Draft PR and explicit user approval.

## Initial board modules
- HOT TALK
- MATCH CHAT
- FAN PICKS

## Data model
See `db/schema.sql`.

Phase 1 is intentionally board-first. Video and media features remain deferred.
