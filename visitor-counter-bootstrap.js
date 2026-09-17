(() => {
  'use strict';

  // Prevent duplicate script execution only. This does not deduplicate visits.
  if (window.__SFANDOM_COUNTER_ACTIVE__) return;
  window.__SFANDOM_COUNTER_ACTIVE__ = true;

  const COUNTER_SELECTOR = '[data-sf-visitor-counter]';
  const CSS_SELECTOR = 'link[data-sf-visitor-counter-css]';
  const CSS_HREF = 'visitor-counter.css?v=20260917-position3';
  const COUNTER_ENDPOINT = 'https://counterapi.com/api/sfandom.com/view/sfandom-global?readOnly=false&unique=false';

  function ensureStyles() {
    if (document.querySelector(CSS_SELECTOR)) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = CSS_HREF;
    link.dataset.sfVisitorCounterCss = '1';
    document.head.appendChild(link);
  }

  function ensureCounter() {
    let root = document.querySelector(COUNTER_SELECTOR);
    if (!root) {
      const header = document.querySelector('.site-header.home-header');
      if (!header) return null;

      root = document.createElement('div');
      root.className = 'sf-visitor-counter';
      root.dataset.sfVisitorCounter = '';
      root.setAttribute('aria-label', 'SFANDOM visitors');
      root.setAttribute('aria-live', 'polite');

      const label = document.createElement('span');
      label.className = 'sf-visitor-counter__label';
      label.textContent = 'VISITORS';

      const value = document.createElement('span');
      value.className = 'sf-visitor-counter__value';
      root.append(label, value);

      const brand = header.querySelector('.brand');
      if (brand) brand.insertAdjacentElement('afterend', root);
      else header.prepend(root);
    }

    let value = root.querySelector('.sf-visitor-counter__value');
    if (!value) {
      value = document.createElement('span');
      value.className = 'sf-visitor-counter__value';
      root.appendChild(value);
    }

    return { root, value };
  }

  async function boot() {
    ensureStyles();
    const counter = ensureCounter();
    if (!counter) return;

    counter.root.hidden = false;
    counter.value.textContent = '...';

    try {
      const response = await fetch(COUNTER_ENDPOINT, {
        method: 'GET',
        mode: 'cors',
        cache: 'no-store',
        credentials: 'omit'
      });
      if (!response.ok) throw new Error(`CounterAPI ${response.status}`);

      const data = await response.json();
      const numeric = Number(data && data.value);
      if (!Number.isFinite(numeric)) throw new Error('CounterAPI invalid value');

      counter.value.textContent = String(Math.trunc(numeric)).padStart(6, '0');
    } catch (error) {
      counter.value.textContent = 'ERROR';
      console.warn('[SFANDOM] visitor counter unavailable', error);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
