(() => {
  const exitCta = document.querySelector('.live-header-cta');
  if (exitCta) {
    exitCta.href = 'index.html';
    exitCta.textContent = '나가기 ↗';
    exitCta.setAttribute('aria-label', 'SFANDOM LIVE 나가기');
  }

  const STORAGE_KEY = 'sfandom_live_messages_v01';
  const NICK_KEY = 'sfandom_live_nickname_v01';
  const CLIENT_KEY = 'sfandom_live_client_v01';
  const MAX_MESSAGES = 100;
  const RATE_LIMIT_MS = 2500;
  const endpointMeta = document.querySelector('meta[name="sfandom-chat-endpoint"]');
  const endpoint = (endpointMeta?.content || '').trim();

  const els = {
    messageList: document.getElementById('messageList'),
    composer: document.getElementById('chatComposer'),
    input: document.getElementById('messageInput'),
    send: document.getElementById('sendButton'),
    topic: document.getElementById('topicSelect'),
    topicList: document.getElementById('topicList'),
    charCount: document.getElementById('charCount'),
    identity: document.getElementById('composerIdentity'),
    connection: document.getElementById('connectionBadge'),
    modeNote: document.getElementById('modeNote'),
    memberBadge: document.getElementById('memberBadge'),
    modal: document.getElementById('nicknameModal'),
    nicknameInput: document.getElementById('nicknameInput'),
    nicknameStart: document.getElementById('nicknameStart'),
    changeNickname: document.getElementById('changeNickname')
  };

  let nickname = localStorage.getItem(NICK_KEY) || '';
  let clientId = localStorage.getItem(CLIENT_KEY) || '';
  let messages = [];
  let activeFilter = 'ALL';
  let lastSentAt = 0;
  let lastSentText = '';
  let socket = null;
  let channel = null;
  let reconnectTimer = null;
  let reconnectAttempt = 0;

  if (!clientId) {
    clientId = crypto.randomUUID();
    localStorage.setItem(CLIENT_KEY, clientId);
  }

  const systemMessage = {
    id: 'system-welcome',
    nickname: 'KAIRO',
    clientId: 'system',
    topic: 'NOTICE',
    text: 'SFANDOM LIVE 테스트 채팅방입니다. 경기 의견은 자유롭게 나누되 서로를 향한 모욕·도배·개인정보 노출은 피해 주세요.',
    createdAt: 1787637600000,
    system: true
  };

  function safeParse(raw, fallback) {
    try { return JSON.parse(raw); } catch { return fallback; }
  }

  function loadLocalMessages() {
    const stored = safeParse(localStorage.getItem(STORAGE_KEY) || '[]', []);
    messages = Array.isArray(stored) ? stored.slice(-MAX_MESSAGES) : [];
    if (!messages.some((m) => m.id === systemMessage.id)) messages.unshift(systemMessage);
  }

  function saveLocalMessages() {
    const clean = messages.filter((m) => !m.system).slice(-MAX_MESSAGES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(clean));
  }

  function sanitizeNickname(value) {
    return value.replace(/[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ ._-]/g, '').replace(/\s+/g, ' ').trim().slice(0, 18);
  }

  function generatedNickname() {
    const suffix = clientId.replace(/-/g, '').slice(0, 4).toUpperCase();
    return `Guest-${suffix}`;
  }

  function formatTime(timestamp) {
    return new Intl.DateTimeFormat('ko-KR', {
      timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', hour12: false
    }).format(new Date(timestamp));
  }

  function initials(name) {
    const clean = name.replace(/[^0-9A-Za-z가-힣]/g, '');
    return (clean.slice(0, 2) || 'SF').toUpperCase();
  }

  function toast(text) {
    let el = document.querySelector('.toast');
    if (!el) {
      el = document.createElement('div');
      el.className = 'toast';
      document.body.appendChild(el);
    }
    el.textContent = text;
    el.classList.add('show');
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.remove('show'), 1800);
  }

  function renderMessages(keepBottom = true) {
    const list = els.messageList;
    const nearBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 130;
    const filtered = messages.filter((m) => activeFilter === 'ALL' || m.topic === activeFilter || m.system);
    list.replaceChildren();

    if (!filtered.length) {
      const empty = document.createElement('div');
      empty.className = 'chat-empty';
      empty.innerHTML = '<div><strong>아직 이 태그의 메시지가 없습니다.</strong><span>첫 이야기를 남겨보세요.</span></div>';
      list.appendChild(empty);
      return;
    }

    const frag = document.createDocumentFragment();
    filtered.forEach((msg) => {
      const row = document.createElement('article');
      row.className = `chat-message${msg.system ? ' is-system' : ''}`;
      row.dataset.id = msg.id;

      const avatar = document.createElement('div');
      avatar.className = 'message-avatar';
      avatar.textContent = initials(msg.nickname);

      const main = document.createElement('div');
      main.className = 'message-main';
      const meta = document.createElement('div');
      meta.className = 'message-meta';
      const name = document.createElement('strong');
      name.textContent = msg.nickname;
      const time = document.createElement('span');
      time.className = 'message-time';
      time.textContent = `${formatTime(msg.createdAt)} KST`;
      const tag = document.createElement('span');
      tag.className = 'message-tag';
      tag.textContent = msg.topic || 'GENERAL';
      meta.append(name, tag, time);

      const text = document.createElement('p');
      text.className = 'message-text';
      text.textContent = msg.text;
      main.append(meta, text);

      const actions = document.createElement('div');
      actions.className = 'message-actions';
      if (!msg.system) {
        const report = document.createElement('button');
        report.type = 'button';
        report.textContent = '신고';
        report.setAttribute('aria-label', '메시지 신고');
        report.addEventListener('click', () => toast('테스트 단계: 신고 기능은 서버 연결 후 활성화됩니다.'));
        actions.appendChild(report);
      }

      row.append(avatar, main, actions);
      frag.appendChild(row);
    });
    list.appendChild(frag);
    if (keepBottom && nearBottom) list.scrollTop = list.scrollHeight;
  }

  function applyIdentity() {
    els.identity.textContent = nickname || 'GUEST';
    els.memberBadge.textContent = nickname ? `GUEST · ${nickname}` : 'GUEST';
  }

  function openNicknameModal() {
    els.nicknameInput.value = nickname || generatedNickname();
    els.modal.hidden = false;
    setTimeout(() => els.nicknameInput.focus(), 10);
  }

  function closeNicknameModal() {
    els.modal.hidden = true;
  }

  function commitNickname() {
    const next = sanitizeNickname(els.nicknameInput.value);
    if (next.length < 2) {
      toast('닉네임을 2자 이상 입력해 주세요.');
      return;
    }
    nickname = next;
    localStorage.setItem(NICK_KEY, nickname);
    applyIdentity();
    closeNicknameModal();
    if (endpoint) connectSocket(true);
    els.input.focus();
  }

  function normalizeMessage(raw) {
    if (!raw || typeof raw !== 'object') return null;
    const text = String(raw.text || '').trim().slice(0, 300);
    const name = sanitizeNickname(String(raw.nickname || 'Guest')) || 'Guest';
    const topic = String(raw.topic || 'GENERAL').toUpperCase().slice(0, 16);
    const createdAt = Number(raw.createdAt) || Date.now();
    const id = String(raw.id || crypto.randomUUID());
    if (!text) return null;
    return { id, nickname: name, clientId: String(raw.clientId || ''), topic, text, createdAt, system: Boolean(raw.system) };
  }

  function appendMessage(message, persist = true) {
    const normalized = normalizeMessage(message);
    if (!normalized || messages.some((m) => m.id === normalized.id)) return;
    messages.push(normalized);
    if (messages.length > MAX_MESSAGES + 1) {
      const system = messages.find((m) => m.system);
      messages = messages.filter((m) => !m.system).slice(-MAX_MESSAGES);
      if (system) messages.unshift(system);
    }
    if (persist && !endpoint) saveLocalMessages();
    renderMessages();
  }

  function sendLocal(text, topic) {
    const msg = {
      id: crypto.randomUUID(), nickname, clientId, topic, text, createdAt: Date.now()
    };
    appendMessage(msg, true);
    channel?.postMessage({ type: 'message', message: msg });
  }

  function socketUrl() {
    const base = endpoint.replace(/^http/i, 'ws').replace(/\/$/, '');
    const url = new URL(`${base}/room/main`);
    url.searchParams.set('nickname', nickname);
    url.searchParams.set('client', clientId);
    return url.toString();
  }

  function setLiveStatus(isLive, label) {
    els.connection.classList.toggle('is-live', isLive);
    els.connection.querySelector('b').textContent = label;
    els.modeNote.textContent = isLive ? '실시간 서버 연결됨' : (endpoint ? '서버 재연결 중' : '브라우저 테스트 모드');
  }

  function connectSocket(force = false) {
    if (!endpoint || !nickname) return;
    if (!force && socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;
    if (socket) {
      socket.onclose = null;
      socket.close();
    }
    clearTimeout(reconnectTimer);
    try {
      socket = new WebSocket(socketUrl());
    } catch {
      setLiveStatus(false, 'OFFLINE');
      return;
    }
    setLiveStatus(false, 'CONNECTING');
    socket.addEventListener('open', () => {
      reconnectAttempt = 0;
      setLiveStatus(true, 'LIVE');
    });
    socket.addEventListener('message', (event) => {
      if (typeof event.data !== 'string') return;
      const payload = safeParse(event.data, null);
      if (!payload) return;
      if (payload.type === 'history' && Array.isArray(payload.messages)) {
        const restored = payload.messages.map(normalizeMessage).filter(Boolean);
        messages = [systemMessage, ...restored.filter((m) => m.id !== systemMessage.id)].slice(-(MAX_MESSAGES + 1));
        renderMessages();
        els.messageList.scrollTop = els.messageList.scrollHeight;
      } else if (payload.type === 'message' && payload.message) {
        appendMessage(payload.message, false);
      } else if (payload.type === 'error') {
        toast(payload.message || '메시지를 전송할 수 없습니다.');
      }
    });
    socket.addEventListener('close', () => {
      setLiveStatus(false, 'OFFLINE');
      const delay = Math.min(15000, 1000 * (2 ** reconnectAttempt++));
      reconnectTimer = setTimeout(() => connectSocket(), delay);
    });
    socket.addEventListener('error', () => setLiveStatus(false, 'OFFLINE'));
  }

  function submitMessage() {
    if (!nickname) {
      openNicknameModal();
      return;
    }
    const text = els.input.value.replace(/\r/g, '').trim();
    if (!text) return;
    if (text.length > 300) {
      toast('메시지는 300자까지 가능합니다.');
      return;
    }
    const now = Date.now();
    if (now - lastSentAt < RATE_LIMIT_MS) {
      toast('조금만 천천히 보내 주세요.');
      return;
    }
    if (text === lastSentText && now - lastSentAt < 15000) {
      toast('같은 메시지를 연속으로 보낼 수 없습니다.');
      return;
    }
    if ((text.match(/https?:\/\//gi) || []).length > 1) {
      toast('광고·도배 방지를 위해 링크는 한 개까지만 허용합니다.');
      return;
    }

    const topic = els.topic.value;
    if (endpoint && socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'message', text, topic }));
    } else if (!endpoint) {
      sendLocal(text, topic);
    } else {
      toast('채팅 서버에 다시 연결 중입니다.');
      return;
    }
    lastSentAt = now;
    lastSentText = text;
    els.input.value = '';
    els.input.style.height = 'auto';
    els.charCount.textContent = '0 / 300';
  }

  function initLocalSync() {
    if (!('BroadcastChannel' in window)) return;
    channel = new BroadcastChannel('sfandom-live-v01');
    channel.addEventListener('message', (event) => {
      if (event.data?.type === 'message') appendMessage(event.data.message, false);
    });
  }

  els.composer.addEventListener('submit', (event) => {
    event.preventDefault();
    submitMessage();
  });

  els.input.addEventListener('input', () => {
    els.charCount.textContent = `${els.input.value.length} / 300`;
    els.input.style.height = 'auto';
    els.input.style.height = `${Math.min(140, els.input.scrollHeight)}px`;
  });

  els.input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitMessage();
    }
  });

  els.topicList.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-topic]');
    if (!button) return;
    activeFilter = button.dataset.topic;
    els.topicList.querySelectorAll('button').forEach((b) => b.classList.toggle('active', b === button));
    renderMessages(false);
  });

  els.nicknameStart.addEventListener('click', commitNickname);
  els.nicknameInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') commitNickname();
  });
  els.changeNickname.addEventListener('click', openNicknameModal);

  window.addEventListener('storage', (event) => {
    if (!endpoint && event.key === STORAGE_KEY) {
      loadLocalMessages();
      renderMessages();
    }
  });

  loadLocalMessages();
  initLocalSync();
  applyIdentity();
  renderMessages();
  els.messageList.scrollTop = els.messageList.scrollHeight;
  setLiveStatus(false, endpoint ? 'CONNECTING' : 'TEST MODE');
  if (!nickname) openNicknameModal();
  else if (endpoint) connectSocket();
})();
