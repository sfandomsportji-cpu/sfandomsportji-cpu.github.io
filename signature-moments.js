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
  const MOMENT_MS=12000;
  const moments=[
    {a:'OHTANI',b:'50–50',sub:"MLB's first 50-HR / 50-SB season · 2024",start:0,gamePk:746011,exact:'shohei ohtani homers, creates the 50-50 club'},
    {a:'FREEMAN',b:'WALK-OFF SLAM',sub:'World Series Game 1 · October 25, 2024',start:5.2,date:'2024-10-25',away:147,home:119,exact:"freddie freeman's walk-off grand slam"},
    {a:'JUDGE',b:'300 HR',sub:'Fastest to 300 career home runs · August 14, 2024',start:0.15,date:'2024-08-14',away:147,home:145,exact:"aaron judge's 300th career homer (43)"},
    {a:'MILLER',b:'FINAL OUT',sub:'Final game at Oakland Coliseum · September 26, 2024',start:0,date:'2024-09-26',away:140,home:133,exact:'mason miller closes out final oakland coliseum game'}
  ];
  const cache=new Map();
  let current=0,timer=null,loadToken=0;
  const norm=s=>(s||'').trim().toLowerCase().replace(/[’‘]/g,"'").replace(/[–—]/g,'-').replace(/\s+/g,' ');
  if(end)end.classList.remove('show');
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
  function scheduleNext(){clearTimeout(timer);timer=setTimeout(next,MOMENT_MS)}
  async function render(){
    clearTimeout(timer);
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
    current=(current+1)%moments.length;
    render();
  }
  render();
})();