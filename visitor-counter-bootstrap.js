(() => {
  'use strict';

  const COUNTER_SELECTOR = '[data-sf-visitor-counter]';
  const CSS_SELECTOR = 'link[data-sf-visitor-counter-css]';
  const CSS_HREF = 'visitor-counter.css?v=20260917-contain1';
  const COUNTER_ENDPOINT = 'https://counterapi.com/api/sfandom.com/view/sfandom-global';

  function keepFirstOnly(selector) {
    const nodes = [...document.querySelectorAll(selector)];
    nodes.slice(1).forEach((node) => node.remove());
    return nodes[0] || null;
  }

  function cleanupResidue() {
    keepFirstOnly(COUNTER_SELECTOR);
    keepFirstOnly(CSS_SELECTOR);
    document.querySelectorAll('script[data-sf-counterapi-script]').forEach((node) => node.remove());
  }

  function ensureStyles() {
    if (document.querySelector(CSS_SELECTOR)) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = CSS_HREF;
    link.dataset.sfVisitorCounterCss = '1';
    document.head.appendChild(link);
  }

  function showCounter(root, value, count) {
    const numeric = Number(count);
    if (!Number.isFinite(numeric)) return false;
    value.textContent = String(Math.trunc(numeric)).padStart(6, '0');
    root.hidden = false;
    return true;
  }

  async function incrementCounter(root, value) {
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
      console.warn('[SFANDOM] visitor counter unavailable', error);
    }
  }

  function ensureCounterRoot() {
    const existing = document.querySelector(COUNTER_SELECTOR);
    if (existing) {
      let existingValue = existing.querySelector('.sf-visitor-counter__value');
      if (!existingValue) {
        existingValue = document.createElement('span');
        existingValue.className = 'sf-visitor-counter__value';
        existing.appendChild(existingValue);
      }
      existingValue.classList.remove('counterapi');
      existingValue.removeAttribute('key');
      existingValue.removeAttribute('action');
      existingValue.removeAttribute('behavior');
      existingValue.removeAttribute('unique');
      existingValue.removeAttribute('timeline');
      existingValue.removeAttribute('readOnly');
      existing.hidden = true;
      return { root: existing, value: existingValue };
    }

    const header = document.querySelector('.site-header.home-header');
    if (!header) return null;

    const root = document.createElement('div');
    root.className = 'sf-visitor-counter';
    root.dataset.sfVisitorCounter = '';
    root.setAttribute('aria-label', 'SFANDOM visitors');
    root.setAttribute('aria-live', 'polite');
    root.hidden = true;

    const label = document.createElement('span');
    label.className = 'sf-visitor-counter__label';
    label.textContent = 'VISITORS';

    const value = document.createElement('span');
    value.className = 'sf-visitor-counter__value';

    root.append(label, value);

    const brand = header.querySelector('.brand');
    if (brand) brand.insertAdjacentElement('afterend', root);
    else header.prepend(root);

    return { root, value };
  }

  function boot() {
    cleanupResidue();
    ensureStyles();
    const counter = ensureCounterRoot();
    if (!counter) return;
    incrementCounter(counter.root, counter.value);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
