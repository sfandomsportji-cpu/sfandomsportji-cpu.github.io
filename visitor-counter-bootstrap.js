(() => {
  'use strict';

  if (window.__SFANDOM_VISITOR_COUNTER_RUNNING__) return;
  window.__SFANDOM_VISITOR_COUNTER_RUNNING__ = true;

  const COUNTER_SELECTOR = '[data-sf-visitor-counter]';
  const CSS_SELECTOR = 'link[data-sf-visitor-counter-css]';
  const CSS_HREF = 'visitor-counter.css?v=20260917-position3';
  const COUNTER_ENDPOINT = 'https://counterapi.com/api/sfandom.com/view/sfandom-global';
  const DISPLAY_BUCKET = 50;

  function ensureStyles() {
    if (document.querySelector(CSS_SELECTOR)) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = CSS_HREF;
    link.dataset.sfVisitorCounterCss = '1';
    document.head.appendChild(link);
  }

  function formatApproximateCount(count) {
    const numeric = Number(count);
    if (!Number.isFinite(numeric)) return null;
    const whole = Math.max(0, Math.trunc(numeric));
    const bucket = Math.floor(whole / DISPLAY_BUCKET) * DISPLAY_BUCKET;
    return `${bucket}+`;
  }

  function setStatus(root, status) {
    const label = root.querySelector('.sf-visitor-counter__label');
    if (label) label.textContent = `VISITORS · ${status}`;
  }

  function showCounter(root, value, count) {
    const approximate = formatApproximateCount(count);
    if (!approximate) return false;

    value.textContent = approximate;
    value.dataset.rawCount = String(Math.trunc(Number(count)));
    root.dataset.counterStatus = 'live';
    root.setAttribute('aria-label', 'SFANDOM visitor counter live');
    setStatus(root, 'LIVE');
    root.hidden = false;
    return true;
  }

  async function loadCounter(root, value) {
    try {
      const response = await fetch(COUNTER_ENDPOINT, {
        method: 'GET',
        mode: 'cors',
        cache: 'no-store',
        credentials: 'omit'
      });
      if (!response.ok) throw new Error(`CounterAPI ${response.status}`);
      const data = await response.json();
      if (!showCounter(root, value, data && data.value)) throw new Error('CounterAPI invalid value');
    } catch (error) {
      root.dataset.counterStatus = 'off';
      root.setAttribute('aria-label', 'SFANDOM visitor counter unavailable');
      setStatus(root, 'OFF');
      root.hidden = false;
      value.textContent = '—';
      console.warn('[SFANDOM] visitor counter unavailable', error);
    }
  }

  function getCounterRoot() {
    const existing = document.querySelector(COUNTER_SELECTOR);
    if (existing) {
      let label = existing.querySelector('.sf-visitor-counter__label');
      if (!label) {
        label = document.createElement('span');
        label.className = 'sf-visitor-counter__label';
        existing.prepend(label);
      }

      let value = existing.querySelector('.sf-visitor-counter__value');
      if (!value) {
        value = document.createElement('span');
        value.className = 'sf-visitor-counter__value';
        existing.appendChild(value);
      }

      label.textContent = 'VISITORS · CHECK';
      existing.hidden = true;
      return { root: existing, value };
    }

    const header = document.querySelector('.site-header.home-header');
    if (!header) return null;

    const root = document.createElement('div');
    root.className = 'sf-visitor-counter';
    root.dataset.sfVisitorCounter = '';
    root.setAttribute('aria-label', 'SFANDOM visitor counter checking');
    root.setAttribute('aria-live', 'polite');
    root.hidden = true;

    const label = document.createElement('span');
    label.className = 'sf-visitor-counter__label';
    label.textContent = 'VISITORS · CHECK';

    const value = document.createElement('span');
    value.className = 'sf-visitor-counter__value';

    root.append(label, value);

    const brand = header.querySelector('.brand');
    if (brand) brand.insertAdjacentElement('afterend', root);
    else header.prepend(root);

    return { root, value };
  }

  function boot() {
    ensureStyles();
    const counter = getCounterRoot();
    if (!counter) return;
    loadCounter(counter.root, counter.value);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
