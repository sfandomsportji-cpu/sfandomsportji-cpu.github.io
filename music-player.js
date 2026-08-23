(()=>{
  const tracks=[
    {src:'assets/music/sfandom-rnb-01-smooth-rnb-beat.mp3',title:'Smooth Rnb Beat',artist:'Tunetank',source:'https://pixabay.com/music/beats-smooth-rnb-beat-409348/'},
    {src:'assets/music/sfandom-rnb-02-modern-rnb.mp3',title:'Modern R&B',artist:'-SunSet-',source:'https://pixabay.com/music/beats-modern-rampb-550856/'},
    {src:'assets/music/sfandom-rnb-03-private-thoughts.mp3',title:'Private Thoughts',artist:'JayStacksBeats',source:'https://pixabay.com/music/funk-private-thoughts-chill-late-night-trapsoul-instrumental-462717/'},
    {src:'assets/music/sfandom-rnb-04-low-glow.mp3',title:'Low Glow',artist:'OpenUseMusic',source:'https://pixabay.com/music/rnb-low-glow-warm-rampb-chill-for-relaxed-focus-460279/'}
  ];

  const K={index:'sfandomMusicIndex',time:'sfandomMusicTime',enabled:'sfandomMusicEnabled'};
  const get=(k,f)=>{try{const v=localStorage.getItem(k);return v===null?f:v}catch{return f}};
  const set=(k,v)=>{try{localStorage.setItem(k,String(v))}catch{}};

  let index=Math.max(0,Math.min(tracks.length-1,parseInt(get(K.index,'0'),10)||0));
  let enabled=get(K.enabled,'1')!=='0';
  let unlocked=false;
  let restoreTime=Math.max(0,parseFloat(get(K.time,'0'))||0);
  let lastSave=0;

  const audio=new Audio();
  audio.preload='metadata';
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
    toggle.textContent=playing?'Ⅱ':'▶';
    toggle.setAttribute('aria-label',playing?'Pause background music':'Play background music');
  }

  function persist(){
    set(K.index,index);
    set(K.time,Number.isFinite(audio.currentTime)?audio.currentTime:0);
    set(K.enabled,enabled?'1':'0');
  }

  function loadCurrent({resume=false,autoplay=false}={}){
    const t=tracks[index];
    audio.pause();
    audio.src=t.src;
    audio.load();
    updateUI();
    const onMeta=()=>{
      if(resume&&restoreTime>0&&Number.isFinite(audio.duration)&&restoreTime<audio.duration-2){
        try{audio.currentTime=restoreTime}catch{}
      }
      restoreTime=0;
      if(autoplay&&enabled&&unlocked)audio.play().catch(()=>{});
      updateUI();
    };
    audio.addEventListener('loadedmetadata',onMeta,{once:true});
  }

  function play(){
    unlocked=true;
    enabled=true;
    set(K.enabled,'1');
    if(!audio.src)loadCurrent({resume:true});
    audio.play().catch(()=>{});
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
    loadCurrent({autoplay:enabled&&unlocked});
  }

  shell.querySelector('[data-prev]').addEventListener('click',()=>{unlocked=true;move(-1)});
  shell.querySelector('[data-next]').addEventListener('click',()=>{unlocked=true;move(1)});
  toggle.addEventListener('click',()=>{
    unlocked=true;
    if(!audio.paused){pause();return}
    play();
  });

  audio.addEventListener('play',updateUI);
  audio.addEventListener('pause',updateUI);
  audio.addEventListener('ended',()=>move(1));
  audio.addEventListener('error',()=>{
    shell.classList.add('has-error');
    setTimeout(()=>{shell.classList.remove('has-error');move(1)},1800);
  });
  audio.addEventListener('timeupdate',()=>{
    const now=Date.now();
    if(now-lastSave>5000){lastSave=now;persist()}
  });

  const unlock=()=>{
    unlocked=true;
    if(enabled)audio.play().catch(()=>{});
    updateUI();
  };
  document.addEventListener('pointerdown',unlock,{once:true,capture:true});
  document.addEventListener('keydown',unlock,{once:true,capture:true});
  window.addEventListener('pagehide',persist);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)persist()});

  loadCurrent({resume:true});
  updateUI();
})();