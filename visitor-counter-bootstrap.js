(() => {
  'use strict';

  const COUNTER_SELECTOR = '[data-sf-visitor-counter]';
  const CSS_SELECTOR = 'link[data-sf-visitor-counter-css]';
  const CSS_HREF = 'visitor-counter.css?v=20260917-position3';

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
      if (!header) return;

      root = document.createElement('div');
      root.className = 'sf-visitor-counter';
      root.dataset.sfVisitorCounter = '';
      root.setAttribute('aria-label', 'SFANDOM visitors');

      const label = document.createElement('span');
      label.className = 'sf-visitor-counter__label';
      label.textContent = 'VISITORS';

      const value = document.createElement('span');
      value.className = 'sf-visitor-counter__value';
      value.textContent = '—';

      root.append(label, value);

      const brand = header.querySelector('.brand');
      if (brand) brand.insertAdjacentElement('afterend', root);
      else header.prepend(root);
    }

    const value = root.querySelector('.sf-visitor-counter__value');
    if (value && !value.textContent.trim()) value.textContent = '—';
    root.hidden = false;
  }

  function boot() {
    ensureStyles();
    ensureCounter();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
