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
        <p style="max-width:460px;margin:0;color:#a7a7a7;line-height:1.75;">맞은 픽도, 빗나간 픽도 같은 기준으로 기록합니다. 오늘 탬파베이 단통은 4–1로 깔끔하게 적중했습니다.</p>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;">
        <a href="archive/picks/#pick-001" aria-label="픽 1 말라가 데포르티보 오버 2.5 복기" style="display:block;padding:28px;border:1px solid #493438;background:linear-gradient(145deg,#12090b,#080809 72%);text-decoration:none;color:#fff;">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;"><span style="padding:7px 9px;border:1px solid #5d4146;color:#ff777c;font-size:.62rem;font-weight:900;letter-spacing:.12em;">PICK 01 · REVIEW</span><b style="color:#ff777c;font-size:.72rem;letter-spacing:.1em;">MISS · −0.5</b></div>
          <p style="margin:26px 0 7px;color:#777b84;font-size:.68rem;font-weight:900;letter-spacing:.1em;">FOOTBALL · MÁLAGA · DEPORTIVO</p>
          <h3 style="margin:0;font-size:clamp(2rem,4vw,3.4rem);letter-spacing:-.055em;">OVER 2.5</h3>
          <div style="display:flex;justify-content:space-between;gap:18px;margin:20px 0;padding:18px 0;border-top:1px solid #332b2d;border-bottom:1px solid #332b2d;"><span style="color:#999da5;">FINAL TOTAL</span><strong style="font-size:1.55rem;">2 GOALS</strong></div>
          <p style="margin:0;color:#b5b7bd;line-height:1.75;"><b style="color:#fff;">0.5 차이로 미적중.</b> 2.5 기준선에서 단 반 골이 부족했습니다. 아쉬운 결과까지 그대로 남기며, 관리 중인 누적 공개 픽 기준 <b style="color:#f0cf57;">적중률 90%를 유지</b>합니다.</p>
        </a>
        <a href="archive/picks/#pick-002" aria-label="픽 2 탬파베이 승 적중" style="display:block;overflow:hidden;border:1px solid #2f7651;background:linear-gradient(145deg,#07160f,#080809 76%);text-decoration:none;color:#fff;">
          <div style="position:relative;height:245px;overflow:hidden;background:#081019;">
            <img src="https://img.mlbstatic.com/mlb-photos/image/upload/w_900,q_auto:best/v1/people/656876/headshot/67/current" alt="탬파베이 선발 드류 라스무센" loading="lazy" style="width:100%;height:100%;object-fit:cover;object-position:50% 12%;filter:saturate(.9) contrast(1.04);">
            <div style="position:absolute;inset:0;background:linear-gradient(90deg,rgba(4,10,8,.95) 0%,rgba(4,10,8,.42) 52%,rgba(4,10,8,.12) 100%);"></div>
            <div style="position:absolute;left:22px;top:20px;padding:7px 9px;border:1px solid #2f7651;background:rgba(7,22,15,.88);color:#70e6a5;font-size:.64rem;font-weight:900;letter-spacing:.14em;">HIT ✓ · MLB</div>
            <div style="position:absolute;left:22px;bottom:20px;"><small style="display:block;color:#8fc3a8;font-size:.62rem;font-weight:900;letter-spacing:.12em;">FINAL SCORE</small><strong style="display:block;margin-top:4px;font-size:clamp(2.7rem,6vw,5rem);line-height:.88;letter-spacing:-.065em;">TB 4–1 DET</strong></div>
          </div>
          <div style="padding:26px 28px 28px;">
            <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;"><span style="padding:7px 9px;border:1px solid #2f7651;color:#70e6a5;font-size:.62rem;font-weight:900;letter-spacing:.12em;">PICK 02 · RESULT</span><b style="color:#70e6a5;font-size:.72rem;letter-spacing:.1em;">TAMPA BAY WIN ✓</b></div>
            <p style="margin:24px 0 7px;color:#777b84;font-size:.68rem;font-weight:900;letter-spacing:.1em;">RASMUSSEN · 6 IP · 3 H · 1 ER · 0 BB · 5 K</p>
            <h3 style="margin:0;font-size:clamp(2rem,4vw,3.4rem);letter-spacing:-.055em;">ML · SINGLE HIT</h3>
            <p style="margin:18px 0 0;color:#b5b7bd;line-height:1.75;">선발 매치업에서 본 우위가 그대로 경기 구조로 연결됐습니다. <b style="color:#fff;">라스무센이 6이닝 1실점으로 버티고, 탬파가 1회부터 잡은 리드를 끝까지 지켰습니다.</b> 단통 한 방향, 시원하게 적중.</p>
          </div>
        </a>
      </div>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:18px;padding-top:16px;border-top:1px solid #222;"><span style="margin-right:8px;color:#777;font-size:.62rem;font-weight:900;letter-spacing:.14em;">PICK ARCHIVE</span><a href="archive/picks/#pick-001" style="display:grid;place-items:center;width:40px;height:40px;border:1px solid #ef2d2d;background:#17090b;color:#fff;text-decoration:none;font-size:.72rem;font-weight:900;">01</a><a href="archive/picks/#pick-002" style="display:grid;place-items:center;width:40px;height:40px;border:1px solid #2f7651;background:#07160f;color:#70e6a5;text-decoration:none;font-size:.72rem;font-weight:900;">02</a><a href="archive/picks/#pick-003" style="display:grid;place-items:center;width:40px;height:40px;border:1px solid #393939;background:#0b0b0c;color:#fff;text-decoration:none;font-size:.72rem;font-weight:900;">03</a><a href="archive/picks/" style="margin-left:5px;color:#aaa;text-decoration:none;font-size:.66rem;font-weight:800;letter-spacing:.08em;">전체 기록 →</a></div>`;
  }

  const mediaRow=document.querySelector('[aria-label="미디어 기록 바로가기"]');
  if(mediaRow){
    const numbered=[...mediaRow.querySelectorAll('a[href*="archive/media/#media-"]')];
    numbered.slice(3).forEach(a=>a.remove());
  }
})();