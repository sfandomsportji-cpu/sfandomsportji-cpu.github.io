(()=>{
  const dock=document.getElementById('sfLiveDock');
  if(!dock)return;

  const MSG_KEY='sfandom_live_messages_v01';
  const NICK_KEY='sfandom_live_nickname_v01';
  const CLIENT_KEY='sfandom_live_client_v01';
  const MAX_MESSAGES=100;
  const DOCK_MESSAGES=3;
  let channel=null,lastSent=0;
  let clientId=localStorage.getItem(CLIENT_KEY)||'';
  if(!clientId){clientId=crypto.randomUUID();localStorage.setItem(CLIENT_KEY,clientId)}

  const feed=dock.querySelector('[data-feed]');
  const form=dock.querySelector('form');
  const identity=dock.querySelector('[data-identity]');
  const collapse=dock.querySelector('[data-collapse]');
  if(!feed||!form||!identity||!collapse)return;
  const input=form.querySelector('input');
  const nickInput=identity.querySelector('input');
  if(!input||!nickInput)return;

  const mobileQuery=window.matchMedia('(max-width:520px)');
  function syncCollapseUi(){
    const closed=dock.classList.contains('is-collapsed');
    collapse.textContent=closed?(mobileQuery.matches?'LIVE':'+'):'—';
    collapse.setAttribute('aria-label',closed?'채팅 열기':'채팅창 접기');
    dock.setAttribute('aria-expanded',String(!closed));
  }

  dock.classList.add('is-collapsed');
  syncCollapseUi();

  function cleanNick(v){return String(v||'').replace(/[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ ._-]/g,'').replace(/\s+/g,' ').trim().slice(0,18)}
  function getStoredMessages(){try{const x=JSON.parse(localStorage.getItem(MSG_KEY)||'[]');return Array.isArray(x)?x.slice(-MAX_MESSAGES):[]}catch{return[]}}
  function saveMessages(messages){localStorage.setItem(MSG_KEY,JSON.stringify(messages.slice(-MAX_MESSAGES)))}
  function render(){
    const list=getStoredMessages().slice(-DOCK_MESSAGES);
    feed.replaceChildren();
    if(!list.length){
      const e=document.createElement('div');
      e.className='sf-live-empty';
      e.textContent='아직 대화가 없습니다.\n첫 메시지를 남겨보세요.';
      feed.appendChild(e);
      return;
    }
    list.forEach(m=>{
      const el=document.createElement('div');
      el.className='sf-live-mini';
      const meta=document.createElement('div');
      meta.className='sf-live-mini-meta';
      const b=document.createElement('b');
      b.textContent=m.nickname||'Guest';
      const tag=document.createElement('span');
      tag.textContent=m.topic||'GENERAL';
      const p=document.createElement('p');
      p.textContent=m.text||'';
      meta.append(b,tag);
      el.append(meta,p);
      feed.appendChild(el);
    });
    feed.scrollTop=feed.scrollHeight;
  }
  function ensureNick(){
    const nick=cleanNick(localStorage.getItem(NICK_KEY)||'');
    if(nick)return nick;
    identity.hidden=false;
    nickInput.focus();
    return'';
  }
  function saveNick(){
    const nick=cleanNick(nickInput.value);
    if(nick.length<2)return'';
    localStorage.setItem(NICK_KEY,nick);
    identity.hidden=true;
    return nick;
  }
  function send(){
    let nick=ensureNick();
    if(!nick){nick=saveNick();if(!nick)return}
    const text=input.value.trim();
    if(!text)return;
    const now=Date.now();
    if(now-lastSent<2500)return;
    const list=getStoredMessages();
    const msg={id:crypto.randomUUID(),nickname:nick,clientId,topic:'GENERAL',text:text.slice(0,300),createdAt:now};
    list.push(msg);
    saveMessages(list);
    channel?.postMessage({type:'message',message:msg});
    lastSent=now;
    input.value='';
    render();
  }

  form.addEventListener('submit',e=>{e.preventDefault();send()});
  nickInput.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();const n=saveNick();if(n)input.focus()}});
  collapse.addEventListener('click',()=>{dock.classList.toggle('is-collapsed');syncCollapseUi()});
  const handleMobileChange=()=>{if(mobileQuery.matches)dock.classList.add('is-collapsed');syncCollapseUi()};
  if(mobileQuery.addEventListener)mobileQuery.addEventListener('change',handleMobileChange);else mobileQuery.addListener(handleMobileChange);
  window.addEventListener('orientationchange',()=>{if(mobileQuery.matches){dock.classList.add('is-collapsed');syncCollapseUi()}});
  window.addEventListener('storage',e=>{if(e.key===MSG_KEY)render()});
  if('BroadcastChannel'in window){
    channel=new BroadcastChannel('sfandom-live-v01');
    channel.addEventListener('message',e=>{
      if(e.data?.type==='message'){
        const list=getStoredMessages();
        if(!list.some(x=>x.id===e.data.message.id)){
          list.push(e.data.message);
          saveMessages(list);
        }
        render();
      }
    });
  }
  render();
})();
