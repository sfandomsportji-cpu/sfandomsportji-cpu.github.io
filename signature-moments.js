const revealNodes=[...document.querySelectorAll('.reveal')];
if('IntersectionObserver' in window){
  const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)e.target.classList.add('show')}),{threshold:.12});
  revealNodes.forEach(el=>io.observe(el));
}else{
  revealNodes.forEach(el=>el.classList.add('show'));
}

const startSignatureMoments=()=>{
  const player=document.getElementById('signaturePlayer');
  const counter=document.getElementById('signatureCounter');
  const title=document.getElementById('signatureTitle');
  const sub=document.getElementById('signatureSub');
  const progress=document.getElementById('signatureProgress');
  const end=document.getElementById('signatureEnd');
  const dots=document.getElementById('signatureDots');
  if(!player||!counter||!title||!sub||!progress||!end||!dots)return;
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

  end.classList.remove('show');
  if(footLabel)footLabel.textContent=moments.length+' VERIFIED MOMENTS · AUTO PLAY';
  dots.replaceChildren();
  moments.forEach((_,i)=>{
    const d=document.createElement('i');
    d.className='signature-dot'+(i===0?' active':'');
    dots.appendChild(d);
  });

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
    title.replaceChildren(document.createTextNode(m.a),document.createElement('br'),document.createTextNode(m.b));
    sub.textContent=m.sub;
    progress.style.width=(((i+1)/moments.length)*100)+'%';
    [...dots.children].forEach((d,n)=>d.classList.toggle('active',n===i));
  }
  function clearPlayer(){player.pause();player.removeAttribute('src');player.load()}
  function scheduleNext(){clearTimeout(timer);timer=setTimeout(next,moments[current].ms||MOMENT_MS)}
  async function render(){
    clearTimeout(timer);clearTimeout(endTimer);
    end.classList.remove('show');
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
      end.classList.add('show');
      endTimer=setTimeout(()=>{
        end.classList.remove('show');
        current=0;
        render();
      },END_MS);
    }else{
      current+=1;
      render();
    }
  }
  render();
};

const signatureSection=document.getElementById('signature-moments');
if(signatureSection&&'IntersectionObserver'in window){
  const signatureIo=new IntersectionObserver(entries=>{
    if(entries.some(entry=>entry.isIntersecting)){
      signatureIo.disconnect();
      startSignatureMoments();
    }
  },{rootMargin:'500px 0px',threshold:0});
  signatureIo.observe(signatureSection);
}else{
  startSignatureMoments();
}

const loadSecondary=()=>{
  import('./brand-film-touch.js?v=20260903-one-tap1').catch(()=>{});
  import('./visitor-counter-bootstrap.js?v=20260904-1').catch(()=>{});
};
if('requestIdleCallback'in window){requestIdleCallback(loadSecondary,{timeout:1200})}
else{setTimeout(loadSecondary,350)}
