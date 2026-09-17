(() => {
  'use strict';

  const COUNTER_SELECTOR = '[data-sf-visitor-counter]';
  const CSS_SELECTOR = 'link[data-sf-visitor-counter-css]';
  const CSS_HREF = 'visitor-counter.css?v=20260917-position3';
  const COUNTER_ENDPOINT = 'https://counterapi.com/api/sfandom.com/view/sfandom-global';

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

    const value = root.querySelector('.sf-visitor-counter__value');
    return value ? { root, value } : null;
  }

  async function boot() {
    ensureStyles();
    const counter = ensureCounter();
    if (!counter) return;

    counter.root.hidden = false;

    try {
      const response = await fetch(COUNTER_ENDPOINT, { cache: 'no-store' });
      const data = await response.json();
      const numeric = Number(data && data.value);
      if (Number.isFinite(numeric)) {
        counter.value.textContent = String(Math.trunc(numeric)).padStart(6, '0');
      }
    } catch (_) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
