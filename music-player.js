(()=>{
  const tracks=[
    {src:'assets/music/sfandom-rnb-01-smooth-rnb-beat.mp3',title:'Smooth Rnb Beat',artist:'Tunetank',source:'https://pixabay.com/music/beats-smooth-rnb-beat-409348/'},
    {src:'assets/music/sfandom-rnb-02-modern-rnb.mp3',title:'Modern R&B',artist:'-SunSet-',source:'https://pixabay.com/music/beats-modern-rampb-550856/'},
    {src:'assets/music/sfandom-rnb-03-private-thoughts.mp3',title:'Private Thoughts',artist:'JayStacksBeats',source:'https://pixabay.com/music/funk-private-thoughts-chill-late-night-trapsoul-instrumental-462717/'},
    {src:'assets/music/sfandom-rnb-04-low-glow.mp3',title:'Low Glow',artist:'OpenUseMusic',source:'https://pixabay.com/music/rnb-low-glow-warm-rampb-chill-for-relaxed-focus-460279/'}
  ];

  // Keep legal pages discoverable across every current SFANDOM page
  // without duplicating footer markup maintenance.
  const footerLinks=document.querySelector('.footer-links');
  if(footerLinks){
    if(!footerLinks.querySelector('a[href="terms.html"]')){
      const terms=document.createElement('a');
      terms.href='terms.html';
      terms.textContent='이용약관';
      terms.setAttribute('aria-label','SFANDOM 이용약관');
      footerLinks.appendChild(terms);
    }
    if(!footerLinks.querySelector('a[href="privacy.html"]')){
      const privacy=document.createElement('a');
      privacy.href='privacy.html';
      privacy.textContent='개인정보 처리방침';
      privacy.setAttribute('aria-label','SFANDOM 개인정보 처리방침');
      footerLinks.appendChild(privacy);
    }
  }

  // V2 keys intentionally reset the previous test-state once. After this,
  // a visitor's MUSIC OFF choice is remembered normally.
  const K={index:'sfandomMusicIndexV2',time:'sfandomMusicTimeV2',enabled:'sfandomMusicEnabledV2'};
  const get=(k,f)=>{try{const v=localStorage.getItem(k);return v===null?f:v}catch{return f}};
  const set=(k,v)=>{try{localStorage.setItem(k,String(v))}catch{}};

  let index=Math.max(0,Math.min(tracks.length-1,parseInt(get(K.index,'0'),10)||0));
  let enabled=get(K.enabled,'1')!=='0';
  let restoreTime=Math.max(0,parseFloat(get(K.time,'0'))||0);
  let lastSave=0;
  let userUnlocked=false;

  const audio=new Audio();
  audio.preload='auto';
  audio.autoplay=true;
  audio.playsInline=true;
  audio.volume=.22;

  const shell=document.createElement('aside');
  shell.className='sf-music-player';
  shell.setAttribute('aria-label','SFANDOM background music');
  shell.innerHTML=`
    <div class="sf-music-now">
      <span class="sf-music-bars" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
      <span class="sf-music-copy"><b>SFANDOM RADIO</b><small id="sfMusicTitle">R&B</small></span>
    </div>
    <div class="sf-music-actions">
      <button type="button" data-prev aria-label="Previous track">‹</button>
      <button type="button" class="sf-music-toggle" data-toggle aria-label="Play or pause background music">▶</button>
      <button type="button" data-next aria-label="Next track">›</button>
      <a data-source href="#" target="_blank" rel="noopener noreferrer" aria-label="Music source">↗</a>
    </div>`;
  document.body.appendChild(shell);

  const titleEl=shell.querySelector('#sfMusicTitle');
  const toggle=shell.querySelector('[data-toggle]');
  const source=shell.querySelector('[data-source]');

  function updateUI(){
    const t=tracks[index];
    titleEl.textContent=`${String(index+1).padStart(2,'0')}/${String(tracks.length).padStart(2,'0')} · ${t.title}`;
    titleEl.title=`${t.title} — ${t.artist}`;
    source.href=t.source;
    const playing=!audio.paused&&!audio.ended;
    shell.classList.toggle('is-playing',playing);
    shell.classList.toggle('is-off',!enabled);
    shell.classList.toggle('is-blocked',enabled&&!playing&&!userUnlocked);
    toggle.textContent=playing?'Ⅱ':'▶';
    toggle.setAttribute('aria-label',playing?'Pause background music':'Play background music');
  }

  function persist(){
    set(K.index,index);
    set(K.time,Number.isFinite(audio.currentTime)?audio.currentTime:0);
    set(K.enabled,enabled?'1':'0');
  }

  function tryPlay({gesture=false}={}){
    if(!enabled)return Promise.resolve(false);
    if(gesture)userUnlocked=true;
    const p=audio.play();
    if(!p||typeof p.then!=='function'){updateUI();return Promise.resolve(true)}
    return p.then(()=>{updateUI();return true}).catch(()=>{updateUI();return false});
  }

  function loadCurrent({resume=false,autoplay=false}={}){
    const t=tracks[index];
    audio.pause();
    audio.src=t.src;
    audio.load();
    updateUI();

    const restore=()=>{
      if(resume&&restoreTime>0&&Number.isFinite(audio.duration)&&restoreTime<audio.duration-2){
        try{audio.currentTime=restoreTime}catch{}
      }
      restoreTime=0;
      if(autoplay&&enabled)tryPlay({gesture:userUnlocked});
      updateUI();
    };
    audio.addEventListener('loadedmetadata',restore,{once:true});
  }

  function playFromControl(){
    enabled=true;
    userUnlocked=true;
    set(K.enabled,'1');
    tryPlay({gesture:true});
    updateUI();
  }

  function pause(){
    enabled=false;
    set(K.enabled,'0');
    audio.pause();
    persist();
    updateUI();
  }

  function move(delta){
    persist();
    index=(index+delta+tracks.length)%tracks.length;
    restoreTime=0;
    set(K.index,index);
    set(K.time,'0');
    loadCurrent({autoplay:enabled});
  }

  shell.querySelector('[data-prev]').addEventListener('click',e=>{
    e.stopPropagation();
    userUnlocked=true;
    move(-1);
  });
  shell.querySelector('[data-next]').addEventListener('click',e=>{
    e.stopPropagation();
    userUnlocked=true;
    move(1);
  });
  toggle.addEventListener('click',e=>{
    e.stopPropagation();
    userUnlocked=true;
    if(!audio.paused){pause();return}
    playFromControl();
  });

  audio.addEventListener('play',updateUI);
  audio.addEventListener('pause',updateUI);
  audio.addEventListener('ended',()=>move(1));
  audio.addEventListener('error',()=>{
    shell.classList.add('has-error');
    setTimeout(()=>{shell.classList.remove('has-error');move(1)},1200);
  });
  audio.addEventListener('timeupdate',()=>{
    const now=Date.now();
    if(now-lastSave>5000){lastSave=now;persist()}
  });

  // Best-effort audible autoplay. Browsers that permit it start immediately.
  // If a mobile browser blocks it, the visitor's very first interaction starts it.
  const unlock=e=>{
    if(!enabled)return;
    if(e&&shell.contains(e.target))return;
    userUnlocked=true;
    tryPlay({gesture:true});
  };
  ['pointerdown','touchstart','click'].forEach(type=>document.addEventListener(type,unlock,{once:true,capture:true,passive:true}));
  document.addEventListener('keydown',unlock,{once:true,capture:true});
  window.addEventListener('pagehide',persist);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)persist()});

  loadCurrent({resume:true,autoplay:false});
  // Try immediately on page load; allowed on desktop/sessions with autoplay permission.
  tryPlay({gesture:false});
  // Retry when media becomes playable. This also helps after internal page navigation.
  audio.addEventListener('canplay',()=>{if(enabled&&!userUnlocked)tryPlay({gesture:false})},{once:true});
  updateUI();
})();