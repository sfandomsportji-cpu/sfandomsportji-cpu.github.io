# SFANDOM Visitor Counter

This counter is intentionally isolated from the static GitHub Pages site.

## Design

- Static site: `visitor-counter.js` + `visitor-counter.css`
- Counter API: Worker endpoint
- Persistence: one Durable Object instance
- No browser-side `+1`
- No raw IP storage
- No cookie requirement
- Bot-like user agents are excluded from counting
- Counter failure never blocks the main site
- A cached last-known-good display value may be shown; the cache never increments the counter

## Metrics

- `actualTracked`: approximate unique visitors recorded since the counter starts
- `pageViews`: non-bot page-load events
- `baseline`: optional display-only baseline configured on the Worker
- `displayVisitors`: `baseline + actualTracked`

`DISPLAY_BASELINE` defaults to `0`. If a historical display baseline is ever used, keep it separate from `actualTracked`; do not describe an unverified baseline as historical measured traffic.

## Privacy model

The Worker reads the request IP, user agent, and language only long enough to create an HMAC digest. Raw request attributes are not stored. The HMAC secret must be configured in the deployment platform's secret manager and must never be committed to Git.

The unique-visitor value is approximate. A changed IP/user-agent/language combination can count as a new visitor, while multiple people behind the same network/device signature can occasionally collapse into one.

## Deployment setup

1. Copy `wrangler.toml.example` to a private/local `wrangler.toml` or equivalent deployment configuration.
2. Bind a Durable Object named `COUNTER` to class `VisitorCounter`.
3. Add a strong `VISITOR_HASH_SECRET` through the platform secret manager.
4. Keep `ALLOWED_ORIGINS` restricted to the production SFANDOM origins.
5. Deploy the Worker to a stable HTTPS endpoint such as `https://counter.sfandom.com`.
6. Verify `GET /health`, then `GET /v1/count`, then `POST /v1/visit` from the production origin.

## Homepage integration patch

Only after the Worker endpoint is verified, add these three isolated pieces to `index.html`.

In `<head>`:

```html
<link rel="stylesheet" href="visitor-counter.css?v=1" />
```

Inside the footer, without changing existing footer classes:

```html
<div
  class="sf-visitor-counter"
  data-sf-visitor-counter
  data-endpoint="https://counter.sfandom.com/v1/visit"
  aria-label="SFANDOM visitors"
  aria-live="polite"
  hidden
>
  <span class="sf-visitor-counter__label">VISITORS</span>
  <strong class="sf-visitor-counter__value" data-sf-visitor-value></strong>
</div>
```

Immediately before `</body>`:

```html
<script defer src="visitor-counter.js?v=1"></script>
```

## Failure behavior

- API timeout: keep last known good value if available; otherwise remain hidden.
- Invalid API response: same behavior.
- `localStorage` unavailable: live API still works; no cache is used.
- Worker unavailable: main SFANDOM content remains unaffected.

Do not merge a live endpoint into `index.html` until the Worker itself has been deployed and verified.
