(()=>{
  const tracks=[
    {src:'assets/music/sfandom-rnb-01-smooth-rnb-beat.mp3',title:'Smooth Rnb Beat',artist:'Tunetank',source:'https://pixabay.com/music/beats-smooth-rnb-beat-409348/'},
    {src:'assets/music/sfandom-rnb-02-modern-rnb.mp3',title:'Modern R&B',artist:'-SunSet-',source:'https://pixabay.com/music/beats-modern-rampb-550856/'},
    {src:'assets/music/sfandom-rnb-03-private-thoughts.mp3',title:'Private Thoughts',artist:'JayStacksBeats',source:'https://pixabay.com/music/funk-private-thoughts-chill-late-night-trapsoul-instrumental-462717/'},
    {src:'assets/music/sfandom-rnb-04-low-glow.mp3',title:'Low Glow',artist:'OpenUseMusic',source:'https://pixabay.com/music/rnb-low-glow-warm-rampb-chill-for-relaxed-focus-460279/'}
  ];

  const footerLinks=document.querySelector('.footer-links');
  if(footerLinks){
    if(!footerLinks.querySelector('a[href="terms.html"]')){
      const terms=document.createElement('a');terms.href='terms.html';terms.textContent='이용약관';footerLinks.appendChild(terms);
    }
    if(!footerLinks.querySelector('a[href="privacy.html"]')){
      const privacy=document.createElement('a');privacy.href='privacy.html';privacy.textContent='개인정보 처리방침';footerLinks.appendChild(privacy);
    }
  }

  const K={index:'sfandomMusicIndexV3',time:'sfandomMusicTimeV3'};
  const get=(k,f)=>{try{const v=localStorage.getItem(k);return v===null?f:v}catch{return f}};
  const set=(k,v)=>{try{localStorage.setItem(k,String(v))}catch{}};
  let index=Math.max(0,Math.min(tracks.length-1,parseInt(get(K.index,'0'),10)||0));
  let restoreTime=Math.max(0,parseFloat(get(K.time,'0'))||0);
  let enabled=false;
  let lastSave=0;

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
        <span class="sf-music-copy"><b>SFANDOM RADIO</b><small id="sfMusicTitle">R&B</small></span>
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
      if(play){enabled=true;audio.play().catch(()=>{});}else{enabled=false;}
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
    if(audio.paused){enabled=true;audio.play().catch(()=>{});}else{enabled=false;audio.pause();}
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

  loadCurrent({resume:true,play:false});
  updateUI();
})();