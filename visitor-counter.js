(() => {
  'use strict';

  if (window.__SFANDOM_VISITOR_COUNTER__) return;
  window.__SFANDOM_VISITOR_COUNTER__ = true;

  const header = document.querySelector('.site-header.home-header');
  const brand = header?.querySelector('.brand');
  if (!header || !brand) return;

  const root = document.createElement('div');
  root.className = 'sf-basic-counter';
  root.setAttribute('aria-label', 'SFANDOM visitors');

  const label = document.createElement('span');
  label.textContent = 'VISITORS';

  const value = document.createElement('b');
  const CACHE_KEY = 'sfandom-visitor-counter-supabase-v1';
  const SUPABASE_URL = 'https://yyjjgxzbqvlpatccbpxm.supabase.co';
  const SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_ABoOVvaUzGuVPBryIpY02w_tTcdt-Q4';
  const RPC_ENDPOINT = SUPABASE_URL + '/rest/v1/rpc/increment_homepage_visitors';

  const parseCount = (raw) => {
    const text = String(raw ?? '').trim();
    if (!/^\d+$/.test(text)) throw new Error('invalid counter value');
    return BigInt(text);
  };

  let cached = null;
  try {
    const saved = localStorage.getItem(CACHE_KEY);
    if (saved !== null) cached = parseCount(saved);
  } catch (_) {}

  value.textContent = cached === null ? '------' : String(cached).padStart(6, '0');
  root.append(label, value);
  brand.insertAdjacentElement('afterend', root);

  fetch(RPC_ENDPOINT, {
    method: 'POST',
    mode: 'cors',
    cache: 'no-store',
    credentials: 'omit',
    headers: {
      apikey: SUPABASE_PUBLISHABLE_KEY,
      'Content-Type': 'application/json'
    },
    body: '{}'
  })
    .then((response) => {
      if (!response.ok) throw new Error('counter ' + response.status);
      return response.json();
    })
    .then((data) => {
      const serverCount = parseCount(data);
      value.textContent = String(serverCount).padStart(6, '0');
      try { localStorage.setItem(CACHE_KEY, String(serverCount)); } catch (_) {}
    })
    .catch(() => {
      if (cached !== null) value.textContent = String(cached).padStart(6, '0');
    });
})();
