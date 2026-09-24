(() => {
  const chapters = [...document.querySelectorAll('.chapter')];
  const links = [...document.querySelectorAll('.rail a')];
  const select = document.querySelector('#chapter-select');
  const status = document.querySelector('#status');
  const viewer = document.querySelector('#image-viewer');
  const pageTitle = document.title;
  let returnFocus;

  function showChapter(id, focus = false) {
    let index = chapters.findIndex(chapter => chapter.id === id);
    if (index < 0) index = 0;
    chapters.forEach((chapter, i) => { chapter.hidden = i !== index; });
    links.forEach((link, i) => {
      link.classList.toggle('before', i < index);
      if (i === index) link.setAttribute('aria-current', 'step');
      else link.removeAttribute('aria-current');
    });
    select.value = chapters[index].id;
    document.title = `${chapters[index].querySelector('h1').textContent} · ${pageTitle}`;
    if (viewer.open) viewer.close();
    if (focus) {
      chapters[index].querySelector('h1').focus({ preventScroll: true });
      window.scrollTo(0, 0);
    }
  }
  document.documentElement.classList.add('js');
  showChapter(location.hash.slice(1));
  window.addEventListener('hashchange', () => showChapter(location.hash.slice(1), true));
  select.addEventListener('change', () => { location.hash = select.value; });

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(text); return; } catch (_) {}
    }
    const field = document.createElement('textarea');
    field.value = text;
    field.style.cssText = 'position:fixed;left:-9999px;top:0';
    document.body.append(field);
    field.select();
    const copied = document.execCommand('copy');
    field.remove();
    if (!copied) throw new Error('Clipboard unavailable');
  }
  document.querySelectorAll('.prompt').forEach(button => {
    let resetTimer;
    let feedbackAnimation;
    button.addEventListener('click', async () => {
      const label = button.querySelector('.copy-label');
      try {
        await copyText(button.querySelector('.prompt-text').textContent);
        clearTimeout(resetTimer);
        label.textContent = 'Copied';
        button.classList.add('is-copied');
        if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
          if (feedbackAnimation) feedbackAnimation.cancel();
          feedbackAnimation = button.animate([
            { transform: 'scale(1)' },
            { transform: 'scale(0.985)', offset: 0.35 },
            { transform: 'scale(1)' }
          ], { duration: 300, easing: 'ease-out' });
        }
        status.textContent = 'Prompt copied to clipboard.';
      } catch (_) {
        label.textContent = 'Select';
        status.textContent = 'Copy unavailable. Select the prompt text and copy it manually.';
        const range = document.createRange();
        range.selectNodeContents(button.querySelector('.prompt-text'));
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      }
      button.focus({ preventScroll: true });
      clearTimeout(resetTimer);
      resetTimer = setTimeout(() => {
        label.textContent = 'Copy';
        button.classList.remove('is-copied');
      }, 2200);
    });
  });
  document.querySelectorAll('.screenshot').forEach(button => {
    button.addEventListener('click', () => {
      returnFocus = button;
      const original = button.querySelector('img');
      const enlarged = viewer.querySelector('img');
      enlarged.src = original.src;
      enlarged.alt = original.alt;
      viewer.showModal();
    });
  });
  viewer.addEventListener('click', () => viewer.close());
  viewer.addEventListener('close', () => { if (returnFocus) returnFocus.focus({ preventScroll: true }); });
})();
