(()=>{
  const tracks=[
    {src:'/assets/music/sfandom-energy-01-danceable-funky-indie-pop.mp3',title:'Danceable Funky Indie Pop',artist:'Sound_For_You',source:'https://pixabay.com/music/funk-upbeat-danceable-funky-indie-pop-energetic-dance-funky-catchy-473869/'},
    {src:'/assets/music/sfandom-energy-02-pop-punk-rock.mp3',title:'Pop Punk Rock Music',artist:'lNPLUSMUSIC',source:'https://pixabay.com/music/rock-pop-punk-rock-music-469456/'},
    {src:'/assets/music/sfandom-energy-03-uplifting-fun-indie-pop-rock.mp3',title:'Uplifting Fun Indie Pop Rock',artist:'Sound_For_You',source:'https://pixabay.com/music/acoustic-group-uplifting-fun-indie-pop-rock-funky-guitar-riff-fun-youthful-vibe-484929/'},
    {src:'/assets/music/sfandom-energy-04-upbeat-party-pop.mp3',title:'Upbeat Party Pop',artist:'Sound_For_You',source:'https://pixabay.com/music/electronic-upbeat-party-pop-energetic-indie-pop-with-catchy-guitars-487926/'},
    {src:'/assets/music/sfandom-energy-05-happy-indie-pop.mp3',title:'Happy Indie Pop',artist:'Sound_For_You',source:'https://pixabay.com/music/acoustic-group-happy-indie-pop-energetic-upbeat-uplifting-catchy-indie-pop-487485/'}
  ];

  const K={index:'sfandomMusicIndexV4',time:'sfandomMusicTimeV4'};
  const get=(k,f)=>{try{const v=localStorage.getItem(k);return v===null?f:v}catch{return f}};
  const set=(k,v)=>{try{localStorage.setItem(k,String(v))}catch{}};
  let index=Math.max(0,Math.min(tracks.length-1,parseInt(get(K.index,'0'),10)||0));
  let restoreTime=Math.max(0,parseFloat(get(K.time,'0'))||0);
  let lastSave=0;
  let routing=false;

  const audio=new Audio();
  audio.preload='metadata';
  audio.autoplay=false;
  audio.playsInline=true;
  audio.volume=.22;

  const shell=document.createElement('aside');
  shell.className='sf-music-player';
  shell.setAttribute('aria-label','SFANDOM music player');
  shell.innerHTML=`
    <div class="sf-music-main">
      <button type="button" class="sf-music-now" data-list aria-expanded="false" aria-label="Choose a track">
        <span class="sf-music-bars" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span class="sf-music-copy"><b>SFANDOM RADIO</b><small id="sfMusicTitle">FUNK POP</small></span>
        <span class="sf-music-chevron" aria-hidden="true">⌃</span>
      </button>
      <div class="sf-music-actions">
        <button type="button" data-prev aria-label="Previous track">‹</button>
        <button type="button" class="sf-music-toggle" data-toggle aria-label="Play selected track">▶</button>
        <button type="button" data-next aria-label="Next track">›</button>
      </div>
    </div>
    <div class="sf-music-list" data-track-list hidden>
      <div class="sf-music-list-head"><span>CHOOSE TRACK</span><small>재생할 음악을 선택하세요</small></div>
      ${tracks.map((t,i)=>`<button type="button" data-track="${i}"><span>${String(i+1).padStart(2,'0')}</span><b>${t.title}</b><small>${t.artist}</small></button>`).join('')}
    </div>`;
  document.body.appendChild(shell);

  const titleEl=shell.querySelector('#sfMusicTitle');
  const toggle=shell.querySelector('[data-toggle]');
  const listBtn=shell.querySelector('[data-list]');
  const list=shell.querySelector('[data-track-list]');

  function updateUI(){
    const t=tracks[index];
    const playing=!audio.paused&&!audio.ended;
    titleEl.textContent=`${String(index+1).padStart(2,'0')} · ${t.title}`;
    titleEl.title=`${t.title} — ${t.artist}`;
    shell.classList.toggle('is-playing',playing);
    shell.classList.toggle('is-open',!list.hidden);
    toggle.textContent=playing?'Ⅱ':'▶';
    toggle.setAttribute('aria-label',playing?'Pause music':'Play selected track');
    listBtn.setAttribute('aria-expanded',String(!list.hidden));
    shell.querySelectorAll('[data-track]').forEach((btn,i)=>btn.classList.toggle('is-active',i===index));
  }

  function persist(){
    set(K.index,index);
    set(K.time,Number.isFinite(audio.currentTime)?audio.currentTime:0);
  }

  function loadCurrent({resume=false,play=false}={}){
    const t=tracks[index];
    audio.pause();
    audio.src=t.src;
    audio.load();
    const ready=()=>{
      if(resume&&restoreTime>0&&Number.isFinite(audio.duration)&&restoreTime<audio.duration-2){try{audio.currentTime=restoreTime}catch{}}
      restoreTime=0;
      if(play)audio.play().catch(()=>{});
      updateUI();
    };
    audio.addEventListener('loadedmetadata',ready,{once:true});
    updateUI();
  }

  function selectTrack(nextIndex){
    persist();
    index=nextIndex;
    restoreTime=0;
    set(K.index,index);set(K.time,'0');
    list.hidden=true;
    loadCurrent({play:true});
  }

  function move(delta){selectTrack((index+delta+tracks.length)%tracks.length)}

  listBtn.addEventListener('click',e=>{e.stopPropagation();list.hidden=!list.hidden;updateUI()});
  shell.querySelectorAll('[data-track]').forEach(btn=>btn.addEventListener('click',e=>{e.stopPropagation();selectTrack(parseInt(btn.dataset.track,10))}));
  shell.querySelector('[data-prev]').addEventListener('click',e=>{e.stopPropagation();move(-1)});
  shell.querySelector('[data-next]').addEventListener('click',e=>{e.stopPropagation();move(1)});
  toggle.addEventListener('click',e=>{
    e.stopPropagation();
    if(!audio.src){loadCurrent({play:true});return}
    if(audio.paused)audio.play().catch(()=>{});else audio.pause();
    updateUI();
  });

  document.addEventListener('click',e=>{if(!shell.contains(e.target)&&!list.hidden){list.hidden=true;updateUI()}});
  audio.addEventListener('play',updateUI);
  audio.addEventListener('pause',updateUI);
  audio.addEventListener('ended',()=>move(1));
  audio.addEventListener('timeupdate',()=>{const now=Date.now();if(now-lastSave>5000){lastSave=now;persist()}});
  audio.addEventListener('error',()=>{shell.classList.add('has-error');setTimeout(()=>shell.classList.remove('has-error'),1200)});
  window.addEventListener('pagehide',persist);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)persist()});

  function enhanceChrome(){
    const header=document.querySelector('.site-header');
    const nav=header?.querySelector('.nav');
    if(nav&&!nav.querySelector('a[href="/preamble.html"],a[href="preamble.html"],a[href="../preamble.html"]')){
      const link=document.createElement('a');
      link.href='/preamble.html';
      link.textContent='PREAMBLE';
      const about=[...nav.querySelectorAll('a')].find(a=>/about\.html(?:$|[?#])/.test(a.getAttribute('href')||''));
      if(about)nav.insertBefore(link,about);else nav.appendChild(link);
    }
    if(nav){
      [...nav.querySelectorAll('a')].forEach(a=>{
        const href=a.getAttribute('href')||'';
        if(/analysis\.html(?:$|[?#])/.test(href))a.textContent='ANALYSIS';
        else if(/content\.html(?:$|[?#])/.test(href))a.textContent='CONTENT';
        else if(/(?:^|\/)archive\/?(?:$|[?#])/.test(href)||href==='archive/'||href==='./')a.textContent='ARCHIVE';
        else if(/preamble\.html(?:$|[?#])/.test(href))a.textContent='PREAMBLE';
        else if(/about\.html(?:$|[?#])/.test(href))a.textContent='ABOUT';
      });
    }
    if(header){
      let cta=header.querySelector('.header-cta');
      if(!cta){
        cta=document.createElement('a');
        cta.className='header-cta';
        cta.href='/analysis.html';
        header.appendChild(cta);
      }
      cta.textContent='ENTER LAB ↗';
    }

    const footer=document.querySelector('.footer-links');
    if(footer){
      if(!footer.querySelector('a[href="/preamble.html"],a[href="preamble.html"],a[href="../preamble.html"]')){
        const link=document.createElement('a');link.href='/preamble.html';link.textContent='전문';
        const about=[...footer.querySelectorAll('a')].find(a=>/about\.html(?:$|[?#])/.test(a.getAttribute('href')||'')||a.textContent.trim()==='소개');
        if(about)footer.insertBefore(link,about);else footer.appendChild(link);
      }
      if(!footer.querySelector('a[href="/legal.html"],a[href="legal.html"],a[href="../legal.html"]')){
        const legal=document.createElement('a');legal.href='/legal.html';legal.textContent='운영·법률';footer.appendChild(legal);
      }
      if(!footer.querySelector('a[href="/terms.html"],a[href="terms.html"],a[href="../terms.html"]')){
        const terms=document.createElement('a');terms.href='/terms.html';terms.textContent='이용약관';footer.appendChild(terms);
      }
      if(!footer.querySelector('a[href="/privacy.html"],a[href="privacy.html"],a[href="../privacy.html"]')){
        const privacy=document.createElement('a');privacy.href='/privacy.html';privacy.textContent='개인정보 처리방침';footer.appendChild(privacy);
      }
    }
  }

  function enhanceHome(){
    const isHome=location.pathname==='/'||location.pathname.endsWith('/index.html');
    if(!isHome)return;

    const card=document.querySelector('.forecast-card');
    if(card){
      const kicker=card.querySelector('.card-kicker span');
      const badge=card.querySelector('.card-kicker b');
      const label=card.querySelector('.forecast-score span');
      const score=card.querySelector('.forecast-score strong');
      const bar=card.querySelector('.signal i');
      const stats=[...card.querySelectorAll('.mini-stats > div')];
      if(kicker)kicker.textContent='SFANDOM PUBLIC PICKS';
      if(badge)badge.textContent='UPDATED';
      if(label)label.textContent='PICK HIT RATE';
      if(score)score.innerHTML='90<small>%</small>';
      if(bar)bar.style.width='90%';
      const values=[['RECORD','OPEN'],['REVIEW','ALL'],['STATUS','LIVE']];
      stats.forEach((el,i)=>{if(!values[i])return;const s=el.querySelector('span');const b=el.querySelector('b');if(s)s.textContent=values[i][0];if(b)b.textContent=values[i][1]});
    }

    const matrix=document.querySelector('.matrix');
    if(matrix){
      const head=matrix.querySelector('.matrix-head span');
      const code=matrix.querySelector('.matrix-head b');
      if(head)head.textContent='SFANDOM ANALYSIS PROCESS';
      if(code)code.textContent='LIVE';
      const rows=[...matrix.querySelectorAll('.matrix-row')];
      const vals=[['RECENT FORM','CHECK'],['STARTER / LINEUP','CHECK'],['MATCHUP','TRACK'],['SITUATION','TRACK'],['MARKET SIGNAL','REVIEW']];
      rows.forEach((row,i)=>{
        if(!vals[i])return;
        const name=row.querySelector('span');
        const fill=row.querySelector('i b');
        const value=row.querySelector('em');
        if(name)name.textContent=vals[i][0];
        if(fill)fill.style.width='100%';
        if(value)value.textContent=vals[i][1];
      });
      const foot=matrix.querySelector('.matrix-foot');
      if(foot){const s=foot.querySelector('span');const strong=foot.querySelector('strong');if(s)s.textContent='PROCESS STATUS';if(strong)strong.textContent='ACTIVE'}
    }
  }

  function maybeShowPreamble(){
    const isHome=location.pathname==='/'||location.pathname.endsWith('/index.html');
    if(!isHome||document.querySelector('.sf-preamble-modal'))return;
    let seen=false;
    try{seen=localStorage.getItem('sfandomPreambleSeenV1')==='1'}catch{}
    if(seen)return;

    const style=document.createElement('style');
    style.dataset.sfTransient='preamble';
    style.textContent=`
      .sf-preamble-modal{position:fixed;inset:0;z-index:10000;display:grid;place-items:center;padding:20px;background:rgba(0,0,0,.78);backdrop-filter:blur(9px)}
      .sf-preamble-card{position:relative;width:min(720px,100%);max-height:min(82vh,760px);overflow:auto;border:1px solid #34343a;background:linear-gradient(145deg,#111114,#070708 72%);box-shadow:0 30px 100px rgba(0,0,0,.55);padding:34px}
      .sf-preamble-card:before{content:'';position:absolute;right:-80px;top:-100px;width:300px;height:300px;border-radius:50%;background:radial-gradient(circle,rgba(239,45,45,.2),transparent 66%);pointer-events:none}
      .sf-preamble-card small{position:relative;z-index:1;color:#ef2d2d;font-size:.62rem;font-weight:900;letter-spacing:.16em}
      .sf-preamble-card h2{position:relative;z-index:1;margin:12px 0 18px;color:#fff;font-size:clamp(2rem,6vw,4rem);line-height:.94;letter-spacing:-.055em}
      .sf-preamble-card h2 span{color:#ef2d2d}.sf-preamble-card p{position:relative;z-index:1;margin:0;color:#b7b7be;line-height:1.85;font-size:.92rem;word-break:keep-all}
      .sf-preamble-points{position:relative;z-index:1;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:24px 0}.sf-preamble-points div{padding:13px;border:1px solid #29292e;background:#0a0a0c}.sf-preamble-points b{display:block;color:#fff;font-size:.75rem}.sf-preamble-points span{display:block;margin-top:5px;color:#707078;font-size:.6rem;font-weight:800;letter-spacing:.08em}
      .sf-preamble-actions{position:relative;z-index:1;display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}.sf-preamble-actions a,.sf-preamble-actions button{appearance:none;border:1px solid #38383e;background:#0c0c0e;color:#fff;padding:12px 15px;text-decoration:none;font:800 .72rem/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:.06em;cursor:pointer}.sf-preamble-actions a{border-color:#ef2d2d;background:#17090b}.sf-preamble-close{position:absolute;right:15px;top:15px;z-index:2;width:36px;height:36px;border:1px solid #33343a;background:#0a0a0c;color:#aaa;font-size:1.1rem;cursor:pointer}
      @media(max-width:620px){.sf-preamble-modal{padding:12px}.sf-preamble-card{padding:27px 20px}.sf-preamble-points{grid-template-columns:1fr}.sf-preamble-actions a,.sf-preamble-actions button{flex:1;text-align:center}}
    `;
    document.head.appendChild(style);

    const modal=document.createElement('div');
    modal.className='sf-preamble-modal';
    modal.setAttribute('role','dialog');
    modal.setAttribute('aria-modal','true');
    modal.setAttribute('aria-labelledby','sfPreambleTitle');
    modal.innerHTML=`<div class="sf-preamble-card"><button type="button" class="sf-preamble-close" aria-label="닫기">×</button><small>SFANDOM PREAMBLE · 前文</small><h2 id="sfPreambleTitle">결과보다 먼저,<br><span>근거를 남깁니다.</span></h2><p>SFANDOM은 스포츠를 단순한 승패가 아니라 기록과 흐름이 축적되는 데이터로 봅니다. 맞았다는 말보다 왜 그렇게 판단했는지를 먼저 공개하고, 실패한 기록까지 남겨 신뢰를 쌓겠습니다.</p><div class="sf-preamble-points"><div><b>근거 우선</b><span>EVIDENCE FIRST</span></div><div><b>시각 기록</b><span>TIME STAMP</span></div><div><b>결과 보존</b><span>RECORD EVERYTHING</span></div></div><div class="sf-preamble-actions"><a href="/preamble.html">전문 전체보기 →</a><button type="button" data-dismiss>확인했습니다</button></div></div>`;
    document.body.appendChild(modal);

    const close=()=>{try{localStorage.setItem('sfandomPreambleSeenV1','1')}catch{}modal.remove();style.remove()};
    modal.querySelector('.sf-preamble-close').addEventListener('click',close);
    modal.querySelector('[data-dismiss]').addEventListener('click',close);
    modal.addEventListener('click',e=>{if(e.target===modal)close()});
    const esc=e=>{if(e.key==='Escape'&&document.body.contains(modal)){close();document.removeEventListener('keydown',esc)}};
    document.addEventListener('keydown',esc);
  }

  function markRouteStyles(){
    document.head.querySelectorAll('style:not([data-sf-transient])').forEach(style=>style.dataset.sfRouteStyle='1');
  }

  function syncHead(nextDoc,targetUrl){
    document.title=nextDoc.title||'SFANDOM';
    const nextDescription=nextDoc.head.querySelector('meta[name="description"]');
    let currentDescription=document.head.querySelector('meta[name="description"]');
    if(nextDescription){
      if(!currentDescription){currentDescription=document.createElement('meta');currentDescription.name='description';document.head.appendChild(currentDescription)}
      currentDescription.content=nextDescription.content||'';
    }

    document.head.querySelectorAll('link[rel="stylesheet"]').forEach(link=>{
      if(!/music-player\.css(?:$|[?#])/i.test(link.href))link.remove();
    });
    document.head.querySelectorAll('style[data-sf-route-style]').forEach(style=>style.remove());

    nextDoc.head.querySelectorAll('link[rel="stylesheet"]').forEach(link=>{
      const raw=link.getAttribute('href');
      if(!raw)return;
      const href=new URL(raw,targetUrl).href;
      if(/music-player\.css(?:$|[?#])/i.test(href))return;
      const clone=document.createElement('link');
      [...link.attributes].forEach(attr=>clone.setAttribute(attr.name,attr.value));
      clone.href=href;
      document.head.appendChild(clone);
    });
    nextDoc.head.querySelectorAll('style').forEach(style=>{
      const clone=document.createElement('style');
      clone.dataset.sfRouteStyle='1';
      clone.textContent=style.textContent;
      document.head.appendChild(clone);
    });
  }

  function executePageScripts(scripts,targetUrl){
    scripts.forEach(info=>{
      if(info.src&&/music-player\.js(?:$|[?#])/i.test(info.src))return;
      const script=document.createElement('script');
      if(info.type)script.type=info.type;
      if(info.src){
        script.src=new URL(info.src,targetUrl).href;
        script.async=false;
      }else{
        script.textContent=info.text;
      }
      document.body.appendChild(script);
    });
  }

  async function navigate(rawUrl,{push=true}={}){
    if(routing)return;
    const targetUrl=new URL(rawUrl,location.href);
    if(targetUrl.origin!==location.origin)return;
    routing=true;
    document.documentElement.classList.add('sf-route-loading');
    persist();

    try{
      const response=await fetch(targetUrl.href,{credentials:'same-origin',cache:'no-store',headers:{'X-SFANDOM-Navigation':'1'}});
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const html=await response.text();
      const nextDoc=new DOMParser().parseFromString(html,'text/html');
      if(!nextDoc.body)throw new Error('Invalid document');

      const bodyClone=nextDoc.body.cloneNode(true);
      const scripts=[...bodyClone.querySelectorAll('script')].map(script=>({
        src:script.getAttribute('src')||'',
        type:script.getAttribute('type')||'',
        text:script.textContent||''
      }));
      bodyClone.querySelectorAll('script').forEach(script=>script.remove());
      bodyClone.querySelectorAll('.sf-music-player').forEach(node=>node.remove());

      syncHead(nextDoc,targetUrl);
      if(push)history.pushState({sfandomRoute:true},'',targetUrl.href);

      shell.remove();
      document.body.className=nextDoc.body.className;
      [...document.body.attributes].forEach(attr=>{if(attr.name!=='class')document.body.removeAttribute(attr.name)});
      [...nextDoc.body.attributes].forEach(attr=>{if(attr.name!=='class')document.body.setAttribute(attr.name,attr.value)});
      document.body.replaceChildren(...[...bodyClone.childNodes]);
      document.body.appendChild(shell);

      enhanceChrome();
      enhanceHome();
      executePageScripts(scripts,targetUrl);

      if(targetUrl.hash){
        requestAnimationFrame(()=>document.getElementById(decodeURIComponent(targetUrl.hash.slice(1)))?.scrollIntoView());
      }else{
        window.scrollTo({top:0,left:0,behavior:'instant'});
      }
    }catch(err){
      console.warn('[SFANDOM] seamless navigation fallback',err);
      location.href=targetUrl.href;
      return;
    }finally{
      routing=false;
      document.documentElement.classList.remove('sf-route-loading');
    }
  }

  function routeable(anchor,url){
    if(anchor.hasAttribute('download'))return false;
    if(anchor.target&&anchor.target.toLowerCase()!=='_self')return false;
    if(url.origin!==location.origin)return false;
    if(!/^https?:$/.test(url.protocol))return false;
    const homeTarget=url.pathname==='/'||url.pathname.endsWith('/index.html');
    if(anchor.classList.contains('brand')&&homeTarget)return false;
    if(url.pathname===location.pathname&&url.search===location.search&&url.hash)return false;
    const last=url.pathname.split('/').pop()||'';
    if(last&&/\.[a-z0-9]{2,8}$/i.test(last)&&!/\.html?$/i.test(last))return false;
    return true;
  }

  document.addEventListener('click',e=>{
    if(e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
    const anchor=e.target.closest?.('a[href]');
    if(!anchor||shell.contains(anchor))return;
    let url;
    try{url=new URL(anchor.href,location.href)}catch{return}
    if(!routeable(anchor,url))return;
    e.preventDefault();
    navigate(url.href);
  });

  window.addEventListener('popstate',()=>navigate(location.href,{push:false}));

  enhanceChrome();
  enhanceHome();
  maybeShowPreamble();
  markRouteStyles();
  loadCurrent({resume:true,play:false});
  updateUI();
})();
