# SFANDOM Blogger Bridge — Sandbox

Status: ISOLATED / NOT CONNECTED TO PRODUCTION

This directory is an experimental bridge sandbox. Nothing here is referenced by `index.html`, `content.html`, or any production page.

## Safety rules

1. `main` is never modified by the bridge test.
2. Feed fetch failure means **no publish**.
3. Parse/validation failure means **no publish**.
4. Empty feed means **no publish**.
5. Oversized feed means **no publish**.
6. Existing `current.json` is never deleted before a replacement passes validation.
7. First-stage output contains text/meta only; remote HTML is not injected into SFANDOM.
8. Production pages must never depend on Blogger being online at request time.

## Intended flow

Blogger public feed -> isolated fetch -> validation -> temporary JSON -> atomic replacement -> later, after approval, SFANDOM reads only the validated static JSON.

## Phase 1 acceptance criteria

- 3 consecutive valid syncs
- malformed XML rejected
- empty feed rejected
- timeout/network failure leaves existing data untouched
- oversized response rejected
- no `<script>`, `<style>`, inline event handler, or remote HTML is passed to the site
- no production file changes

Only after the above passes should a limited production integration be proposed.
