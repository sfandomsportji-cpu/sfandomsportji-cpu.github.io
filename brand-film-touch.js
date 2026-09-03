(() => {
  'use strict';

  const mobileLike = window.matchMedia('(max-width: 900px), (pointer: coarse)').matches;
  if (!mobileLike) return;

  function init() {
    const video = document.querySelector('.home-brand-film-player');
    if (!video || video.dataset.oneTapReady === '1') return;

    video.dataset.oneTapReady = '1';

    const stage = document.createElement('div');
    stage.className = 'home-brand-film-stage';

    const parent = video.parentNode;
    if (!parent) return;

    parent.insertBefore(stage, video);
    stage.appendChild(video);

    const playButton = document.createElement('button');
    playButton.type = 'button';
    playButton.className = 'home-brand-film-tap-play';
    playButton.setAttribute('aria-label', 'SFANDOM 브랜드 필름 재생');
    playButton.innerHTML = '<span aria-hidden="true">▶</span><strong>PLAY</strong>';
    stage.appendChild(playButton);

    const hideButton = () => {
      playButton.hidden = true;
    };

    const showButton = () => {
      playButton.hidden = false;
    };

    playButton.addEventListener('click', async (event) => {
      event.preventDefault();
      event.stopPropagation();

      try {
        const result = video.play();
        if (result && typeof result.then === 'function') await result;
        hideButton();
      } catch (_) {
        showButton();
      }
    });

    video.addEventListener('play', hideButton);
    video.addEventListener('ended', showButton);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
