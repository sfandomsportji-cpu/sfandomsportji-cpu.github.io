const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)e.target.classList.add('show')}),{threshold:.12});
document.querySelectorAll('.reveal').forEach(el=>io.observe(el));

(()=>{
  const player=document.getElementById('signaturePlayer');
  if(!player) return;
  const counter=document.getElementById('signatureCounter');
  const title=document.getElementById('signatureTitle');
  const sub=document.getElementById('signatureSub');
  const progress=document.getElementById('signatureProgress');
  const end=document.getElementById('signatureEnd');
  const dots=document.getElementById('signatureDots');
  const footLabel=document.querySelector('#signature-moments .signature-foot b');
  const MOMENT_MS=12000,END_MS=3200;
  const moments=[
    {a:'OHTANI',b:'50–50',sub:"MLB's first 50-HR / 50-SB season · 2024",start:0,gamePk:746011,exact:'shohei ohtani homers, creates the 50-50 club'},
    {a:'FREEMAN',b:'WALK-OFF SLAM',sub:'World Series Game 1 · October 25, 2024',start:5.2,date:'2024-10-25',away:147,home:119,exact:"freddie freeman's walk-off grand slam"},
    {a:'JUDGE',b:'300 HR',sub:'Fastest to 300 career home runs · August 14, 2024',start:0.15,date:'2024-08-14',away:147,home:145,exact:"aaron judge's 300th career homer (43)"},
    {a:'MILLER',b:"K'S THE SIDE",sub:'6th save · 30⅔-inning scoreless streak · April 16, 2026',start:44.5,ms:36000,gamePk:823313,exact:'miller strikes out side, extends scoreless streak'}
  ];
  const cache=new Map();
  let current=0,timer=null,endTimer=null,loadToken=0;
  const norm=s=>(s||'').trim().toLowerCase().replace(/[’‘]/g,"'").replace(/[–—]/g,'-').replace(/\s+/g,' ');
  if(end){end.classList.remove('show');end.style.transition='opacity 1.35s ease'}
  if(footLabel)footLabel.textContent=moments.length+' VERIFIED MOMENTS · AUTO PLAY';
  if(dots)dots.innerHTML='';
  moments.forEach((_,i)=>{const d=document.createElement('i');d.className='signature-dot'+(i===0?' active':'');dots.appendChild(d)});

  function tags(item){return (item.keywordsAll||[]).map(x=>norm(x.displayName||x.value||x.name)).join(' | ')}
  function choosePlayback(item){
    const all=(item.playbacks||[]).filter(p=>p&&p.url);
    const mp4=all.filter(p=>/\.mp4(?:\?|$)/i.test(p.url));
    const pool=mp4.length?mp4:all;
    pool.sort((a,b)=>((b.width||0)*(b.height||0))-((a.width||0)*(a.height||0)));
    return pool[0];
  }
  async function resolveGamePk(m){
    if(m.gamePk)return m.gamePk;
    const sr=await fetch(`https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=${m.date}`,{mode:'cors',cache:'no-store'});
    if(!sr.ok)throw new Error('schedule '+sr.status);
    const sd=await sr.json();
    const games=(sd.dates||[]).flatMap(d=>d.games||[]);
    const game=games.find(g=>g.teams?.away?.team?.id===m.away&&g.teams?.home?.team?.id===m.home);
    if(!game)throw new Error('gamePk not found');
    return game.gamePk;
  }
  async function resolveMoment(i){
    if(cache.has(i))return cache.get(i);
    const m=moments[i];
    const gamePk=await resolveGamePk(m);
    const r=await fetch(`https://statsapi.mlb.com/api/v1/game/${gamePk}/content`,{mode:'cors',cache:'no-store'});
    if(!r.ok)throw new Error('content '+r.status);
    const data=await r.json();
    const items=data?.highlights?.highlights?.items||[];
    let item=items.find(x=>norm(x.title)===norm(m.exact));
    if(!item)item=items.find(x=>norm(x.title).includes(norm(m.exact)));
    if(!item)throw new Error('exact in-game highlight not found');
    const k=tags(item);
    if(i>0&&k&&!k.includes('in-game highlight'))throw new Error('not in-game highlight');
    if(k&&(k.includes('interview')||k.includes('exclusive angle')||k.includes('statcast')||k.includes('data visualization')))throw new Error('banned highlight type');
    const t=norm(item.title);
    if(t.includes('field view')||t.includes('radio call')||t.includes('all calls')||t.includes('curtain call'))throw new Error('banned highlight title');
    const playback=choosePlayback(item);
    if(!playback?.url)throw new Error('playback not found');
    const out={url:playback.url,start:m.start||0};
    cache.set(i,out);
    return out;
  }
  function setMeta(i){
    const m=moments[i];
    counter.textContent='MOMENT '+String(i+1).padStart(2,'0')+' / '+String(moments.length).padStart(2,'0');
    title.innerHTML=m.a+'<br>'+m.b;
    sub.textContent=m.sub;
    progress.style.width=(((i+1)/moments.length)*100)+'%';
    [...dots.children].forEach((d,n)=>d.classList.toggle('active',n===i));
  }
  function clearPlayer(){player.pause();player.removeAttribute('src');player.load()}
  function scheduleNext(){clearTimeout(timer);timer=setTimeout(next,moments[current].ms||MOMENT_MS)}
  async function render(){
    clearTimeout(timer);clearTimeout(endTimer);
    if(end)end.classList.remove('show');
    const token=++loadToken;
    setMeta(current);
    clearPlayer();
    try{
      const v=await resolveMoment(current);
      if(token!==loadToken)return;
      player.src=v.url;
      player.muted=true;
      player.playsInline=true;
      const startPlayback=()=>{
        if(token!==loadToken)return;
        if(v.start>0&&Number.isFinite(player.duration)&&player.currentTime<v.start-.25){player.currentTime=Math.min(v.start,Math.max(0,player.duration-.5));return}
        player.play().catch(()=>{});
        scheduleNext();
        resolveMoment((current+1)%moments.length).catch(()=>{});
      };
      player.onloadedmetadata=startPlayback;
      player.onseeked=()=>{player.play().catch(()=>{});scheduleNext();resolveMoment((current+1)%moments.length).catch(()=>{})};
      player.onended=next;
      player.onerror=next;
    }catch(e){next()}
  }
  function next(){
    clearTimeout(timer);
    if(current===moments.length-1){
      clearPlayer();
      if(end)end.classList.add('show');
      endTimer=setTimeout(()=>{
        if(end)end.classList.remove('show');
        current=0;
        render();
      },END_MS);
    }else{
      current+=1;
      render();
    }
  }
  render();
})();

(()=>{
  const signature=document.getElementById('signature-moments');
  const pickSection=document.querySelector('section[aria-labelledby="pick-result-title"]');
  if(signature&&pickSection){
    signature.insertAdjacentElement('afterend',pickSection);
    pickSection.style.paddingTop='58px';
    pickSection.style.paddingBottom='58px';
    pickSection.innerHTML=`
      <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:28px;flex-wrap:wrap;margin-bottom:28px;">
        <div><p class="eyebrow">SFANDOM & KAIRO PICK ARCHIVE · 2026.08.25 KST</p><h2 id="pick-result-title" style="margin:8px 0 0;font-size:clamp(2rem,4vw,4.2rem);line-height:.96;letter-spacing:-.05em;">결과까지 남겨야,<br><span style="color:#ef2d2d;">기록이 됩니다.</span></h2></div>
        <p style="max-width:460px;margin:0;color:#a7a7a7;line-height:1.75;">적중만 골라 보여주지 않습니다. 기준선에서 얼마나 벗어났는지까지 그대로 기록합니다.</p>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;">
        <a href="archive/picks/#pick-001" aria-label="픽 1 말라가 데포르티보 오버 2.5 복기" style="display:block;padding:28px;border:1px solid #493438;background:linear-gradient(145deg,#12090b,#080809 72%);text-decoration:none;color:#fff;">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;"><span style="padding:7px 9px;border:1px solid #5d4146;color:#ff777c;font-size:.62rem;font-weight:900;letter-spacing:.12em;">PICK 01 · REVIEW</span><b style="color:#ff777c;font-size:.72rem;letter-spacing:.1em;">MISS · −0.5</b></div>
          <p style="margin:26px 0 7px;color:#777b84;font-size:.68rem;font-weight:900;letter-spacing:.1em;">FOOTBALL · MÁLAGA · DEPORTIVO</p>
          <h3 style="margin:0;font-size:clamp(2rem,4vw,3.4rem);letter-spacing:-.055em;">OVER 2.5</h3>
          <div style="display:flex;justify-content:space-between;gap:18px;margin:20px 0;padding:18px 0;border-top:1px solid #332b2d;border-bottom:1px solid #332b2d;"><span style="color:#999da5;">FINAL TOTAL</span><strong style="font-size:1.55rem;">2 GOALS</strong></div>
          <p style="margin:0;color:#b5b7bd;line-height:1.75;"><b style="color:#fff;">0.5 차이로 미적중.</b> 2.5 기준선에서 단 반 골이 부족했습니다. 아쉬운 결과까지 그대로 남기며, 관리 중인 누적 공개 픽 기준 <b style="color:#f0cf57;">적중률 90%를 유지</b>합니다.</p>
        </a>
        <a href="analysis.html" aria-label="픽 2 탬파베이 승" style="display:block;padding:28px;border:1px solid #303943;background:linear-gradient(145deg,#091019,#080809 72%);text-decoration:none;color:#fff;">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;"><span style="padding:7px 9px;border:1px solid #31475f;color:#77bfff;font-size:.62rem;font-weight:900;letter-spacing:.12em;">PICK 02 · MLB</span><b style="color:#77bfff;font-size:.72rem;letter-spacing:.1em;">CURRENT</b></div>
          <p style="margin:26px 0 7px;color:#777b84;font-size:.68rem;font-weight:900;letter-spacing:.1em;">TAMPA BAY RAYS @ DETROIT TIGERS</p>
          <h3 style="margin:0;font-size:clamp(2rem,4vw,3.4rem);letter-spacing:-.055em;">TAMPA BAY WIN</h3>
          <div style="display:flex;justify-content:space-between;gap:18px;margin:20px 0;padding:18px 0;border-top:1px solid #29313a;border-bottom:1px solid #29313a;"><span style="color:#999da5;">MARKET</span><strong style="font-size:1.55rem;">ML · SINGLE</strong></div>
          <p style="margin:0;color:#b5b7bd;line-height:1.75;">오늘은 여러 시장을 섞지 않고 <b style="color:#fff;">탬파베이 승 한 방향</b>으로만 선택했습니다. 상세 근거와 실제 게시 시각은 분석 페이지에 그대로 남깁니다.</p>
        </a>
      </div>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:18px;padding-top:16px;border-top:1px solid #222;"><a href="archive/picks/" aria-label="SFANDOM and KAIRO picks archive" style="display:inline-flex;align-items:center;justify-content:center;min-width:178px;height:40px;padding:0 16px;border:1px solid #393939;background:#0b0b0c;color:#fff;text-decoration:none;font-size:.72rem;font-weight:900;letter-spacing:.08em;">SFANDOM&KAIRO픽</a></div>`;
  }

  const mediaRow=document.querySelector('[aria-label="미디어 기록 바로가기"]');
  if(mediaRow){
    const numbered=[...mediaRow.querySelectorAll('a[href*="archive/media/#media-"]')];
    numbered.slice(3).forEach(a=>a.remove());
  }
})();

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