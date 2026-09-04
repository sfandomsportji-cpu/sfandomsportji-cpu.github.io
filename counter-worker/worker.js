const DEFAULT_ALLOWED_ORIGINS = ['https://sfandom.com', 'https://www.sfandom.com'];
const BOT_UA = /(bot|crawler|spider|slurp|bingpreview|facebookexternalhit|headless|lighthouse|pagespeed|curl|wget)/i;

function json(body, status = 200, origin = '') {
  const headers = {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store, max-age=0',
    'x-content-type-options': 'nosniff'
  };

  if (origin) {
    headers['access-control-allow-origin'] = origin;
    headers['vary'] = 'Origin';
  }

  return new Response(JSON.stringify(body), { status, headers });
}

function parseOrigins(env) {
  const raw = String(env.ALLOWED_ORIGINS || '').trim();
  if (!raw) return DEFAULT_ALLOWED_ORIGINS;
  return raw.split(',').map((value) => value.trim()).filter(Boolean);
}

function allowedOrigin(request, env) {
  const origin = request.headers.get('Origin') || '';
  if (!origin) return '';
  return parseOrigins(env).includes(origin) ? origin : null;
}

function nonNegativeInteger(value, fallback = 0) {
  const parsed = Number.parseInt(String(value ?? ''), 10);
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : fallback;
}

async function hmacHex(secret, value) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signature = await crypto.subtle.sign('HMAC', key, encoder.encode(value));
  return [...new Uint8Array(signature)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

async function anonymousFingerprint(request, env) {
  if (!env.VISITOR_HASH_SECRET) throw new Error('missing-hash-secret');

  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  const userAgent = (request.headers.get('User-Agent') || 'unknown').slice(0, 256);
  const language = (request.headers.get('Accept-Language') || 'unknown').slice(0, 96);

  // Raw request attributes are never persisted. Only this HMAC digest reaches storage.
  return hmacHex(env.VISITOR_HASH_SECRET, `${ip}\n${userAgent}\n${language}`);
}

function isBot(request) {
  return BOT_UA.test(request.headers.get('User-Agent') || '');
}

async function callCounter(env, payload) {
  const id = env.COUNTER.idFromName('sfandom-global');
  const stub = env.COUNTER.get(id);
  const response = await stub.fetch('https://counter.internal/event', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) throw new Error(`durable-object-${response.status}`);
  return response.json();
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = allowedOrigin(request, env);

    if (origin === null) return json({ ok: false, error: 'origin-not-allowed' }, 403);

    if (request.method === 'OPTIONS') {
      const headers = {
        'access-control-allow-methods': 'GET, POST, OPTIONS',
        'access-control-allow-headers': 'Content-Type',
        'access-control-max-age': '86400',
        'cache-control': 'no-store'
      };
      if (origin) {
        headers['access-control-allow-origin'] = origin;
        headers['vary'] = 'Origin';
      }
      return new Response(null, { status: 204, headers });
    }

    if (url.pathname === '/health') {
      return json({ ok: true, service: 'sfandom-visitor-counter' }, 200, origin || '');
    }

    if (url.pathname === '/v1/count' && request.method === 'GET') {
      try {
        const counts = await callCounter(env, { type: 'read' });
        const baseline = nonNegativeInteger(env.DISPLAY_BASELINE, 0);
        return json({
          ok: true,
          displayVisitors: baseline + counts.actualTracked,
          actualTracked: counts.actualTracked,
          pageViews: counts.pageViews,
          baseline
        }, 200, origin || '');
      } catch (_) {
        return json({ ok: false, error: 'counter-unavailable' }, 503, origin || '');
      }
    }

    if (url.pathname === '/v1/visit' && request.method === 'POST') {
      try {
        const bot = isBot(request);
        const fingerprint = bot ? null : await anonymousFingerprint(request, env);
        const counts = await callCounter(env, {
          type: bot ? 'read' : 'visit',
          fingerprint
        });
        const baseline = nonNegativeInteger(env.DISPLAY_BASELINE, 0);

        return json({
          ok: true,
          counted: !bot,
          displayVisitors: baseline + counts.actualTracked,
          actualTracked: counts.actualTracked,
          pageViews: counts.pageViews,
          baseline
        }, 200, origin || '');
      } catch (_) {
        return json({ ok: false, error: 'counter-unavailable' }, 503, origin || '');
      }
    }

    return json({ ok: false, error: 'not-found' }, 404, origin || '');
  }
};

export class VisitorCounter {
  constructor(state) {
    this.state = state;
  }

  async fetch(request) {
    if (request.method !== 'POST') return json({ ok: false }, 405);

    let payload;
    try {
      payload = await request.json();
    } catch (_) {
      return json({ ok: false }, 400);
    }

    if (payload.type === 'read') {
      const actualTracked = nonNegativeInteger(await this.state.storage.get('actualTracked'), 0);
      const pageViews = nonNegativeInteger(await this.state.storage.get('pageViews'), 0);
      return json({ ok: true, actualTracked, pageViews });
    }

    if (payload.type !== 'visit' || typeof payload.fingerprint !== 'string' || payload.fingerprint.length < 32) {
      return json({ ok: false }, 400);
    }

    let result = { actualTracked: 0, pageViews: 0 };

    await this.state.storage.transaction(async (txn) => {
      const seenKey = `seen:${payload.fingerprint}`;
      const [seen, storedVisitors, storedPageViews] = await Promise.all([
        txn.get(seenKey),
        txn.get('actualTracked'),
        txn.get('pageViews')
      ]);

      let actualTracked = nonNegativeInteger(storedVisitors, 0);
      const pageViews = nonNegativeInteger(storedPageViews, 0) + 1;

      await txn.put('pageViews', pageViews);

      if (!seen) {
        actualTracked += 1;
        await txn.put(seenKey, 1);
        await txn.put('actualTracked', actualTracked);
      }

      result = { actualTracked, pageViews };
    });

    return json({ ok: true, ...result });
  }
}
