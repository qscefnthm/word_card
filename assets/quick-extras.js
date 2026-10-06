'use strict';
// Quick-view-only preferences and writing drafts; never modify flashcard ratings/runs.
window.WordCardQuickExtras = (() => {
  const $ = id => document.getElementById(id);
  const KEY = 'word-card-recall-v1';
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let mode = 'bilingual', drafts = {}, context = null, hooks = null, saving = true;
  let revealed = new Set(), nextId = null, navigating = false;
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (saved && saved.version === 1) {
      mode = saved.mode === 'english' ? 'english' : 'bilingual';
      if (saved.drafts && typeof saved.drafts === 'object' && !Array.isArray(saved.drafts)) drafts = saved.drafts;
    }
  } catch (_) { saving = false; }

  function persist() {
    try { localStorage.setItem(KEY, JSON.stringify({version:1, mode, drafts})); saving = true; }
    catch (_) { saving = false; }
    $('recallStorage').textContent = saving
      ? '默写草稿仅保存在当前浏览器，不同步，也不改正式词卡的熟悉度。'
      : '当前无法保存草稿；本页仍可默写，刷新或关闭后可能丢失。';
  }
  function key(card) { return context.deck.id + '/' + card.id; }
  function draft(card) {
    const item = drafts[key(card)];
    return item && item.term === card.term && typeof item.text === 'string' ? item.text.slice(0,1000) : '';
  }
  function isRecall(view) { return view === 'list' && mode === 'english'; }
  function syncAnswers() {
    let open = 0;
    document.querySelectorAll('#quickList [data-recall-row]').forEach(row => {
      const show = revealed.has(row.dataset.recallRow);
      row.querySelector('.recall-answer').hidden = !show;
      const button = row.querySelector('[data-reveal-meaning]');
      button.setAttribute('aria-expanded', String(show));
      button.textContent = show ? '隐藏释义' : '核对释义';
      if (show) open++;
    });
    $('toggleRecallAnswers').textContent = context && context.filtered.length && open === context.filtered.length
      ? '隐藏全部释义' : '展开全部释义';
    $('toggleRecallAnswers').disabled = !context || !context.filtered.length;
  }
  function renderList(cards) {
    $('quickList').innerHTML = cards.length ? cards.map((card, i) =>
      '<article class="quick-row recall-row" data-recall-row="' + esc(card.id) + '">' +
        '<button class="quick-speak" data-speak="' + esc(card.id) + '" aria-label="朗读 ' + esc(card.term) + '" title="播放发音">' +
          '<svg viewBox="0 0 24 24"><path d="M11 4 5 9H2v6h3l6 5Z"></path><path d="M15 8a6 6 0 0 1 0 8M18 5a10 10 0 0 1 0 14"></path></svg></button>' +
        '<div class="quick-en"><div class="quick-term" lang="en">' + esc(card.term) + '</div></div>' +
        '<div class="recall-writing"><label class="recall-label" for="recall-' + i + '">中文默写</label>' +
          '<textarea id="recall-' + i + '" data-recall-input="' + esc(card.id) + '" rows="2" maxlength="1000" spellcheck="false" autocomplete="off" placeholder="先回想，再写下中文释义；也可以写在纸上">' + esc(draft(card)) + '</textarea></div>' +
        '<button class="quiet recall-reveal" data-reveal-meaning="' + esc(card.id) + '" aria-expanded="false" aria-controls="recall-answer-' + i + '">核对释义</button>' +
        '<div class="recall-answer" id="recall-answer-' + i + '" hidden><div class="recall-label">词条释义</div><div>' + esc(card.meaning) + '</div>' +
          (card.collocation && card.collocationMeaning ? '<div class="quick-usage"><span class="recall-label">例句中的搭配 · 单独理解</span><span lang="en">' + esc(card.collocation) + '</span> — ' + esc(card.collocationMeaning) + '</div>' : '') +
        '</div></article>'
    ).join('') : '<div class="quick-empty">没有匹配的英文词条，试试清空搜索或切换“本篇全部”。</div>';
    syncAnswers();
  }
  function render(next) {
    if (!context || context.deck.id !== next.deck.id) revealed = new Set();
    context = next;
    document.querySelectorAll('[data-list-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.listMode === mode)));
    const recall = isRecall(next.view);
    $('recallTools').hidden = !recall;
    $('listHint').textContent = recall ? '先回想中文，再主动核对' : '点喇叭即可听英文发音';
    $('searchInput').placeholder = recall ? '搜索英文词条' : '搜英文或中文，例如 persuasive / 有说服力';
    $('searchInput').setAttribute('aria-label', recall ? '搜索英文词条' : '搜索中英文');
    $('nextDeckSection').hidden = next.view !== 'list' && !next.atEnd;
    const position = next.catalog.decks.findIndex(d => d.id === next.deck.id);
    const following = position >= 0 ? next.catalog.decks[position + 1] : null;
    nextId = following ? following.id : null;
    $('nextDeckTitle').textContent = following ? '下一篇：' + following.title + ' · ' + following.count + ' 张' : '当前已是词库最后一篇';
    $('nextDeckHint').textContent = following ? '保留当前视图与核心筛选，接续该篇已保存的速览位置。' : '没有更多篇目了；可以在上方选择其他篇目复习。';
    $('nextDeckButton').textContent = following ? '下一篇 →' : '暂无下一篇';
    $('nextDeckButton').disabled = !following || navigating;
    if (recall) renderList(next.filtered);
    persist();
  }
  function setup(callbacks) {
    hooks = callbacks;
    document.querySelectorAll('[data-list-mode]').forEach(button => button.addEventListener('click', () => {
      if (mode === button.dataset.listMode) return;
      mode = button.dataset.listMode === 'english' ? 'english' : 'bilingual';
      revealed.clear();
      persist();
      hooks.modeChanged();
    }));
    $('quickList').addEventListener('input', event => {
      const input = event.target.closest('[data-recall-input]');
      if (!input || !context) return;
      const card = context.filtered.find(c => c.id === input.dataset.recallInput);
      if (!card) return;
      if (input.value) drafts[key(card)] = {term:card.term, text:input.value.slice(0,1000)};
      else delete drafts[key(card)];
      persist();
    });
    $('quickList').addEventListener('click', event => {
      const button = event.target.closest('[data-reveal-meaning]');
      if (!button || !context) return;
      const id = button.dataset.revealMeaning;
      if (revealed.has(id)) revealed.delete(id); else revealed.add(id);
      syncAnswers();
    });
    $('toggleRecallAnswers').addEventListener('click', () => {
      if (!context) return;
      const hide = context.filtered.every(c => revealed.has(c.id));
      for (const card of context.filtered) { if (hide) revealed.delete(card.id); else revealed.add(card.id); }
      syncAnswers();
    });
    $('nextDeckButton').addEventListener('click', async () => {
      if (!nextId || navigating) return;
      navigating = true;
      $('nextDeckButton').disabled = true;
      try { await hooks.nextDeck(nextId); }
      finally { navigating = false; $('nextDeckButton').disabled = !nextId; }
    });
  }
  return {setup, render, isRecall};
})();
