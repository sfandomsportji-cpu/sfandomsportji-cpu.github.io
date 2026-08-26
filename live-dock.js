(()=>{
  const isHome=location.pathname==='/'||location.pathname.endsWith('/index.html');
  if(!isHome||document.getElementById('sfLiveDock'))return;

  const MSG_KEY='sfandom_live_messages_v01';
  const NICK_KEY='sfandom_live_nickname_v01';
  const CLIENT_KEY='sfandom_live_client_v01';
  let channel=null,lastSent=0;
  let clientId=localStorage.getItem(CLIENT_KEY)||'';
  if(!clientId){clientId=crypto.randomUUID();localStorage.setItem(CLIENT_KEY,clientId)}

  const style=document.createElement('style');
  style.textContent=`
  .sf-live-dock{position:fixed;right:22px;top:86px;z-index:7200;width:342px;border:1px solid #34343a;background:rgba(8,8,10,.96);box-shadow:0 24px 70px rgba(0,0,0,.48);backdrop-filter:blur(16px);font-family:Inter,'Noto Sans KR',sans-serif;color:#fff;overflow:hidden}
  .sf-live-dock *{box-sizing:border-box}.sf-live-dock-head{height:54px;display:flex;align-items:center;justify-content:space-between;padding:0 14px 0 16px;border-bottom:1px solid #242429;background:linear-gradient(90deg,#120809,#09090b)}
  .sf-live-dock-title{display:flex;align-items:center;gap:9px}.sf-live-dock-title i{width:8px;height:8px;border-radius:50%;background:#ef2d2d;box-shadow:0 0 0 5px rgba(239,45,45,.12);animation:sfLivePulse 1.8s infinite}.sf-live-dock-title strong{font-size:.76rem;letter-spacing:.09em}.sf-live-dock-title span{color:#ef5b60;font-size:.58rem;font-weight:900;letter-spacing:.12em}
  .sf-live-dock-actions{display:flex;gap:6px}.sf-live-dock-actions a,.sf-live-dock-actions button{display:grid;place-items:center;width:30px;height:30px;border:1px solid #303037;background:#0c0c0f;color:#aeb0b7;text-decoration:none;font:800 .76rem/1 Inter;cursor:pointer}.sf-live-dock-actions a:hover,.sf-live-dock-actions button:hover{border-color:#ef2d2d;color:#fff}
  .sf-live-dock-body{padding:12px}.sf-live-dock.is-collapsed .sf-live-dock-body{display:none}.sf-live-dock-feed{display:grid;gap:7px;min-height:114px;max-height:170px;overflow:auto;padding-right:2px}.sf-live-mini{padding:9px 10px;border:1px solid #24242a;background:#0d0d10}.sf-live-mini-meta{display:flex;align-items:center;gap:6px;margin-bottom:4px}.sf-live-mini-meta b{font-size:.66rem}.sf-live-mini-meta span{padding:2px 4px;border:1px solid #3b2a2d;color:#f07176;font-size:.5rem;font-weight:900}.sf-live-mini p{margin:0;color:#b9bac0;font-size:.68rem;line-height:1.45;word-break:break-word}.sf-live-empty{display:grid;place-items:center;min-height:114px;border:1px dashed #2f2f35;color:#777b83;font-size:.66rem;text-align:center}
  .sf-live-dock-identity{display:flex;gap:7px;margin-top:9px}.sf-live-dock-identity input{width:100%;height:34px;border:1px solid #303038;background:#09090b;color:#fff;padding:0 10px;font:700 .68rem/1 Inter,'Noto Sans KR',sans-serif;outline:none}.sf-live-dock-identity input:focus{border-color:#ef2d2d}
  .sf-live-dock-form{display:grid;grid-template-columns:1fr 52px;gap:7px;margin-top:8px}.sf-live-dock-form input{height:39px;border:1px solid #303038;background:#09090b;color:#fff;padding:0 11px;font:600 .7rem/1 Inter,'Noto Sans KR',sans-serif;outline:none}.sf-live-dock-form input:focus{border-color:#ef2d2d}.sf-live-dock-form button{border:0;background:#ef2d2d;color:#fff;font:900 .65rem/1 Inter;cursor:pointer}.sf-live-dock-foot{display:flex;justify-content:space-between;gap:10px;margin-top:8px;color:#6f727a;font-size:.54rem;font-weight:800;letter-spacing:.04em}.sf-live-dock-foot a{color:#9c9fa7;text-decoration:none}.sf-live-dock-foot a:hover{color:#fff}
  @keyframes sfLivePulse{0%,100%{opacity:1}50%{opacity:.45}}
  @media(max-width:820px){.sf-live-dock{top:72px;right:10px;width:min(310px,calc(100vw - 20px))}.sf-live-dock:not(.is-collapsed){max-height:430px}.sf-live-dock-feed{max-height:128px}.sf-live-dock-title span{display:none}}
  @media(max-width:520px){.sf-live-dock{top:auto;bottom:74px;right:10px;width:min(295px,calc(100vw - 20px))}.sf-live-dock.is-collapsed{width:165px}.sf-live-dock.is-collapsed .sf-live-dock-head{border-bottom:0}.sf-live-dock-head{height:48px}}
  `;
  document.head.appendChild(style);

  const dock=document.createElement('aside');
  dock.id='sfLiveDock';dock.className='sf-live-dock';dock.setAttribute('aria-label','SFANDOM LIVE 미니 채팅');
  dock.innerHTML=`<div class="sf-live-dock-head"><div class="sf-live-dock-title"><i></i><strong>SFANDOM LIVE</strong><span>OPEN BETA</span></div><div class="sf-live-dock-actions"><a href="live.html" aria-label="전체 채팅 열기">↗</a><button type="button" data-collapse aria-label="채팅창 접기">—</button></div></div><div class="sf-live-dock-body"><div class="sf-live-dock-feed" data-feed></div><div class="sf-live-dock-identity" data-identity hidden><input type="text" maxlength="18" placeholder="닉네임을 먼저 정해주세요"></div><form class="sf-live-dock-form"><input type="text" maxlength="300" placeholder="경기 이야기를 남겨보세요…" aria-label="채팅 메시지"><button type="submit">SEND</button></form><div class="sf-live-dock-foot"><span>GUEST CHAT · TEST MODE</span><a href="live.html">전체 채팅 보기 →</a></div></div>`;
  document.body.appendChild(dock);

  const feed=dock.querySelector('[data-feed]');
  const form=dock.querySelector('form');
  const input=form.querySelector('input');
  const identity=dock.querySelector('[data-identity]');
  const nickInput=identity.querySelector('input');
  const collapse=dock.querySelector('[data-collapse]');

  function cleanNick(v){return String(v||'').replace(/[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ ._-]/g,'').replace(/\s+/g,' ').trim().slice(0,18)}
  function getMessages(){try{const x=JSON.parse(localStorage.getItem(MSG_KEY)||'[]');return Array.isArray(x)?x.slice(-3):[]}catch{return[]}}
  function render(){
    const list=getMessages();feed.replaceChildren();
    if(!list.length){const e=document.createElement('div');e.className='sf-live-empty';e.textContent='아직 대화가 없습니다.\n첫 메시지를 남겨보세요.';feed.appendChild(e);return}
    list.forEach(m=>{const el=document.createElement('div');el.className='sf-live-mini';const meta=document.createElement('div');meta.className='sf-live-mini-meta';const b=document.createElement('b');b.textContent=m.nickname||'Guest';const tag=document.createElement('span');tag.textContent=m.topic||'GENERAL';const p=document.createElement('p');p.textContent=m.text||'';meta.append(b,tag);el.append(meta,p);feed.appendChild(el)});feed.scrollTop=feed.scrollHeight;
  }
  function ensureNick(){
    let nick=cleanNick(localStorage.getItem(NICK_KEY)||'');
    if(nick)return nick;
    identity.hidden=false;nickInput.focus();return'';
  }
  function saveNick(){const nick=cleanNick(nickInput.value);if(nick.length<2)return'';localStorage.setItem(NICK_KEY,nick);identity.hidden=true;return nick}
  function send(){
    let nick=ensureNick();if(!nick){nick=saveNick();if(!nick)return}
    const text=input.value.trim();if(!text)return;
    const now=Date.now();if(now-lastSent<2500)return;
    const list=getMessages();const msg={id:crypto.randomUUID(),nickname:nick,clientId,topic:'GENERAL',text:text.slice(0,300),createdAt:now};
    list.push(msg);localStorage.setItem(MSG_KEY,JSON.stringify(list.slice(-100)));channel?.postMessage({type:'message',message:msg});lastSent=now;input.value='';render();
  }
  form.addEventListener('submit',e=>{e.preventDefault();send()});
  nickInput.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();const n=saveNick();if(n)input.focus()}});
  collapse.addEventListener('click',()=>{dock.classList.toggle('is-collapsed');collapse.textContent=dock.classList.contains('is-collapsed')?'+':'—'});
  window.addEventListener('storage',e=>{if(e.key===MSG_KEY)render()});
  if('BroadcastChannel'in window){channel=new BroadcastChannel('sfandom-live-v01');channel.addEventListener('message',e=>{if(e.data?.type==='message'){const list=getMessages();if(!list.some(x=>x.id===e.data.message.id)){list.push(e.data.message);localStorage.setItem(MSG_KEY,JSON.stringify(list.slice(-100)))}render()}})}
  render();
})();
