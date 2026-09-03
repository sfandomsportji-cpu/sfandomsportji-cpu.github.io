(() => {
  'use strict';

  const ROOT_SELECTOR = '[data-sf-visitor-counter]';
  const VALUE_SELECTOR = '[data-sf-visitor-value]';
  const CACHE_KEY = 'sfandom:visitor-counter:last-good:v1';
  const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
  const REQUEST_TIMEOUT_MS = 2500;

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

  async function fetchCount(endpoint) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        mode: 'cors',
        credentials: 'omit',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
        keepalive: true,
        signal: controller.signal
      });

      if (!response.ok) throw new Error(`counter-http-${response.status}`);
      const payload = await response.json();
      const value = Number(payload && payload.displayVisitors);
      if (!isValidCount(value)) throw new Error('counter-invalid-payload');
      return value;
    } finally {
      window.clearTimeout(timer);
    }
  }

  async function init(root) {
    const endpoint = (root.dataset.endpoint || window.SFANDOM_VISITOR_COUNTER_ENDPOINT || '').trim();
    const cached = readCache();

    if (cached !== null) render(root, cached, 'cache');

    if (!endpoint) {
      hideIfEmpty(root);
      return;
    }

    try {
      const value = await fetchCount(endpoint);
      if (render(root, value, 'live')) writeCache(value);
    } catch (_) {
      // Fail closed: keep the last verified value, or remain hidden.
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
