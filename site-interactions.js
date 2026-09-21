(() => {
  'use strict';

  const revealNodes = [...document.querySelectorAll('.reveal')];
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('show');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    revealNodes.forEach(node => io.observe(node));
  } else {
    revealNodes.forEach(node => node.classList.add('show'));
  }

  const hero = document.querySelector('.hero-reel[data-src]');
  if (!hero) return;

  const loadHero = () => {
    if (hero.dataset.loaded === '1') return;
    hero.dataset.loaded = '1';
    const source = document.createElement('source');
    source.src = hero.dataset.src;
    source.type = 'video/mp4';
    hero.append(source);
    hero.load();
    hero.play().catch(() => {});
  };

  const scheduleLoad = () => {
    if ('requestIdleCallback' in window) {
      requestIdleCallback(loadHero, { timeout: 1500 });
    } else {
      setTimeout(loadHero, 700);
    }
  };

  if ('IntersectionObserver' in window) {
    const heroObserver = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        heroObserver.disconnect();
        scheduleLoad();
      }
    }, { rootMargin: '200px 0px', threshold: 0 });
    heroObserver.observe(hero);
  } else {
    scheduleLoad();
  }
})();
