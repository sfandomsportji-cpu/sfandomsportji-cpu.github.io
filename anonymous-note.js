(()=>{
  /* Homepage pick UI fully retired. */
  const removePicks=()=>{
    document.getElementById('sfAnonymousNoteButton')?.remove();
    document.querySelector('.sf-note-modal')?.remove();
    document.querySelectorAll('style[data-sf-transient="anonymous-note"],#sfPickRepairStyle,#sfTodayPickStyle').forEach(el=>el.remove());
    document.querySelectorAll('section[aria-labelledby="pick-result-title"]').forEach(el=>el.remove());
    document.querySelectorAll('.sf-real-pick-board,.sf-today-board,[data-sf-real-board],[data-sf-current-picks]').forEach(el=>el.remove());
  };
  removePicks();
  requestAnimationFrame(removePicks);
})();
