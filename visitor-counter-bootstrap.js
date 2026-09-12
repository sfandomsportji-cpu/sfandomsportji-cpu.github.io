(() => {
  'use strict';

  const COUNTER_SELECTOR = '[data-sf-visitor-counter]';
  const SCRIPT_SELECTOR = 'script[data-sf-counterapi-script]';
  const CSS_SELECTOR = 'link[data-sf-visitor-counter-css]';
  const CSS_HREF = 'visitor-counter.css?v=20260906-header2';
  const COUNTERAPI_SRC = 'https://counterapi.com/c.js?ns=sfandom.com';

  function keepFirstOnly(selector) {
    const nodes = [...document.querySelectorAll(selector)];
    nodes.slice(1).forEach((node) => node.remove());
    return nodes[0] || null;
  }

  function cleanupResidue() {
    keepFirstOnly(COUNTER_SELECTOR);
    keepFirstOnly(SCRIPT_SELECTOR);
    keepFirstOnly(CSS_SELECTOR);
  }

  function ensureStyles() {
    if (document.querySelector(CSS_SELECTOR)) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = CSS_HREF;
    link.dataset.sfVisitorCounterCss = '1';
    document.head.appendChild(link);
  }

  function revealWhenReady(root, value) {
    const showIfReady = () => {
      const digits = (value.textContent || '').replace(/\D/g, '');
      if (!digits) return false;

      const formatted = digits.padStart(6, '0');
      if ((value.textContent || '').trim() !== formatted) value.textContent = formatted;
      root.hidden = false;
      return true;
    };

    if (showIfReady()) return;

    const observer = new MutationObserver(() => {
      if (showIfReady()) observer.disconnect();
    });
    observer.observe(value, { childList: true, subtree: true, characterData: true });

    window.setTimeout(() => observer.disconnect(), 10000);
  }

  function ensureCounterRoot() {
    const existing = document.querySelector(COUNTER_SELECTOR);
    if (existing) {
      const existingValue = existing.querySelector('.sf-visitor-counter__value');
      if (existingValue) revealWhenReady(existing, existingValue);
      return existing;
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
    value.className = 'counterapi sf-visitor-counter__value';
    value.setAttribute('key', 'sfandom-global');
    value.setAttribute('action', 'view');
    value.setAttribute('noIcon', 'true');
    value.setAttribute('noCss', 'true');
    value.setAttribute('noLink', 'true');
    value.setAttribute('noAnim', 'true');
    value.setAttribute('noFormatting', 'true');

    root.append(label, value);

    const cta = header.querySelector('.header-cta');
    if (cta) header.insertBefore(root, cta);
    else header.appendChild(root);

    revealWhenReady(root, value);
    return root;
  }

  function ensureCounterApiScript() {
    if (document.querySelector(SCRIPT_SELECTOR)) return;
    const script = document.createElement('script');
    script.src = COUNTERAPI_SRC;
    script.async = true;
    script.dataset.sfCounterapiScript = '1';
    document.head.appendChild(script);
  }

  function boot() {
    cleanupResidue();
    ensureStyles();
    if (!ensureCounterRoot()) return;
    ensureCounterApiScript();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
