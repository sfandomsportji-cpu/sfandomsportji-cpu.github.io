(() => {
  'use strict';

  const ROOT_SELECTOR = '[data-sf-visitor-counter]';
  const VALUE_SELECTOR = '[data-sf-visitor-value]';
  const CACHE_KEY = 'sfandom:visitor-counter:last-good:v3';
  const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
  const REQUEST_TIMEOUT_MS = 5000;

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

  function fetchCount(endpoint) {
    return new Promise((resolve, reject) => {
      const callbackName = `sfandomCounterCallback${Date.now()}${Math.floor(Math.random() * 100000)}`;
      const script = document.createElement('script');
      let settled = false;

      const cleanup = () => {
        window.clearTimeout(timer);
        script.remove();
        try {
          delete window[callbackName];
        } catch (_) {
          window[callbackName] = undefined;
        }
      };

      const finish = (error, value) => {
        if (settled) return;
        settled = true;
        cleanup();
        if (error) reject(error);
        else resolve(value);
      };

      window[callbackName] = (payload) => {
        const rawValue = payload && (payload.displayVisitors ?? payload.value);
        const value = Number(rawValue);
        if (!isValidCount(value)) {
          finish(new Error('counter-invalid-payload'));
          return;
        }
        finish(null, value);
      };

      let url;
      try {
        url = new URL(endpoint, window.location.href);
      } catch (_) {
        finish(new Error('counter-invalid-endpoint'));
        return;
      }

      url.searchParams.set('callback', callbackName);
      url.searchParams.set('_', String(Date.now()));

      script.src = url.toString();
      script.async = true;
      script.referrerPolicy = 'no-referrer-when-downgrade';
      script.onerror = () => finish(new Error('counter-script-error'));

      const timer = window.setTimeout(() => {
        finish(new Error('counter-timeout'));
      }, REQUEST_TIMEOUT_MS);

      document.head.appendChild(script);
    });
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
