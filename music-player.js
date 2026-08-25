(()=>{
  if(document.getElementById('sfAnonymousNoteButton'))return;
  const script=document.createElement('script');
  script.src='/anonymous-note.js?v=20260826-note2';
  script.async=false;
  script.onerror=()=>console.warn('[SFANDOM] anonymous note loader failed');
  document.body.appendChild(script);
})();
