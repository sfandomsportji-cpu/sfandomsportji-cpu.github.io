(()=>{
  /* Anonymous-note UI and the temporary pick-board repair layer are retired.
     The homepage pick board is rendered in one place only: music-player.js. */
  document.getElementById('sfAnonymousNoteButton')?.remove();
  document.querySelector('.sf-note-modal')?.remove();
  document.querySelectorAll('style[data-sf-transient="anonymous-note"],#sfPickRepairStyle').forEach(el=>el.remove());
})();
