'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const KEY = 'word-card-site-v2';
  let catalog = null, deck = null, cards = [], filter = 'all', voice = null, toastTimer = null, audioPlayer = null, audioBundle = null, audioUrls = new Map();
  const esc = v => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function readState() {
    try {
      const raw = JSON.parse(localStorage.getItem(KEY) || 'null');
      return raw && raw.version === 2 ? raw : {version:2, theme:'night', deckId:'', ratings:{}, runs:{}};
    } catch (_) {
      return {version:2, theme:'night', deckId:'', ratings:{}, runs:{}};
    }
  }
  function writePrefs(patch) {
    try {
      const state = readState();
      Object.assign(state, patch);
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch (_) {}
  }
  const state = readState();
  document.documentElement.dataset.theme = state.theme === 'day' ? 'day' : 'night';

  function toast(text) {
    clearTimeout(toastTimer);
    $('toast').textContent = text;
    $('toast').hidden = false;
    toastTimer = setTimeout(() => { $('toast').hidden = true; }, 3200);
  }
  function cancelSpeech() {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    if (audioPlayer) {
      audioPlayer.pause();
      audioPlayer.removeAttribute('src');
      audioPlayer.load();
    }
    document.querySelectorAll('.quick-speak.playing').forEach(b => b.classList.remove('playing'));
  }
  function clearAudioBundle() {
    for (const url of audioUrls.values()) URL.revokeObjectURL(url);
    audioUrls.clear();
    audioBundle = null;
  }
  function bundledAudioUrl(id) {
    if (!audioBundle || !audioBundle[id]) return null;
    if (audioUrls.has(id)) return audioUrls.get(id);
    try {
      const raw = atob(audioBundle[id]);
      const bytes = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
      const url = URL.createObjectURL(new Blob([bytes], {type:'audio/mpeg'}));
      audioUrls.set(id, url);
      return url;
    } catch (_) {
      return null;
    }
  }
  function pickVoice() {
    if (!('speechSynthesis' in window)) return;
    const voices = window.speechSynthesis.getVoices();
    voice = voices.find(v => /^en(?:-|_)/i.test(v.lang) && v.localService)
      || voices.find(v => /^en(?:-|_)/i.test(v.lang))
      || null;
  }
  function pronunciationText(card) {
    return card.term.replace(/…/g, ' something ').replace(/\s*\/\s*/g, ', ').trim();
  }
  function speakLocal(text, button) {
    if (!('speechSynthesis' in window) || typeof SpeechSynthesisUtterance === 'undefined') {
      button.classList.remove('playing');
      toast('在线发音和本机语音都没有成功，可以稍后再试。');
      return;
    }
    const u = new SpeechSynthesisUtterance(text);
    if (voice) { u.voice = voice; u.lang = voice.lang; } else { u.lang = 'en-US'; }
    u.rate = .84;
    u.onend = () => button.classList.remove('playing');
    u.onerror = () => { button.classList.remove('playing'); toast('这次朗读没有成功，可以稍后再试。'); };
    window.speechSynthesis.speak(u);
  }
  function playAudioSource(src, onFail, button) {
    audioPlayer = new Audio();
    audioPlayer.preload = 'auto';
    audioPlayer.src = src;
    audioPlayer.onended = () => button.classList.remove('playing');
    audioPlayer.onerror = onFail;
    const p = audioPlayer.play();
    if (p && typeof p.catch === 'function') p.catch(onFail);
  }
  function speak(id, button) {
    const card = cards.find(c => c.id === id);
    if (!card) return;
    cancelSpeech();
    const text = pronunciationText(card);
    button.classList.add('playing');
    let stage = 0;
    const fallback = () => {
      if (audioPlayer) {
        audioPlayer.onerror = null;
        audioPlayer.onended = null;
      }
      if (stage === 0) {
        stage = 1;
        playAudioSource('https://dict.youdao.com/dictvoice?audio=' + encodeURIComponent(text) + '&type=2', fallback, button);
      } else if (stage === 1) {
        stage = 2;
        speakLocal(text, button);
      }
    };
    const bundled = bundledAudioUrl(id);
    if (bundled) playAudioSource(bundled, fallback, button);
    else fallback();
  }
  async function fetchJSON(path) {
    const response = await fetch(path, {cache:'no-store', credentials:'same-origin'});
    if (!response.ok) throw new Error('读取失败（HTTP ' + response.status + '）');
    return await response.json();
  }
  function requestedDeck() {
    const q = new URLSearchParams(location.search).get('deck');
    return q || state.deckId || '';
  }
  function render() {
    if (!deck) return;
    const q = $('searchInput').value.trim().toLowerCase();
    const shown = cards.filter(c => (filter === 'all' || c.core) &&
      (!q || [c.term,c.form,c.meaning,c.translation,...c.book.map(b => b.word)].join(' ').toLowerCase().includes(q)));
    $('listCount').textContent = '显示 ' + shown.length + ' / ' + cards.length + ' 张';
    $('quickList').innerHTML = shown.length ? shown.map(c =>
      '<article class="quick-row">' +
        '<button class="quick-speak" data-speak="' + esc(c.id) + '" aria-label="朗读 ' + esc(c.term) + '" title="播放发音">' +
          '<svg viewBox="0 0 24 24"><path d="M11 4 5 9H2v6h3l6 5Z"></path><path d="M15 8a6 6 0 0 1 0 8M18 5a10 10 0 0 1 0 14"></path></svg>' +
        '</button>' +
        '<div class="quick-en"><div class="quick-term" lang="en">' + esc(c.term) + '</div><div class="quick-form">' + esc(c.form) + '</div></div>' +
        '<div class="quick-zh">' + esc(c.meaning) + '</div>' +
        (c.core ? '<span class="quick-core">核心</span>' : '<span></span>') +
      '</article>'
    ).join('') : '<div class="quick-empty">没有匹配的词，换个关键词试试。</div>';
  }
  function setFilter(next) {
    filter = next === 'core' ? 'core' : 'all';
    document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.filter === filter)));
    render();
  }
  async function load(id) {
    cancelSpeech();
    clearAudioBundle();
    $('loadingBox').hidden = false;
    $('quickWorkspace').hidden = true;
    $('loadingMessage').textContent = '正在读取篇目词库…';
    $('deckSelect').disabled = true;
    $('searchInput').disabled = true;
    document.querySelectorAll('[data-filter]').forEach(b => b.disabled = true);
    try {
      catalog = await fetchJSON('./data/catalog.json');
      const entry = catalog.decks.find(d => d.id === id) || catalog.decks.find(d => d.id === catalog.defaultDeck);
      deck = await fetchJSON('./' + entry.file);
      cards = deck.cards;
      try {
        const audioData = await fetchJSON('./data/audio/' + entry.id + '.json');
        if (audioData && audioData.schemaVersion === 1 && audioData.deckId === entry.id && audioData.codec === 'audio/mpeg' && audioData.audio) {
          audioBundle = audioData.audio;
        }
      } catch (_) {
        audioBundle = null;
      }
      $('deckSelect').innerHTML = catalog.decks.map(d => '<option value="' + esc(d.id) + '">' + esc(d.title) + ' · ' + d.count + ' 张</option>').join('');
      $('deckSelect').value = deck.id;
      $('edition').textContent = '词库版本 ' + catalog.version;
      $('allCount').textContent = cards.length + ' 张';
      $('coreCount').textContent = cards.filter(c => c.core).length + ' 张';
      $('searchInput').value = '';
      $('deckSelect').disabled = false;
      $('searchInput').disabled = false;
      document.querySelectorAll('[data-filter]').forEach(b => b.disabled = false);
      $('loadingBox').hidden = true;
      $('quickWorkspace').hidden = false;
      writePrefs({deckId: deck.id});
      history.replaceState(null, '', './quick.html?deck=' + encodeURIComponent(deck.id));
      document.title = '中英速览 · ' + deck.title;
      render();
    } catch (err) {
      $('loadingMessage').textContent = (err && err.message) || '词库读取失败，请稍后重试。';
    }
  }

  $('deckSelect').addEventListener('change', e => load(e.target.value));
  $('searchInput').addEventListener('input', render);
  document.querySelectorAll('[data-filter]').forEach(b => b.addEventListener('click', () => setFilter(b.dataset.filter)));
  $('quickList').addEventListener('click', e => {
    const b = e.target.closest('[data-speak]');
    if (b) speak(b.dataset.speak, b);
  });
  $('theme').addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'night' ? 'day' : 'night';
    document.documentElement.dataset.theme = next;
    writePrefs({theme: next});
  });
  window.addEventListener('pagehide',() => { cancelSpeech(); clearAudioBundle(); });
  if ('speechSynthesis' in window) {
    pickVoice();
    window.speechSynthesis.addEventListener('voiceschanged', pickVoice);
  }
  load(requestedDeck());
})();