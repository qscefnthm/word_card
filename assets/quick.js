'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const KEY = 'word-card-site-v2';
  const QUICK_KEY = 'word-card-quick-v1';
  let catalog = null, deck = null, cards = [], filtered = [];
  let filter = 'all', view = 'cards', index = 0;
  let voice = null, toastTimer = null, audioPlayer = null, audioBundle = null, audioUrls = new Map();
  let touchStartX = null;

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
  function readQuickState() {
    try {
      const raw = JSON.parse(localStorage.getItem(QUICK_KEY) || 'null');
      return raw && raw.version === 1 ? raw : {version:1, view:'cards', filter:'all', indices:{}};
    } catch (_) {
      return {version:1, view:'cards', filter:'all', indices:{}};
    }
  }
  const state = readState();
  const quickState = readQuickState();
  filter = quickState.filter === 'core' ? 'core' : 'all';
  view = quickState.view === 'list' ? 'list' : 'cards';
  document.documentElement.dataset.theme = state.theme === 'day' ? 'day' : 'night';

  function saveQuickState() {
    try {
      quickState.filter = filter;
      quickState.view = view;
      if (deck) quickState.indices[deck.id + ':' + filter] = index;
      localStorage.setItem(QUICK_KEY, JSON.stringify(quickState));
    } catch (_) {}
  }
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
    document.querySelectorAll('.quick-speak.playing,.overview-speak.playing').forEach(b => b.classList.remove('playing'));
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
    return (card.spokenText || card.term).replace(/…/g, ' something ').replace(/\s*\/\s*/g, ', ').trim();
  }
  function speakLocal(text, button) {
    if (!('speechSynthesis' in window) || typeof SpeechSynthesisUtterance === 'undefined') {
      button.classList.remove('playing');
      toast('发音暂时不可用，不影响速览。');
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
  function filteredCards() {
    const q = $('searchInput').value.trim().toLowerCase();
    return cards.filter(c =>
      (filter === 'all' || c.core) &&
      (!q || [c.term,c.form,c.meaning,c.translation,c.note,...c.book.map(b => b.word)].join(' ').toLowerCase().includes(q))
    );
  }
  function highlightedQuote(card) {
    const pos = card.quote.indexOf(card.mark);
    return pos < 0
      ? esc(card.quote)
      : esc(card.quote.slice(0,pos)) + '<mark>' + esc(card.mark) + '</mark>' + esc(card.quote.slice(pos + card.mark.length));
  }
  function rebuildFiltered(resetIndex = false) {
    filtered = filteredCards();
    if (resetIndex) index = 0;
    if (!filtered.length) index = 0;
    else index = Math.max(0, Math.min(index, filtered.length - 1));
    render();
  }
  function renderCard() {
    const hasCards = filtered.length > 0;
    $('quickDone').hidden = true;
    $('overviewCard').hidden = !hasCards;
    $('.overview-nav');
    $('prevCard').hidden = !hasCards;
    $('nextCard').hidden = !hasCards;
    $('cardPosition').textContent = hasCards ? String(index + 1).padStart(2,'0') + ' / ' + String(filtered.length).padStart(2,'0') : '0 / 0';
    $('cardScope').textContent = filter === 'core' ? ' · 只看核心' : ' · 本篇全部';
    $('quickProgressFill').style.width = hasCards ? ((index + 1) / filtered.length * 100) + '%' : '0%';
    if (!hasCards) {
      $('cardKind').textContent = '没有匹配内容';
      $('overviewCard').hidden = true;
      $('prevCard').disabled = true;
      $('nextCard').disabled = true;
      return;
    }
    const c = filtered[index];
    $('cardKind').textContent = c.core ? '核心 · ' + c.kind : c.kind;
    $('cardTerm').textContent = c.term;
    $('cardForm').textContent = c.form;
    $('cardMeaning').textContent = c.meaning;
    $('cardQuoteType').textContent = c.quoteType;
    $('cardCollocationBlock').hidden = !(c.collocation && c.collocationMeaning);
    $('cardCollocation').textContent = c.collocation || '';
    $('cardCollocationMeaning').textContent = c.collocationMeaning || '';
    $('cardQuote').innerHTML = highlightedQuote(c);
    $('cardTranslation').textContent = c.translation;
    $('cardNote').textContent = c.note;
    $('cardSpeak').dataset.speak = c.id;
    $('prevCard').disabled = index === 0;
    $('nextCard').textContent = index === filtered.length - 1 ? '完成速览 ✓' : '下一个 →';
    saveQuickState();
  }
  function renderList() {
    $('listCount').textContent = '显示 ' + filtered.length + ' / ' + cards.length + ' 张 · ' + (filter === 'core' ? '核心' : '全部');
    $('quickList').innerHTML = filtered.length ? filtered.map(c =>
      '<article class="quick-row">' +
        '<button class="quick-speak" data-speak="' + esc(c.id) + '" aria-label="朗读 ' + esc(c.term) + '" title="播放发音">' +
          '<svg viewBox="0 0 24 24"><path d="M11 4 5 9H2v6h3l6 5Z"></path><path d="M15 8a6 6 0 0 1 0 8M18 5a10 10 0 0 1 0 14"></path></svg>' +
        '</button>' +
        '<div class="quick-en"><div class="quick-term" lang="en">' + esc(c.term) + '</div><div class="quick-form">' + esc(c.form) + '</div></div>' +
        '<div class="quick-zh">' + esc(c.meaning) +
          (c.collocation && c.collocationMeaning ? '<div class="quick-usage"><span lang="en">' + esc(c.collocation) + '</span> — ' + esc(c.collocationMeaning) + '</div>' : '') + '</div>' +
        (c.core ? '<span class="quick-core">核心</span>' : '<span></span>') +
      '</article>'
    ).join('') : '<div class="quick-empty">没有匹配的词，换个关键词试试。</div>';
  }
  function render() {
    filtered = filteredCards();
    if (filtered.length) index = Math.max(0, Math.min(index, filtered.length - 1));
    else index = 0;
    document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.filter === filter)));
    document.querySelectorAll('[data-view]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === view)));
    $('cardView').hidden = view !== 'cards';
    $('listView').hidden = view !== 'list';
    renderCard();
    renderList();
  }
  function move(delta) {
    if (!filtered.length) return;
    const next = index + delta;
    if (next < 0) return;
    if (next >= filtered.length) {
      showDone();
      return;
    }
    cancelSpeech();
    index = next;
    renderCard();
  }
  function showDone() {
    cancelSpeech();
    $('overviewCard').hidden = true;
    $('prevCard').hidden = true;
    $('nextCard').hidden = true;
    $('quickDone').hidden = false;
    $('quickProgressFill').style.width = '100%';
    $('cardPosition').textContent = filtered.length + ' / ' + filtered.length;
    $('doneTitle').textContent = filter === 'core' ? '核心词，已经速览完了。' : '这一篇，已经速览完了。';
    $('doneMessage').textContent = '这轮看过 ' + filtered.length + ' 张中英对照。现在回正式词卡做主动回忆，会容易很多。';
    $('goFlashcards').href = './index.html?deck=' + encodeURIComponent(deck.id);
  }
  function restart() {
    index = 0;
    $('quickDone').hidden = true;
    $('overviewCard').hidden = false;
    $('prevCard').hidden = false;
    $('nextCard').hidden = false;
    renderCard();
  }
  function setFilter(next) {
    filter = next === 'core' ? 'core' : 'all';
    index = 0;
    quickState.indices[deck.id + ':' + filter] = 0;
    saveQuickState();
    render();
  }
  function setView(next) {
    view = next === 'list' ? 'list' : 'cards';
    saveQuickState();
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
    document.querySelectorAll('[data-filter],[data-view]').forEach(b => b.disabled = true);
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
      index = Number.isInteger(quickState.indices[deck.id + ':' + filter]) ? quickState.indices[deck.id + ':' + filter] : 0;
      $('deckSelect').disabled = false;
      $('searchInput').disabled = false;
      document.querySelectorAll('[data-filter],[data-view]').forEach(b => b.disabled = false);
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
  $('searchInput').addEventListener('input', () => { index = 0; rebuildFiltered(true); });
  document.querySelectorAll('[data-filter]').forEach(b => b.addEventListener('click', () => setFilter(b.dataset.filter)));
  document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
  $('quickList').addEventListener('click', e => {
    const b = e.target.closest('[data-speak]');
    if (b) speak(b.dataset.speak, b);
  });
  $('cardSpeak').addEventListener('click', () => {
    const id = $('cardSpeak').dataset.speak;
    if (id) speak(id, $('cardSpeak'));
  });
  $('prevCard').addEventListener('click', () => move(-1));
  $('nextCard').addEventListener('click', () => move(1));
  $('restartQuick').addEventListener('click', restart);
  $('overviewCard').addEventListener('touchstart', e => { touchStartX = e.changedTouches[0]?.clientX ?? null; }, {passive:true});
  $('overviewCard').addEventListener('touchend', e => {
    if (touchStartX === null) return;
    const endX = e.changedTouches[0]?.clientX ?? touchStartX;
    const dx = endX - touchStartX;
    touchStartX = null;
    if (Math.abs(dx) < 55) return;
    move(dx < 0 ? 1 : -1);
  }, {passive:true});
  document.addEventListener('keydown', e => {
    if (view !== 'cards' || e.target.matches('input,select,textarea') || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); move(1); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); move(-1); }
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