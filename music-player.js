(()=>{
  const load=(src,done)=>{
    const script=document.createElement('script');
    script.src=src;
    script.async=false;
    script.onload=()=>done?.();
    script.onerror=()=>console.warn('[SFANDOM] failed to load',src);
    document.body.appendChild(script);
  };
  load('/music-player-core.js?v=20260826-note1',()=>load('/anonymous-note.js?v=20260826-note1'));
})();