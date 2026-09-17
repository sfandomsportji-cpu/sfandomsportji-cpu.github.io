(() => {
  'use strict';

  const COUNTER_SELECTOR = '[data-sf-visitor-counter]';
  const SCRIPT_SELECTOR = 'script[data-sf-counterapi-script]';
  const CSS_SELECTOR = 'link[data-sf-visitor-counter-css]';
  const CSS_HREF = 'visitor-counter.css?v=20260917-v2';
  const COUNTERAPI_SRC = 'https://counterapi.com/c.js?ns=sfandom.com';
  const COUNTER_CONFIG = Object.freeze({
    key: 'sfandom-global',
    action: 'view',
    behavior: 'view',
    unique: 'false',
    timeline: 'total',
    readOnly: 'false',
    noIcon: 'true',
    noCss: 'true',
    noLink: 'true',
    noAnim: 'true',
    noFormatting: 'true'
  });

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
    const existing = document.querySelector(CSS_SELECTOR);
    if (existing) {
      if (existing.getAttribute('href') !== CSS_HREF) existing.setAttribute('href', CSS_HREF);
      return;
    }
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = CSS_HREF;
    link.dataset.sfVisitorCounterCss = '1';
    document.head.appendChild(link);
  }

  function applyCounterConfig(value) {
    Object.entries(COUNTER_CONFIG).forEach(([name, setting]) => {
      value.setAttribute(name, setting);
    });
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

  function counterMount() {
    const footer = document.querySelector('.footer-v2.home-footer');
    if (!footer) return null;
    return footer.querySelector(':scope > div:first-child') || footer;
  }

  function ensureCounterRoot() {
    const mount = counterMount();
    if (!mount) return null;

    const existing = document.querySelector(COUNTER_SELECTOR);
    if (existing) {
      if (existing.parentElement !== mount) mount.appendChild(existing);
      const existingValue = existing.querySelector('.sf-visitor-counter__value');
      if (existingValue) {
        applyCounterConfig(existingValue);
        revealWhenReady(existing, existingValue);
      }
      return existing;
    }

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
    applyCounterConfig(value);

    root.append(label, value);
    mount.appendChild(root);

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
