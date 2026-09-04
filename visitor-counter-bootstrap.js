(() => {
  'use strict';

  const COUNTER_SELECTOR = '[data-sf-visitor-counter]';
  const ENDPOINT = 'https://counter.sfandom.com/v1/visit';
  const CSS_HREF = 'visitor-counter.css?v=20260904-1';

  function ensureStyles() {
    if (document.querySelector('link[data-sf-visitor-counter-css]')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = CSS_HREF;
    link.dataset.sfVisitorCounterCss = '1';
    document.head.appendChild(link);
  }

  function ensureCounterRoot() {
    const existing = document.querySelector(COUNTER_SELECTOR);
    if (existing) return existing;

    const footer = document.querySelector('.footer-v2.home-footer, footer');
    if (!footer) return null;

    const root = document.createElement('div');
    root.className = 'sf-visitor-counter';
    root.dataset.sfVisitorCounter = '';
    root.dataset.endpoint = ENDPOINT;
    root.setAttribute('aria-label', 'SFANDOM visitors');
    root.setAttribute('aria-live', 'polite');
    root.hidden = true;

    const label = document.createElement('span');
    label.className = 'sf-visitor-counter__label';
    label.textContent = 'VISITORS';

    const value = document.createElement('strong');
    value.className = 'sf-visitor-counter__value';
    value.dataset.sfVisitorValue = '';

    root.append(label, value);

    const copyright = footer.querySelector('small');
    if (copyright) footer.insertBefore(root, copyright);
    else footer.appendChild(root);

    return root;
  }

  function boot() {
    ensureStyles();
    if (!ensureCounterRoot()) return;
    import('./visitor-counter.js?v=20260904-1').catch(() => {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
