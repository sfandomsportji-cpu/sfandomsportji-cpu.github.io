# SFANDOM LIVE chat worker

This folder contains the real-time backend for `live.html`.

## Current state

- `live.html` works in browser test mode while its `sfandom-chat-endpoint` meta value is empty.
- After this Worker is deployed, set that meta value to the deployed Worker origin, for example `https://sfandom-live-chat.<account>.workers.dev`.
- The browser client then switches automatically from local test mode to WebSocket LIVE mode.

## Deploy

```bash
cd cloudflare-chat-worker
npm install
npx wrangler login
npm run deploy
```

After deployment, copy the Worker origin and set it in `live.html`:

```html
<meta name="sfandom-chat-endpoint" content="https://YOUR-WORKER-ORIGIN" />
```

## v0.1 behavior

- One public room: `main`
- Guest nickname only; no email or account required
- Text messages up to 300 characters
- Topic tags: GENERAL, MLB, KBO, NBA, FOOTBALL
- 2.5 second server-side send rate limit
- Repeated-message protection
- Maximum one HTTP(S) link per message
- Last 100 messages sent as history to new connections
- Up to 500 messages retained in Durable Object SQLite storage
- WebSocket Hibernation API for idle connections
- Browser origins restricted to SFANDOM, the GitHub Pages host, and localhost development

Before a full public launch, add moderator authentication, server-side reports/blocks, and a stronger anti-abuse layer.
