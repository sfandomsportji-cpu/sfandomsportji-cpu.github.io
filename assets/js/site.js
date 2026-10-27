/* SFANDOM site script — 메뉴 · 경기 종목 탭 · 릴스 · 쪽지 · 팀 로고 · 블로그 · 팬 보드 · 검색 */
(() => {
  'use strict';
  const CFG = window.SFANDOM || {};
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };

  /* 외부 이미지 서버가 차단되어도 콘텐츠 카드가 빈 화면이 되지 않도록 안전하게 표시 */
  const fallbackImage = img => {
    if (!img || img.dataset.fallbackApplied) return;
    const thumb = img.closest('.thumb');
    if (!thumb) return;
    img.dataset.fallbackApplied = '1';
    img.remove();
    thumb.classList.add('thumb-fallback');
    if (!thumb.querySelector('.thumb-fallback-text')) {
      const label = img.closest('.portrait') ? 'NBA' : 'SFANDOM';
      thumb.append(el('span', 'thumb-fallback-text', label));
    }
  };
  document.addEventListener('error', e => {
    if (e.target?.tagName === 'IMG') fallbackImage(e.target);
  }, true);
  $$('img').forEach(img => {
    if (img.complete && img.naturalWidth === 0) fallbackImage(img);
  });

  /* 점수는 배포 시각의 기록입니다. 빌드가 늦어져도 오래된 LIVE를 현재형으로 남기지 않습니다. */
  const refreshRecordedScores = () => {
    const now = Date.now();
    $$('[data-score-state]').forEach(card => {
      const state = card.dataset.scoreState;
      const checked = Date.parse(card.dataset.scoreChecked || '');
      const start = Date.parse(card.dataset.scoreStart || '');
      const stale = !Number.isFinite(checked) || now - checked > 2 * 60 * 60 * 1000;
      const label = $('.sf-scores__time small', card);
      const badge = $('.sf-scores__tag', card);
      if (!label || !badge) return;
      if (state === 'live' && stale) {
        label.textContent = '마지막 확인 당시 진행 중';
        badge.textContent = '자료 시각 기준';
      } else if (state === 'scheduled' && Number.isFinite(start) && now > start + 20 * 60 * 1000) {
        label.textContent = '결과 확인 중';
        badge.textContent = '자료 시각 기준';
      } else if (state === 'scheduled' && stale) {
        label.textContent = '예정 · 갱신 지연';
        badge.textContent = '자료 시각 기준';
      }
    });
  };
  refreshRecordedScores();
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refreshRecordedScores();
  });

  /* ── 경기 센터 종목 탭: 스크립트가 켜질 때만 탭으로 바꾸고, 꺼져 있으면 전 종목이 그대로 보입니다 ── */
  $$('[data-score-tabs]').forEach(box => {
    const bar = $('.sf-scores__tabs', box);
    const tabs = $$('[data-score-tab]', box);
    const panels = $$('.sf-scores__league[data-league]', box);
    if (!bar || !tabs.length || !panels.length) return;
    const show = league => {
      tabs.forEach(t => t.setAttribute('aria-selected', String(t.dataset.scoreTab === league)));
      panels.forEach(p => { p.hidden = p.dataset.league !== league; });
    };
    bar.hidden = false;
    box.classList.add('is-tabbed');
    tabs.forEach(t => t.addEventListener('click', () => show(t.dataset.scoreTab)));
    show(tabs[0].dataset.scoreTab);
  });

  /* ── 전체 메뉴 · 검색 ── */
  const toggle = (btn, panel, focusSel) => {
    if (!btn || !panel) return;
    btn.addEventListener('click', () => {
      const open = panel.hasAttribute('hidden');
      $$('[data-panel]').forEach(p => p.setAttribute('hidden', ''));
      $$('[aria-controls]').forEach(b => b.setAttribute('aria-expanded', 'false'));
      if (open) {
        panel.removeAttribute('hidden');
        btn.setAttribute('aria-expanded', 'true');
        const f = focusSel && $(focusSel, panel);
        if (f) f.focus();
      }
    });
  };
  toggle($('#searchBtn'), $('#searchBar'), 'input');
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    $$('[data-panel]').forEach(p => p.setAttribute('hidden', ''));
    $$('[aria-controls]').forEach(b => b.setAttribute('aria-expanded', 'false'));
  });

  /* ── 첫 화면 배경 영상: 자동재생 + 자동 사운드 복구 ── */
  const heroVideo = $('.hero-video');
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const saveData = navigator.connection && navigator.connection.saveData;

  if (heroVideo && heroVideo.dataset.src && !reduce && !saveData) {
    heroVideo.addEventListener('playing', () => {
      heroVideo.classList.add('on');
      heroVideo.parentElement.classList.add('playing');
    }, { once: true });

    let dimTimer = null;
    const dim = () => {
      if (!heroVideo.classList.contains('on')) return;
      clearTimeout(dimTimer);
      dimTimer = setTimeout(() => heroVideo.classList.add('dim'), 250);
    };
    const undim = () => {
      clearTimeout(dimTimer);
      heroVideo.classList.remove('dim');
    };
    heroVideo.addEventListener('waiting', dim);
    heroVideo.addEventListener('stalled', dim);
    heroVideo.addEventListener('playing', undim);

    if (!heroVideo.getAttribute('src')) heroVideo.src = heroVideo.dataset.src;
    heroVideo.preload = 'auto';
    heroVideo.volume = 0.65;

    const muteToggle = document.createElement('button');
    muteToggle.type = 'button';
    muteToggle.className = 'hero-mute-toggle';
    muteToggle.setAttribute('aria-label', '음악 음소거');
    muteToggle.setAttribute('aria-pressed', 'false');
    muteToggle.innerHTML = '';
    muteToggle.style.cssText = 'position:absolute;right:18px;bottom:18px;z-index:12;width:44px;height:44px;border:1px solid rgba(255,255,255,.42);border-radius:50%;background:rgba(11,11,15,.68);color:#fff;font-size:20px;display:flex;align-items:center;justify-content:center;cursor:pointer;backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)';
    heroVideo.closest('.hero')?.append(muteToggle);

    const volumeMutedIcon = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="m23 9-6 6"/><path d="m17 9 6 6"/></svg>';
    const volumeOnIcon = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>';
    const syncMuteToggle = () => {
      const isMuted = heroVideo.muted;
      muteToggle.innerHTML = isMuted ? volumeMutedIcon : volumeOnIcon;
      muteToggle.setAttribute('aria-label', isMuted ? '영상 소리 켜기' : '영상 소리 끄기');
      muteToggle.setAttribute('title', isMuted ? '영상 소리 켜기' : '영상 소리 끄기');
      muteToggle.setAttribute('aria-pressed', String(isMuted));
    };

    muteToggle.addEventListener('click', async () => {
      heroVideo.muted = !heroVideo.muted;
      if (!heroVideo.muted) {
        heroVideo.volume = 0.65;
        try { await heroVideo.play(); } catch (_) {}
      }
      syncMuteToggle();
    });

    heroVideo.addEventListener('volumechange', syncMuteToggle);
    syncMuteToggle();

    // 안정화: 소리는 사용자가 음소거 버튼을 직접 누를 때만 켭니다.
    // 외부 동영상 로딩 실패 시 저장소의 로컬 영상으로 전환합니다.
    const backupHeroVideo = '/assets/sfandom-hero-loop.mp4';
    let backupActive = false;
    const onVideoFailure = () => {
      heroVideo.classList.remove('on', 'dim');
      heroVideo.parentElement?.classList.remove('playing');
      if (!backupActive) {
        backupActive = true;
        heroVideo.src = backupHeroVideo;
        heroVideo.load();
        heroVideo.play().catch(() => {});
      } else {
        heroVideo.pause();
        heroVideo.removeAttribute('src');
        heroVideo.load();
        muteToggle.hidden = true;
      }
    };
    heroVideo.addEventListener('error', onVideoFailure);
    const firstFrameTimer = setTimeout(() => {
      if (!backupActive && heroVideo.readyState < 2) onVideoFailure();
    }, 8500);
    heroVideo.addEventListener('playing', () => clearTimeout(firstFrameTimer), { once: true });
    heroVideo.muted = true;
    syncMuteToggle();
    heroVideo.play().catch(() => {});

    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && heroVideo.paused && heroVideo.src) heroVideo.play().catch(() => {});
    });
  }

  /* ── FAN ZONE 릴스: 인스타그램 화면이 뜨지 않으면 사이트의 브랜드 영상으로 그 자리를 채움 ──
     인스타그램 임베드는 뜨는 즉시 부모 창에 메시지를 보냅니다. 화면에 들어온 뒤 8초 동안 메시지가 없으면 실패로 봅니다. */
  const reel = $('[data-reel]');
  if (reel) {
    const frame = $('iframe', reel), fb = $('.reel-fallback', reel);
    let alive = false, timer = null;
    window.addEventListener('message', e => { if (/^https:\/\/([a-z0-9-]+\.)*instagram\.com$/.test(e.origin || '')) { alive = true; clearTimeout(timer); } });
    const fail = () => {
      if (alive || !fb) return;
      reel.classList.add('failed'); fb.hidden = false;
      if (!fb.getAttribute('src')) fb.src = fb.dataset.src;
      fb.play().catch(() => {});
    };
    if (frame && fb && 'IntersectionObserver' in window) {
      const io = new IntersectionObserver(es => { if (es.some(x => x.isIntersecting)) { io.disconnect(); timer = setTimeout(fail, 8000); } }, { rootMargin: '200px' });
      io.observe(reel);
      frame.addEventListener('error', fail, { once: true });
    }
  }

  /* ── 문의(쪽지) 양식: 메일 주소를 노출하지 않고 사이트 안에서 접수 → 드라이브 "SFANDOM 쪽지함" 시트에 저장 ──
     받는 쪽(Apps Script 웹 앱)은 nick · email · message · page · website 값을 받고, message는 1000자까지 저장합니다. */
  const cf = $('[data-contact]');
  if (cf) {
    const msg = $('[data-contact-msg]', cf), btn = $('button[type=submit]', cf), endpoint = cf.dataset.endpoint, opened = Date.now();
    const say = (t, bad) => { msg.textContent = t; msg.style.color = bad ? 'var(--red)' : ''; };
    cf.addEventListener('submit', async e => {
      e.preventDefault();
      if (!endpoint) return;
      const fd = new FormData(cf), v = k => String(fd.get(k) || '').trim();
      if (v('website')) return;                                   // 자동 프로그램이 채우는 숨은 칸
      if (Date.now() - opened < 4000) return say('잠시 뒤에 다시 눌러 주세요.', true);
      if (v('title').length < 2 || v('body').length < 10) return say('제목과 내용을 조금 더 적어 주세요.', true);
      if (v('reply') && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v('reply'))) return say('이메일 주소 형식을 확인해 주세요.', true);
      if (!fd.get('agree')) return say('수집·보관 동의에 체크해 주세요.', true);
      const message = `[${v('type')}] ${v('title').slice(0, 100)}\n\n${v('body').slice(0, 850)}`.slice(0, 1000);
      btn.disabled = true; say('보내는 중입니다…');
      try {
        // 받는 쪽이 다른 주소라 응답 내용은 읽을 수 없습니다. 전송이 끝나면 접수 안내만 보여 줍니다.
        await fetch(endpoint, { method: 'POST', mode: 'no-cors',
          body: new URLSearchParams({ nick: v('name').slice(0, 40), email: v('reply').slice(0, 120), message, website: '', page: location.pathname }) });
        cf.reset(); cf.classList.add('sent'); say('쪽지가 전달됐습니다. 확인 후 필요한 경우 회신드리겠습니다.');
      } catch (err) {
        btn.disabled = false; say('전송하지 못했습니다. 잠시 뒤 다시 시도해 주세요.', true);
      }
    });
  }

  /* ── 팀 로고: 못 불러오면 팀 색 약자 칩으로 ── */
  $$('img.tlogo').forEach(im => {
    const fail = () => im.parentNode && im.parentNode.classList.add('nologo');
    if (im.complete && im.naturalWidth === 0 && im.currentSrc) fail(); else im.addEventListener('error', fail, { once: true });
  });

  /* ── 매거진: 구글 블로그(Blogger) 최신 글을 브라우저에서 바로 받아 합치기 ──
     네이버 글은 빌드 때 받아 HTML에 들어 있고, 구글 글은 여기서 JSONP로 최신 상태를 가져옵니다. */
  const grids = $$('[data-blog-grid]');
  const blogUrl = grids[0]?.dataset.blogger;
  if (grids.length && blogUrl) {
    // 정적 글이 이미 있는 경우 외부 API 실패와 무관하게 대기 문구를 즉시 숨깁니다.
    grids.forEach(g => { const e = g.nextElementSibling; if (e?.classList.contains('blog-empty') && $$('a.mag', g).length) e.hidden = true; });
    const cb = '__sfBlogger' + Date.now();
    const bigImg = u => (u || '').replace(/\/[sw]\d+(?:-[a-z]+\d*)*\//, '/w800-rj/').replace(/=[sw]\d+(?:-[a-z]+\d*)*$/, '=w800-rj');
    const strip = h => { const d = document.createElement('div'); d.innerHTML = h || ''; return (d.textContent || '').replace(/\s+/g, ' ').trim(); };
    window[cb] = data => {
      const entries = data?.feed?.entry || [];
      const posts = entries.map(e => {
        const link = (e.link || []).find(l => l.rel === 'alternate')?.href || '';
        let img = e.media$thumbnail?.url || '';
        if (!img) { const m = (e.content?.$t || '').match(/<img[^>]+src="([^"]+)"/i); img = m ? m[1] : ''; }
        return { title: e.title?.$t || '', link, date: (e.published?.$t || '').slice(0, 10), img: bigImg(img),
                 summary: (s => s.length > 320 ? s.slice(0, 319).trimEnd() + '…' : s)(strip(e.summary?.$t || e.content?.$t)) };
      }).filter(p => p.link);
      grids.forEach(grid => {
        const have = new Set($$('a[href]', grid).map(a => a.href));
        const core = grid.dataset.core ? new RegExp(grid.dataset.core, 'i') : null;   // 홈: NBA·MLB 글만
        posts.forEach(p => {
          if (have.has(p.link) || (core && !core.test(p.title + ' ' + p.summary))) return;
          const a = el('a', 'mag lift'); a.href = p.link; a.target = '_blank'; a.rel = 'noopener';
          a.dataset.date = p.date; a.dataset.src = 'google';
          const th = el('div', 'thumb' + (p.img ? '' : ' blog-thumb'));
          if (p.img) { const im = el('img'); im.src = p.img; im.alt = ''; im.loading = 'lazy'; im.referrerPolicy = 'no-referrer'; th.append(im); } else th.append(el('span', null, 'G'));
          const body = el('div', 'body');
          body.append(el('span', 'tag red', grid.dataset.label || 'GOOGLE BLOG'), el('h3', null, p.title), el('p', null, p.summary),
                      el('span', 'tag', `${p.date.replace(/-/g, '.')} · 블로그에서 읽기 ↗`));
          a.append(th, body); grid.append(a);
        });
        const cards = $$('a.mag', grid).sort((x, y) => (y.dataset.date || '').localeCompare(x.dataset.date || ''));
        const limit = Number(grid.dataset.limit || 6);
        cards.forEach((c, i) => { if (i < limit) grid.append(c); else c.remove(); });
        const empty = grid.nextElementSibling;
        if (empty && empty.classList.contains('blog-empty')) empty.hidden = cards.length > 0;
      });
      delete window[cb];
    };
    const sc = document.createElement('script');
    sc.src = `${blogUrl.replace(/\/$/, '')}/feeds/posts/default?alt=json-in-script&max-results=24&callback=${cb}`;
    sc.async = true;
    sc.onerror = () => grids.forEach(g => { const e = g.nextElementSibling; if (e && !$$('a.mag', g).length) e.textContent = '블로그 글을 불러오지 못했습니다. 아래 블로그 바로가기를 이용해 주세요.'; });
    document.head.append(sc);
  }

  /* ── 네이버 영상 카드: 누르면 사이트 안에서 바로 재생 ──
     영상 번호·재생 키는 빌드 때 네이버 글에서 받아 카드에 넣어 둡니다(data-vid · data-inkey).
     값이 없거나 30분이 지났거나 Ctrl·⌘·Shift 클릭이면 기존처럼 네이버 원문이 새 탭으로 열립니다. */
  const closePlayer = () => {
    const box = document.querySelector('.sf-vmodal');
    if (!box) return;
    const back = box._opener;
    box.remove();
    document.documentElement.classList.remove('sf-vmodal-open');
    if (back && back.focus) back.focus();
  };
  const openPlayer = card => {
    closePlayer();
    const vid = card.dataset.vid, key = card.dataset.inkey;
    const title = (card.querySelector('h3') || {}).textContent || '네이버 영상';
    const box = el('div', 'sf-vmodal'); box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-label', title);
    box._opener = card;
    const panel = el('div', 'sf-vmodal__panel');
    const bar = el('div', 'sf-vmodal__bar');
    const t = el('strong', null, title);
    const close = el('button', 'sf-vmodal__close', '닫기 ✕'); close.type = 'button'; close.addEventListener('click', closePlayer);
    bar.append(t, close);
    const stage = el('div', 'sf-vmodal__stage');
    const frame = document.createElement('iframe');
    frame.src = 'https://serviceapi.nmv.naver.com/flash/convertIframeTag.nhn?vid=' + encodeURIComponent(vid) + '&inKey=' + encodeURIComponent(key) + '&autoPlay=true&width=1280&height=720';
    frame.allow = 'autoplay; fullscreen; encrypted-media; picture-in-picture';
    frame.allowFullscreen = true; frame.title = title; frame.referrerPolicy = 'strict-origin-when-cross-origin';
    stage.append(frame);
    const foot = el('div', 'sf-vmodal__foot');
    const out = el('a', null, '재생이 안 되면 네이버에서 열기 ↗'); out.href = card.href; out.target = '_blank'; out.rel = 'noopener';
    foot.append(out);
    panel.append(bar, stage, foot); box.append(panel);
    box.addEventListener('click', e => { if (e.target === box) closePlayer(); });
    document.body.append(box);
    document.documentElement.classList.add('sf-vmodal-open');
    close.focus();
  };
  document.addEventListener('click', e => {
    const card = e.target.closest && e.target.closest('a[data-vid][data-inkey]');
    if (!card || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    // 재생 키는 받은 지 30분이 지나면 쓰지 않습니다. 시각이 없거나 오래됐으면 네이버 원문이 새 탭으로 열립니다.
    const got = Number(card.dataset.inkeyAt || 0);
    if (!got || Date.now() / 1000 - got > 30 * 60) return;
    e.preventDefault();
    openPlayer(card);
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closePlayer(); });

  /* ── Supabase 공통 ── */
  const SB = CFG.supabase || {};
  // Reads can temporarily time out at PostgREST. Retry only safe GET requests.
  // Never retry POST automatically: the original write might already have succeeded.
  const request = async (path, options = {}) => {
    const isRead = !options.method || String(options.method).toUpperCase() === 'GET';
    const attempts = isRead ? 2 : 1;
    for (let attempt = 0; attempt < attempts; attempt++) {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), attempt ? 10000 : 8000);
      try {
        const res = await fetch(SB.url + path, {
          ...options, signal: ctrl.signal, cache: 'no-store', credentials: 'omit',
          headers: { apikey: SB.key, Accept: 'application/json', ...(options.headers || {}) }
        });
        if (!res.ok) {
          const err = new Error('http ' + res.status);
          err.status = res.status;
          throw err;
        }
        return res;
      } catch (err) {
        const retryable = !err.status || err.status === 429 || err.status >= 500;
        if (!isRead || attempt === attempts - 1 || !retryable) throw err;
        await new Promise(resolve => setTimeout(resolve, 450));
      } finally {
        clearTimeout(timer);
      }
    }
  };
  const fmtTime = raw => {
    const d = new Date(raw);
    if (!raw || Number.isNaN(d.getTime())) return '';
    const diff = (Date.now() - d.getTime()) / 60000;
    if (diff < 1) return '방금';
    if (diff < 60) return Math.floor(diff) + '분 전';
    if (diff < 1440) return Math.floor(diff / 60) + '시간 전';
    return new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', month: '2-digit', day: '2-digit' }).format(d);
  };

  /* ── 팬 보드 ──
     채널·경기 스레드·한 줄 평은 글 제목 앞의 [머리말]로 구분합니다. 예) "[NBA] 제목", "[PHI@NYK] 제목", "[한줄] 내용"
     게시판 저장소(posts 표)는 그대로 쓰고, 목록을 불러올 때 제목 머리말로 걸러 냅니다. */
  const QUICK = '한줄';
  const splitTag = title => { const m = /^\[([^\]]{1,20})\]\s*(.*)$/.exec(title || ''); return m ? [m[1], m[2]] : ['자유', title || '']; };
  const likeTag = t => 'like.' + encodeURIComponent('[' + t + ']') + '*';
  const throttled = () => { let last = 0; try { last = Number(localStorage.getItem('sfandom_community_last_post_at') || 0); } catch (_) {} return Date.now() - last < 15000; };
  const stamp = () => { try { localStorage.setItem('sfandom_community_last_post_at', String(Date.now())); } catch (_) {} };
  const sendPost = (nickname, title, body) => request('/functions/v1/community-post', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nickname, title, body }) });
  const postError = err => err && err.status === 429 ? '연속 등록 방지를 위해 잠시 후 다시 작성해 주세요.' : '게시하지 못했습니다. 잠시 후 다시 시도해 주세요.';

  const renderPosts = (list, rows, total, page, size) => {
    list.replaceChildren();
    if (!rows.length) { list.append(el('div', 'empty', '아직 글이 없습니다. 첫 글을 남겨보세요.')); return; }
    rows.forEach((p, i) => {
      const [tag, title] = splitTag(p.title);
      const a = el('article', 'post');
      a.dataset.postId = p.id;
      a.id = 'comments-' + p.id;
      a.append(el('span', 'post-no', String(Math.max(1, total - ((page - 1) * size + i)))));
      const b = el('div', 'post-body');
      const meta = el('span', 'post-meta');
      meta.append(el('b', null, '#' + tag), document.createTextNode(` · ${p.nickname || 'ANON'} · ${fmtTime(p.created_at)}` + (typeof p._cc === 'number' ? ` · 댓글 ${p._cc}` : '')));
      b.append(meta, el('strong', null, title || '(제목 없음)'), el('p', null, p.body || ''));
      if (typeof p.source_url === 'string' && /^\/news\/\d{4}\/\d{2}\/[a-z0-9-]+\/$/.test(p.source_url)) {
        const source = el('a', 'news-discussion-source', '원문 기사 보기 ↗');
        source.href = p.source_url;
        b.append(source);
      }
      a.append(b);
      list.append(a);
    });
  };

  // 글 목록(홈 등) 바로 밑에 최근 댓글을 보여 줍니다. 댓글·답글 전체 화면(community-thread.js)이 있는 팬 보드에서는 그쪽이 대신합니다.
  const previewComments = async (list, rows) => {
    if (window.SFANDOM_THREAD || !rows.length) return;
    const ids = rows.map(p => p.id).filter(id => /^[0-9a-zA-Z-]{1,40}$/.test(String(id)));
    if (!ids.length) return;
    try {
      const res = await request('/rest/v1/comments?select=id,post_id,nickname,body,created_at&status=eq.published&order=created_at.desc&limit=80&post_id=in.(' + ids.join(',') + ')');
      const all = await res.json();
      if (!Array.isArray(all)) return;
      const by = {};
      all.forEach(c => { (by[c.post_id] = by[c.post_id] || []).push(c); });
      list.querySelectorAll('article.post[data-post-id]').forEach(card => {
        const cs = by[card.dataset.postId];
        const body = card.querySelector('.post-body');
        if (!cs || !cs.length || !body || body.querySelector('.post-preview')) return;
        const box = el('div', 'post-preview');
        cs.slice(0, 3).reverse().forEach(c => {
          const item = el('div', 'pp-item');
          const meta = el('span', 'pp-meta');
          meta.append(el('b', null, c.nickname || 'ANON'), document.createTextNode(' · ' + fmtTime(c.created_at)));
          item.append(meta, el('span', 'pp-text', c.body || ''));
          box.append(item);
        });
        const more = el('a', 'pp-more', cs.length > 3 ? '댓글 ' + cs.length + '개 모두 보기 →' : '댓글 · 답글 쓰기 →');
        more.href = '/community/#comments-' + card.dataset.postId;
        box.append(more);
        body.append(box);
      });
    } catch (_) { /* 댓글 미리보기는 부가 기능입니다. 실패해도 글 목록은 그대로 둡니다. */ }
  };

  const params = new URLSearchParams(location.search);
  const channel = (params.get('ch') || '').slice(0, 20), thread = (params.get('thread') || '').slice(0, 20);
  const onBoardPage = !!$('[data-board-form]');
  $$('[data-chips] a').forEach(a => { if (onBoardPage && !thread && a.dataset.ch === channel) a.setAttribute('aria-current', 'page'); });

  const board = $('[data-board]');
  if (board && SB.url) {
    const size = Number(board.dataset.size || 10);
    const list = $('[data-board-list]', board);
    const pager = $('[data-board-pager]', board);
    const form = $('[data-board-form]');
    const status = $('[data-board-status]');
    const scope = onBoardPage ? (thread || channel) : '';
    let page = 1, total = 0, busy = false;
    // 홈 팬 보드의 정렬 탭: 실시간(최근 활동순) · 투데이(오늘 올라온 글) · 댓글순(최근 글 중 댓글 많은 순)
    let mode = 'live';
    const kstDayStart = () => { const n = new Date(Date.now() + 9 * 3600e3); return new Date(Date.UTC(n.getUTCFullYear(), n.getUTCMonth(), n.getUTCDate()) - 9 * 3600e3).toISOString(); };
    $$('[data-board-tab]', board).forEach(tab => tab.addEventListener('click', () => {
      if (busy || tab.dataset.boardTab === mode) return;
      mode = tab.dataset.boardTab; page = 1;
      $$('[data-board-tab]', board).forEach(t => t.setAttribute('aria-selected', t === tab ? 'true' : 'false'));
      load();
    }));

    const head = $('[data-thread-head]', board);
    if (head && thread) { head.hidden = false; $('[data-thread-name]', head).textContent = thread.replace('@', ' @ '); }
    const sel = form && form.querySelector('[name="channel"]');
    if (sel && thread) { const o = el('option', null, thread.replace('@', ' @ ') + ' 경기 스레드'); o.value = thread; sel.append(o); sel.value = thread; }
    else if (sel && channel && [...sel.options].some(o => o.value === channel)) sel.value = channel;

    const renderPager = () => {
      if (!pager) return;
      pager.replaceChildren();
      const pages = Math.max(1, Math.ceil(total / size));
      const mk = (label, target, disabled, current) => {
        const b = el('button', null, label);
        b.type = 'button'; b.disabled = disabled;
        if (current) b.setAttribute('aria-current', 'page');
        b.addEventListener('click', () => { if (!busy && target !== page) { page = target; load(); } });
        pager.append(b);
      };
      mk('‹', Math.max(1, page - 1), page === 1);
      const start = Math.max(1, Math.min(page - 2, Math.max(1, pages - 4)));
      for (let p = start; p <= Math.min(pages, start + 4); p++) mk(String(p), p, false, p === page);
      mk('›', Math.min(pages, page + 1), page === pages);
    };

    const load = async () => {
      busy = true;
      const from = (page - 1) * size;
      // 한 줄 평은 QUICK TALK에만 보이게 일반 목록에서 뺍니다. '자유'는 머리말이 없는 글도 포함합니다.
      const filter = scope === '자유' ? '&title=not.like.' + encodeURIComponent('[') + '*'
        : scope ? '&title=' + likeTag(scope) : '&title=not.' + likeTag(QUICK);
      const today = mode === 'today', byComments = mode === 'comments';
      const order = today ? 'created_at.desc' : 'updated_at.desc';
      const since = today ? '&created_at=gte.' + encodeURIComponent(kstDayStart()) : '';
      const last = byComments ? from + 29 : from + size - 1;  // 댓글순은 최근 글 30개 안에서 정렬합니다.
      try {
        const res = await request('/rest/v1/posts?select=id,title,body,nickname,created_at,updated_at,source_url&status=eq.published&order=' + order + filter + since, {
          headers: { Prefer: 'count=exact', 'Range-Unit': 'items', Range: `${from}-${last}` }
        });
        let rows = await res.json();
        const m = (res.headers.get('content-range') || '').match(/\/(\d+)$/);
        total = m ? Number(m[1]) : rows.length;
        if (byComments && rows.length) {
          try {
            const ids = rows.map(p => p.id).filter(id => /^[0-9a-zA-Z-]{1,40}$/.test(String(id)));
            const cr = await request('/rest/v1/comments?select=post_id&status=eq.published&limit=1000&post_id=in.(' + ids.join(',') + ')');
            const cs = await cr.json();
            const cnt = {};
            if (Array.isArray(cs)) cs.forEach(c => { cnt[c.post_id] = (cnt[c.post_id] || 0) + 1; });
            rows = rows.map((p, i) => ({ p, i, n: cnt[p.id] || 0 })).sort((a, b) => b.n - a.n || a.i - b.i).map(x => Object.assign({}, x.p, { _cc: x.n }));
          } catch (_) { /* 댓글 수를 못 불러오면 최근 활동순 그대로 보여 줍니다. */ }
          rows = rows.slice(0, size); total = rows.length;
        } else if (today) { total = rows.length; }
        renderPosts(list, rows, total, page, size);
        renderPager();
        previewComments(list, rows);
        return true;
      } catch (_) {
        // Keep any already visible posts on intermittent read failures.
        if (!list.querySelector('article.post')) {
          const warning = el('div', 'empty', '글은 보관되어 있습니다. 목록을 불러오는 중 연결이 끊겼습니다.');
          const retry = el('button', 'pill', '글 목록 다시 불러오기');
          retry.type = 'button';
          retry.addEventListener('click', () => { if (!busy) load(); });
          list.replaceChildren(warning, retry);
        }
        if (status) status.textContent = '글 목록 연결이 지연되고 있습니다. 다시 불러오기를 눌러주세요.';
        if (pager) pager.replaceChildren();
        return false;
      } finally { busy = false; }
    };

    form?.addEventListener('submit', async e => {
      e.preventDefault();
      if (busy) return;
      const fd = new FormData(form);
      if (String(fd.get('website') || '').trim()) return;
      const nickname = String(fd.get('nickname') || '').trim().slice(0, 30) || 'ANON';
      const ch = String(fd.get('channel') || '자유').trim().slice(0, 20);
      const raw = String(fd.get('title') || '').trim().replace(/^\[[^\]]*\]\s*/, '').slice(0, 100);
      const body = String(fd.get('body') || '').trim().slice(0, 2000);
      if (raw.length < 2 || body.length < 2) { status.textContent = '제목과 내용을 2자 이상 입력해 주세요.'; return; }
      if (throttled()) { status.textContent = '연속 등록 방지를 위해 잠시 후 다시 작성해 주세요.'; return; }
      const title = (ch === '자유' ? raw : `[${ch}] ${raw}`).slice(0, 120);
      busy = true; status.textContent = '게시 중입니다…';
      const btn = form.querySelector('button[type="submit"]'); if (btn) btn.disabled = true;
      try {
        await sendPost(nickname, title, body);
        stamp();
        const keep = sel ? sel.value : '';
        form.reset(); if (sel && keep) sel.value = keep;
        page = 1; status.textContent = '게시되었습니다.';
        busy = false;
        const visible = await load();
        if (!visible) status.textContent = '글은 저장되었습니다. 목록 조회가 지연 중입니다. 다시 불러오기를 눌러주세요.';
      } catch (err) {
        status.textContent = postError(err);
      } finally { busy = false; if (btn) btn.disabled = false; }
    });

    // 글의 "토론하기"에서 넘어오면 제목을 미리 채웁니다. "[NBA] …"처럼 채널 머리말이 있으면 채널도 맞춥니다.
    const pre = params.get('topic');
    if (pre && form) {
      const [tag, rest] = splitTag(pre);
      const t = form.querySelector('[name="title"]');
      if (sel && [...sel.options].some(o => o.value === tag)) { sel.value = tag; if (t && !t.value) t.value = rest.slice(0, 100); }
      else if (t && !t.value) t.value = pre.slice(0, 100);
    }
    load();
  }

  /* ── QUICK TALK: 한 줄 평 ── */
  const quick = $('[data-quick]');
  if (quick && SB.url) {
    const qList = $('[data-quick-list]', quick), qForm = $('[data-quick-form]', quick), qStatus = $('[data-quick-status]', quick);
    const qSize = Number(quick.dataset.size || 4);
    let qBusy = false;
    const qLoad = async () => {
      try {
        const res = await request('/rest/v1/posts?select=id,title,nickname,created_at&status=eq.published&order=created_at.desc&title=' + likeTag(QUICK), {
          headers: { 'Range-Unit': 'items', Range: `0-${qSize - 1}` } });
        const rows = await res.json();
        qList.replaceChildren();
        if (!rows.length) { qList.append(el('div', 'empty', '첫 한 줄 평을 남겨보세요.')); return; }
        rows.forEach(p => {
          const row = el('div', 'quick-row');
          row.append(el('span', 'quick-text', splitTag(p.title)[1]), el('span', 'quick-meta', `${p.nickname || 'ANON'} · ${fmtTime(p.created_at)}`));
          qList.append(row);
        });
      } catch (_) {
        const warning = el('div', 'empty', '한 줄 평 목록 연결이 지연되고 있습니다.');
        const retry = el('button', 'pill', '다시 불러오기');
        retry.type = 'button';
        retry.addEventListener('click', qLoad);
        if (!qList.querySelector('.quick-row')) qList.replaceChildren(warning, retry);
      }
    };
    qForm?.addEventListener('submit', async e => {
      e.preventDefault();
      if (qBusy) return;
      const fd = new FormData(qForm);
      if (String(fd.get('website') || '').trim()) return;
      const text = String(fd.get('text') || '').trim().replace(/\s+/g, ' ').slice(0, 60);
      if (text.length < 2) { qStatus.textContent = '2자 이상 적어 주세요.'; return; }
      if (throttled()) { qStatus.textContent = '연속 등록 방지를 위해 잠시 후 다시 작성해 주세요.'; return; }
      qBusy = true; qStatus.textContent = '등록 중입니다…';
      const btn = qForm.querySelector('button'); if (btn) btn.disabled = true;
      try { await sendPost('ANON', `[${QUICK}] ${text}`, text); stamp(); qForm.reset(); qStatus.textContent = '등록되었습니다.'; await qLoad(); }
      catch (err) { qStatus.textContent = postError(err); }
      finally { qBusy = false; if (btn) btn.disabled = false; }
    });
    qLoad();
  }

  /* ── 홈의 "SFANDOM과 대화하기" 쪽지 칸: 문의 페이지와 같은 쪽지함으로 전송 ── */
  const mf = $('[data-message]');
  if (mf && mf.dataset.endpoint) {
    const mStatus = $('[data-message-status]', mf), mBtn = $('button[type=submit]', mf), mOpened = Date.now();
    const mSay = (t, bad) => { mStatus.textContent = t; mStatus.style.color = bad ? 'var(--red)' : ''; };
    mf.addEventListener('submit', async e => {
      e.preventDefault();
      const fd = new FormData(mf), v = k => String(fd.get(k) || '').trim();
      if (v('website')) return;
      if (Date.now() - mOpened < 4000) return mSay('잠시 뒤에 다시 눌러 주세요.', true);
      if (v('body').length < 5) return mSay('내용을 조금 더 적어 주세요.', true);
      if (v('reply') && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v('reply'))) return mSay('이메일 주소 형식을 확인해 주세요.', true);
      mBtn.disabled = true; mSay('보내는 중입니다…');
      try {
        await fetch(mf.dataset.endpoint, { method: 'POST', mode: 'no-cors',
          body: new URLSearchParams({ nick: v('name').slice(0, 40), email: v('reply').slice(0, 120), message: ('[홈 쪽지] ' + v('body')).slice(0, 1000), website: '', page: location.pathname }) });
        mf.reset(); mSay('쪽지가 전달됐습니다. 확인 후 필요한 경우 회신드리겠습니다.');
      } catch (err) { mSay('전송하지 못했습니다. 잠시 뒤 다시 시도해 주세요.', true); }
      finally { mBtn.disabled = false; }
    });
  }

  /* ── 검색 ── */
  const results = $('[data-search-results]');
  if (results) {
    const q = (new URLSearchParams(location.search).get('q') || '').trim();
    const input = $('#searchPageInput'); if (input) input.value = q;
    const count = $('[data-search-count]');
    if (!q) { if (count) count.textContent = '검색어를 입력해 주세요.'; return; }
    fetch(CFG.root + 'search-index.json', { cache: 'no-cache' }).then(r => r.json()).then(items => {
      const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
      const hits = items.map(it => {
        const hay = (it.t + ' ' + it.s + ' ' + it.k + ' ' + it.x).toLowerCase();
        const score = terms.reduce((n, w) => n + (hay.includes(w) ? (it.t.toLowerCase().includes(w) ? 3 : 1) : -99), 0);
        return { it, score };
      }).filter(h => h.score > 0).sort((a, b) => b.score - a.score || (a.it.d < b.it.d ? 1 : -1));
      if (count) count.textContent = `“${q}” 검색 결과 ${hits.length}건`;
      results.replaceChildren();
      hits.slice(0, 50).forEach(({ it }) => {
        const a = el('a', 'li'); a.href = it.u;
        const box = el('div');
        box.append(el('span', 'tag red', `${it.k} · ${it.d}`), el('h2', null, it.t), el('p', null, it.x));
        a.append(el('div'), box);
        a.style.gridTemplateColumns = '1fr';
        a.firstChild.remove();
        results.append(a);
      });
      if (!hits.length) results.append(el('div', 'empty', '검색 결과가 없습니다. 다른 단어로 찾아보세요.'));
    }).catch(() => { if (count) count.textContent = '검색을 불러오지 못했습니다.'; });
  }

  /* NBA 허브: 기사 탭(뉴스·분석·매거진)과 접힌 지난 경기 — 해시로 들어오면 해당 부분을 펼친다 */
  const artTabs = $('[data-art-tabs]');
  const pastGames = $('.past-games');
  const showPanel = (id, focus) => {
    if (!artTabs) return false;
    const panel = $$('section[id]', artTabs).find(s => s.id === id);
    if (!panel) return false;
    $$('section[id]', artTabs).forEach(s => { s.hidden = s !== panel; });
    $$('[data-panel]', artTabs).forEach(b => b.setAttribute('aria-selected', String(b.dataset.panel === id)));
    if (focus) artTabs.scrollIntoView({ block: 'start' });
    return true;
  };
  if (artTabs) {
    $$('[data-panel]', artTabs).forEach(b => b.addEventListener('click', () => showPanel(b.dataset.panel, false)));
    const first = $('[data-panel]', artTabs);
    if (first) showPanel(first.dataset.panel, false);
  }
  const openFromHash = () => {
    const id = decodeURIComponent(location.hash.slice(1));
    if (!id) return;
    if (showPanel(id, true)) return;
    const target = document.getElementById(id);
    if (pastGames && target && pastGames.contains(target)) {
      pastGames.open = true;
      target.scrollIntoView({ block: 'center' });
    }
  };
  openFromHash();
  window.addEventListener('hashchange', openFromHash);
})();
