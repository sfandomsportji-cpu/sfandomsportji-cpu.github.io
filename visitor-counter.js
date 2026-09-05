(() => {
  'use strict';

  const ROOT_SELECTOR = '[data-sf-visitor-counter]';
  const VALUE_SELECTOR = '[data-sf-visitor-value]';
  const CACHE_KEY = 'sfandom:visitor-counter:last-good:v1';
  const FALLBACK_SEEN_KEY = 'sfandom:visitor-counter:fallback-seen:v1';
  const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
  const REQUEST_TIMEOUT_MS = 2500;
  const FALLBACK_TIMEOUT_MS = 2500;
  const FALLBACK_BASE = 'https://countapi.mileshilliard.com/api/v1';
  const FALLBACK_KEY = 'sfandom-prod-unique-visitors-20260906-b7c1f4d9';

  const formatter = new Intl.NumberFormat('en-US');

  function isValidCount(value) {
    return Number.isSafeInteger(value) && value >= 0;
  }

  function readCache() {
    try {
      const raw = window.localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      const cached = JSON.parse(raw);
      if (!cached || !isValidCount(cached.value) || !Number.isFinite(cached.savedAt)) return null;
      if (Date.now() - cached.savedAt > CACHE_MAX_AGE_MS) return null;
      return cached.value;
    } catch (_) {
      return null;
    }
  }

  function writeCache(value) {
    try {
      window.localStorage.setItem(CACHE_KEY, JSON.stringify({ value, savedAt: Date.now() }));
    } catch (_) {
      // Cache is optional. Counting never depends on browser storage.
    }
  }

  function render(root, value, source) {
    const target = root.querySelector(VALUE_SELECTOR);
    if (!target || !isValidCount(value)) return false;

    target.textContent = formatter.format(value);
    root.dataset.counterSource = source;
    root.hidden = false;
    return true;
  }

  function hideIfEmpty(root) {
    const target = root.querySelector(VALUE_SELECTOR);
    if (!target || !target.textContent.trim()) root.hidden = true;
  }

  async function fetchWithTimeout(url, options, timeoutMs) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeoutMs);

    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      window.clearTimeout(timer);
    }
  }

  async function fetchCount(endpoint) {
    const response = await fetchWithTimeout(endpoint, {
      method: 'POST',
      mode: 'cors',
      credentials: 'omit',
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      keepalive: true
    }, REQUEST_TIMEOUT_MS);

    if (!response.ok) throw new Error(`counter-http-${response.status}`);
    const payload = await response.json();
    const value = Number(payload && payload.displayVisitors);
    if (!isValidCount(value)) throw new Error('counter-invalid-payload');
    return value;
  }

  function hasFallbackSeen() {
    try {
      return window.localStorage.getItem(FALLBACK_SEEN_KEY) === '1';
    } catch (_) {
      return false;
    }
  }

  function markFallbackSeen() {
    try {
      window.localStorage.setItem(FALLBACK_SEEN_KEY, '1');
    } catch (_) {
      // If storage is blocked, fallback degrades to page-view counting.
    }
  }

  async function fetchFallbackCount() {
    let action = hasFallbackSeen() ? 'get' : 'hit';
    let url = `${FALLBACK_BASE}/${action}/${FALLBACK_KEY}`;
    let response = await fetchWithTimeout(url, {
      method: 'GET',
      mode: 'cors',
      credentials: 'omit',
      cache: 'no-store',
      headers: { Accept: 'application/json' }
    }, FALLBACK_TIMEOUT_MS);

    // A browser may remember it was counted while the public counter was reset.
    // Recreate the key safely if a read returns 404.
    if (response.status === 404 && action === 'get') {
      action = 'hit';
      url = `${FALLBACK_BASE}/${action}/${FALLBACK_KEY}`;
      response = await fetchWithTimeout(url, {
        method: 'GET',
        mode: 'cors',
        credentials: 'omit',
        cache: 'no-store',
        headers: { Accept: 'application/json' }
      }, FALLBACK_TIMEOUT_MS);
    }

    if (!response.ok) throw new Error(`counter-fallback-http-${response.status}`);
    const payload = await response.json();
    const value = Number(payload && payload.value);
    if (!isValidCount(value)) throw new Error('counter-fallback-invalid-payload');
    if (action === 'hit') markFallbackSeen();
    return value;
  }

  async function init(root) {
    const endpoint = (root.dataset.endpoint || window.SFANDOM_VISITOR_COUNTER_ENDPOINT || '').trim();
    const cached = readCache();

    if (cached !== null) render(root, cached, 'cache');

    if (endpoint) {
      try {
        const value = await fetchCount(endpoint);
        if (render(root, value, 'live')) writeCache(value);
        return;
      } catch (_) {
        // Primary SFANDOM Worker unavailable: use the isolated public fallback below.
      }
    }

    try {
      const value = await fetchFallbackCount();
      if (render(root, value, 'fallback')) writeCache(value);
    } catch (_) {
      // Preserve the last verified value if available; otherwise stay hidden.
      hideIfEmpty(root);
    }
  }

  function boot() {
    document.querySelectorAll(ROOT_SELECTOR).forEach((root) => {
      init(root);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
