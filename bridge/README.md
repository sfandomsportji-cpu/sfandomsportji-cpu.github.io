# SFANDOM Blogger Bridge — Static v2

Status: production candidate / isolated static route.

## Runtime principle

Blogger is used only at build time. Visitors never wait for Blogger, GitHub API, Raw GitHub, or a JSON fetch. The published `/blog/` pages contain the article HTML in the first response.

## Pipeline

1. Fetch the public Blogger Atom/RSS feed over HTTPS.
2. Require the `SFANDOM-SYNC` label by default.
3. Reject malformed, empty, oversized, duplicate, or unsafe feed data.
4. Sanitize Blogger HTML with an allow-list. Scripts, styles, iframes, inline event handlers, and unsafe URLs are removed.
5. Atomically replace `bridge/data/current.json` only after validation passes.
6. Render static `/blog/YYYY/MM/slug/index.html` pages plus `/blog/index.html`.
7. Validate generated HTML and reject runtime fetch/API dependencies.
8. Commit only the validated generated data/pages.

## Failure behavior

- Missing feed configuration: safe no-op.
- Network/timeout/XML/validation error: build stops; no publish.
- Blogger deletion does not automatically delete old static article pages.
- Existing SFANDOM home/content/analysis pages are not rewritten by the bridge.

## GitHub configuration

Repository variable required for live sync:

- `SFANDOM_BLOGGER_FEED` — public HTTPS Atom/RSS feed URL.

Optional:

- `SFANDOM_REQUIRED_LABEL` — defaults to `SFANDOM-SYNC`.

The scheduled workflow runs hourly at minute 17. Until the feed variable is configured, it exits without changing the site.
