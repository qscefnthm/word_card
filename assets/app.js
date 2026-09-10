'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const KEY = 'word-card-site-v2';
  const LEGACY_KEY = 'zhou-night-vocab-2010t4-v1';
  const VALID_ID = /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}$/;
  const statuses = new Set(['known', 'fuzzy', 'unknown']);
  const names = {known: '认识', fuzzy: '模糊', unknown: '不认识'};
  let cards = [], byId = new Map(), catalog = null, deck = null;
  let flipped = false, storageOK = true, voice = null, toastTimer, loadSerial = 0;
  let state = {version: 2, theme: 'night', showContext: true, deckId: '', ratings: {}, runs: {}};
  const validId = id => typeof id === 'string' && VALID_ID.test(id) && !['constructor', 'prototype', '__proto__'].includes(id);
  const isObject = o => o && typeof o === 'object' && !Array.isArray(o);
  const esc = v => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function safeRatings(raw) {
    const out = {};
    if (!isObject(raw)) return out;
    for (const [id, value] of Object.entries(raw)) {
      if (!validId(id) || !isObject(value) || !statuses.has(value.status)) continue;
      const t = typeof value.updatedAt === 'string' ? Date.parse(value.updatedAt) : NaN;
      if (!Number.isFinite(t) || t < 0 || t > 8640000000000000) continue;
      out[id] = {status: value.status, updatedAt: new Date(t).toISOString()};
    }
    return out;
  }
  function mergeRatings(a, b) {
    const out = {...a};
    for (const [id, value] of Object.entries(b)) {
      if (!out[id] || Date.parse(value.updatedAt) >= Date.parse(out[id].updatedAt)) out[id] = value;
    }
    return out;
  }
  // Keep ratings for other or future decks. Loading one deck must not erase them.
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (saved && saved.version === 2) {
      state.theme = saved.theme === 'day' ? 'day' : 'night';
      state.showContext = saved.showContext !== false;
      state.deckId = validId(saved.deckId) ? saved.deckId : '';
      state.ratings = safeRatings(saved.ratings);
      if (isObject(saved.runs)) {
        for (const [id, run] of Object.entries(saved.runs)) if (validId(id)) state.runs[id] = run;
      }
    } else {
      const legacy = JSON.parse(localStorage.getItem(LEGACY_KEY) || 'null');
      if (legacy && legacy.version === 1) {
        state.ratings = safeRatings(legacy.ratings);
        state.runs['2010-e1-text4'] = legacy.run;
        state.theme = legacy.theme === 'day' ? 'day' : 'night';
      }
    }
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch (_) { storageOK = false; }
  document.documentElement.dataset.theme = state.theme;
  function storageLabel() {
    $('storageInfo').textContent = storageOK
      ? '自评保存在当前浏览器。手机与电脑共享词库，但进度需导出 / 导入，不自动同步。'
      : '此浏览器暂不能保存进度。复习仍可继续，请离开前导出记录。';
    $('storageInfo').classList.toggle('warning', !storageOK);
  }
  function save(merge = true) {
    try {
      if (merge) {
        let saved = null;
        try { saved = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (_) {}
        if (saved && saved.version === 2) state.ratings = mergeRatings(safeRatings(saved.ratings), state.ratings);
      }
      localStorage.setItem(KEY, JSON.stringify(state));
      storageOK = true;
    } catch (_) { storageOK = false; }
    storageLabel();
  }
  function toast(text) {
    clearTimeout(toastTimer); $('toast').textContent = text; $('toast').hidden = false;
    toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4500);
  }
  const run = () => deck ? state.runs[deck.id] : null;
  function cancelSpeech() { if ('speechSynthesis' in window) window.speechSynthesis.cancel(); }
  function cleanRun(raw) {
    if (!isObject(raw) || !Array.isArray(raw.ids)) return null;
    const ids = [...new Set(raw.ids.filter(id => byId.has(id)))];
    const answers = {};
    if (isObject(raw.answers)) for (const id of ids) if (statuses.has(raw.answers[id])) answers[id] = raw.answers[id];
    return {
      pack: ['core', 'all', 'hard', 'custom'].includes(raw.pack) ? raw.pack : 'custom',
      label: typeof raw.label === 'string' ? raw.label.slice(0, 60) : '本轮', ids, answers,
      index: Math.max(0, Math.min(Number.isInteger(raw.index) ? raw.index : 0, Math.max(0, ids.length - 1))),
      done: !!raw.done || ids.length === 0
    };
  }
  function start(pack, ids, label) {
    if (!deck) return;
    cancelSpeech();
    if (!ids) ids = cards.filter(c => pack === 'all' || pack === 'core' && c.core ||
      pack === 'hard' && ['fuzzy', 'unknown'].includes(state.ratings[c.id]?.status)).map(c => c.id);
    state.runs[deck.id] = {
      pack, label: label || ({core:'今晚轻复习', all:'本篇全部', hard:'只重看不熟的'}[pack] || '小组复习'),
      ids, index:0, answers:{}, done:ids.length === 0
    };
    flipped = false; save(); render();
  }
  function stats() {
    const s = {known:0, fuzzy:0, unknown:0, total:0};
    for (const v of Object.values(run()?.answers || {})) if (statuses.has(v)) {s[v]++; s.total++;}
    return s;
  }
  function updateSummary() {
    const r = run(), s = stats();
    $('seenCount').textContent = s.total; $('totalCount').textContent = ' / ' + r.ids.length;
    for (const status of statuses) $(status + 'Count').textContent = s[status];
    $('corePackCount').textContent = cards.filter(c => c.core).length + ' 张';
    $('allPackCount').textContent = cards.length + ' 张';
    $('hardCount').textContent = cards.filter(c => ['fuzzy', 'unknown'].includes(state.ratings[c.id]?.status)).length;
    $('progressFill').style.width = (r.ids.length ? s.total / r.ids.length * 100 : 0) + '%';
    $('progress').setAttribute('aria-valuemax', r.ids.length || 1);
    $('progress').setAttribute('aria-valuenow', s.total);
    document.querySelectorAll('[data-pack]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.pack === r.pack)));
    $('stop').disabled = r.done;
  }
  function applyFlip() {
    $('answer').hidden = !flipped; $('reveal').setAttribute('aria-expanded', String(flipped));
    $('reveal').innerHTML = (flipped ? '收起中文，再想一次' : '想一想，再翻开中文') + '<span class="keyhint">SPACE</span>';
    document.querySelectorAll('[data-rating]').forEach(b => { b.disabled = !flipped; });
  }
  function render() {
    if (!deck || !run()) return;
    const r = run(); updateSummary(); $('studyView').hidden = r.done; $('doneView').hidden = !r.done;
    $('contextToggle').checked = state.showContext;
    if (r.done) { renderDone(); return; }
    const c = byId.get(r.ids[r.index]);
    if (!c) { r.done = true; save(); render(); return; }
    $('roundPosition').innerHTML = '<strong>' + String(r.index + 1).padStart(2, '0') + '</strong> / ' + r.ids.length + ' · ' + esc(r.label);
    $('kind').textContent = c.kind; $('location').textContent = c.loc;
    $('word').textContent = c.term; $('word').classList.toggle('long', c.term.length > 22);
    $('form').textContent = c.form;
    $('quoteType').textContent = c.quoteType + (c.clue ? ' · 已标注的答案线索' : '');
    const pos = c.quote.indexOf(c.mark);
    $('quote').innerHTML = pos < 0 ? esc(c.quote) : esc(c.quote.slice(0, pos)) + '<mark>' + esc(c.mark) + '</mark>' + esc(c.quote.slice(pos + c.mark.length));
    $('quote').classList.toggle('clue', c.clue); $('quoteBlock').hidden = !state.showContext;
    for (const field of ['meaning','translation','note','match']) $(field).textContent = c[field];
    $('bookEntries').innerHTML = c.book.map(b => '<p class="source-word">' + esc(b.word) + ' <span class="source-no">#' + b.number + ' · A4版第' + b.page + '页 / 英文版第' + b.englishPage + '页</span></p><p class="definition">' + esc(b.definition) + '</p>').join('');
    $('bookDetails').open = false; $('prev').disabled = r.index === 0;
    const status = state.ratings[c.id]?.status;
    $('priorStatus').textContent = status ? '上次自评：' + names[status] : '';
    applyFlip(); voiceState(); $('announce').textContent = '第 ' + (r.index + 1) + ' 张，共 ' + r.ids.length + ' 张。' + c.term;
  }
  function move(delta) {
    const r = run(); if (!r || r.done) return;
    cancelSpeech(); const index = r.index + delta;
    if (index < 0) return;
    if (index >= r.ids.length) { finish(); return; }
    r.index = index; flipped = false; save(); render();
    if (innerWidth <= 760 && $('studyView').getBoundingClientRect().top < 0)
      window.scrollTo({top:Math.max(0, $('studyView').getBoundingClientRect().top + scrollY - 14), behavior:'auto'});
  }
  function rate(status) {
    const r = run(); if (!r || r.done || !flipped || !statuses.has(status)) return;
    const id = r.ids[r.index]; r.answers[id] = status;
    state.ratings[id] = {status, updatedAt:new Date().toISOString()}; move(1);
  }
  function finish() { if (!run()) return; cancelSpeech(); run().done = true; flipped = false; save(); render(); }
  function renderDone() {
    const r = run(), s = stats(); $('roundPosition').textContent = r.label + ' · 已收好';
    $('doneTitle').textContent = r.ids.length ? '这一小组，先收到这里。' : '这里暂时没有待重看的词。';
    $('doneMessage').textContent = r.ids.length ? '这轮你回想并自评了 ' + s.total + ' 张。剩下的，不必今晚清空。' : '标记“模糊”或“不认识”后，它们就会出现在这一组。';
    for (const status of statuses) $('done' + status[0].toUpperCase() + status.slice(1)).textContent = s[status];
    const hard = r.ids.filter(id => ['fuzzy','unknown'].includes(r.answers[id]));
    $('doneWords').innerHTML = hard.length ? '这轮留待重看：<em>' + hard.map(id => esc(byId.get(id).term)).join(' · ') + '</em>' : '词还在这里。下次继续就好。';
    $('retryHard').disabled = !hard.length; $('restart').disabled = !r.ids.length;
  }
  function listRender() {
    const q = $('searchInput').value.trim().toLowerCase();
    const matches = cards.filter(c => [c.term,c.form,c.meaning,...c.book.map(b => b.word)].join(' ').toLowerCase().includes(q));
    $('listCount').textContent = '显示 ' + matches.length + ' / ' + cards.length + ' 张 · ' + (deck?.title || '');
    $('wordList').innerHTML = matches.map(c => {
      const status = state.ratings[c.id]?.status;
      return '<section class="word-row"><div class="row-top"><div><div class="row-term" lang="en">' + esc(c.term) + '</div><div class="row-kind">' + esc(c.loc) + ' · ' + esc(c.kind) + '</div></div><span class="row-status">' + (status ? names[status] : '未自评') + '</span></div><details><summary>查看释义</summary><div class="row-meaning">' + esc(c.meaning) + '</div><div class="tiny">语境讲解；词表原释义在卡片背面。</div><button data-goto="' + esc(c.id) + '">去看这张卡 →</button></details></section>';
    }).join('') || '<p class="dialog-text">没有匹配的词，试试原形或更短的关键词。</p>';
  }
  function openDialog(id) { const d = $(id); if (d.showModal) d.showModal(); else d.setAttribute('open',''); }
  function closeDialog(id) { const d = $(id); if (d.close) d.close(); else d.removeAttribute('open'); }
  function download() {
    const data = {app:'word-card',version:2,exportedAt:new Date().toISOString(),deckId:state.deckId,ratings:state.ratings,
      words:cards.filter(c => state.ratings[c.id]).map(c => ({id:c.id,word:c.term,status:state.ratings[c.id].status,meaning:c.meaning}))};
    const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)], {type:'application/json;charset=utf-8'}));
    const a = document.createElement('a'); a.href = url; a.download = '晚安词卡_复习记录.json'; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url),2000); toast('已导出记录。在另一台设备导入即可接续自评。');
  }
  function voiceState() {
    voice = 'speechSynthesis' in window && typeof SpeechSynthesisUtterance !== 'undefined'
      ? window.speechSynthesis.getVoices().find(v => /^en(?:-|_)/i.test(v.lang) && v.localService) : null;
    $('speak').disabled = !voice;
    $('speak').title = voice ? '使用本机离线英语音色朗读' : '此设备没有可用的离线英语音色；不影响背词';
  }
  async function fetchJSON(path) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(),15000);
    try {
      const response = await fetch(path, {cache:'no-store',credentials:'same-origin',signal:controller.signal});
      if (!response.ok) throw new Error('词库请求失败（HTTP ' + response.status + '）');
      return await response.json();
    } finally { clearTimeout(timer); }
  }
  function checkCatalog(raw) {
    if (!raw || raw.schemaVersion !== 1 || typeof raw.version !== 'string' || !Array.isArray(raw.decks) || !raw.decks.length)
      throw new Error('词库目录格式有误。旧的复习记录没有被改动。');
    const ids = new Set();
    for (const d of raw.decks) {
      if (!d || !validId(d.id) || ids.has(d.id) || typeof d.title !== 'string' ||
        !/^data\/decks\/[a-zA-Z0-9_-]+\.json$/.test(d.file) || !Number.isInteger(d.count) || d.count < 1)
        throw new Error('篇目目录含无效或重复项。');
      ids.add(d.id);
    }
    if (!ids.has(raw.defaultDeck)) throw new Error('默认篇目不存在。');
    return raw;
  }
  function checkDeck(raw, entry) {
    if (!raw || raw.schemaVersion !== 1 || raw.id !== entry.id || typeof raw.title !== 'string' ||
        typeof raw.description !== 'string' || !Array.isArray(raw.cards) || raw.cards.length !== entry.count)
      throw new Error('篇目数据与目录不一致，请稍后重试。');
    const ids = new Set();
    for (const c of raw.cards) {
      if (!c || !validId(c.id) || ids.has(c.id) ||
        !['term','form','kind','loc','quote','mark','meaning','translation','note','match','quoteType','readingSource'].every(k => typeof c[k] === 'string') ||
        !c.term || !c.mark || !c.quote.includes(c.mark) || typeof c.core !== 'boolean' || typeof c.clue !== 'boolean' || !Array.isArray(c.book))
        throw new Error('词卡存在无效字段，未替换已加载的内容。');
      for (const b of c.book) if (!b || typeof b.word !== 'string' || typeof b.definition !== 'string' ||
        !['number','page','englishPage'].every(k => Number.isInteger(b[k]) && b[k] > 0)) throw new Error('词表来源字段有误。');
      ids.add(c.id);
    }
    return raw;
  }
  async function load(requestedId, isUpdate = false) {
    const serial = ++loadSerial, oldVersion = catalog?.version;
    $('checkUpdate').disabled = true; $('deckSelect').disabled = true;
    $('loadingBox').hidden = false; $('retryLoad').hidden = true;
    $('loadingMessage').textContent = isUpdate ? '正在检查已发布的词库…' : '正在读取篇目词库…';
    try {
      const nextCatalog = checkCatalog(await fetchJSON('./data/catalog.json'));
      const entry = nextCatalog.decks.find(d => d.id === requestedId) || nextCatalog.decks.find(d => d.id === nextCatalog.defaultDeck);
      const nextDeck = checkDeck(await fetchJSON('./' + entry.file), entry);
      if (serial !== loadSerial) return;
      cancelSpeech(); catalog = nextCatalog; deck = nextDeck; cards = deck.cards; byId = new Map(cards.map(c => [c.id,c]));
      state.deckId = deck.id; state.runs[deck.id] = cleanRun(state.runs[deck.id]);
      $('deckSelect').innerHTML = catalog.decks.map(d => '<option value="' + esc(d.id) + '">' + esc(d.title) + ' · ' + d.count + ' 张</option>').join('');
      $('deckSelect').value = deck.id; $('deckTitle').textContent = deck.title;
      $('deckDescription').textContent = deck.description; $('edition').textContent = '词库版本 ' + catalog.version;
      document.title = '晚安词卡 · ' + deck.title;
      $('workspace').hidden = false; $('loadingBox').hidden = true; flipped = false;
      document.querySelectorAll('[data-pack]').forEach(b => { b.disabled = false; });
      for (const id of ['openList','exportQuick','export','import','reset']) $(id).disabled = false;
      if (!run()) start('core'); else { save(); render(); }
      if ($('listDialog').open) listRender();
      if (isUpdate) toast(oldVersion === catalog.version ? '已检查，当前是最新发布词库。' : '词库已更新，自评和当前一轮已保留。新词可在“本篇全部”查看。');
    } catch (err) {
      if (serial !== loadSerial) return;
      $('loadingMessage').textContent = (err.name === 'AbortError' ? '读取超时，请检查网络后重试。' : err.message || '词库加载失败。') + (deck ? ' 可以继续复习已加载的卡片。' : ' 请通过网站地址访问，而不是双击 index.html。');
      $('retryLoad').hidden = false;
      if (deck) $('deckSelect').value = deck.id;
    } finally {
      if (serial === loadSerial) { $('checkUpdate').disabled = false; $('deckSelect').disabled = !deck; }
    }
  }
  $('checkUpdate').addEventListener('click',() => load(state.deckId,true));
  $('retryLoad').addEventListener('click',() => load(state.deckId));
  $('deckSelect').addEventListener('change',e => load(e.target.value));
  $('reveal').addEventListener('click',() => { flipped = !flipped; applyFlip(); });
  document.querySelectorAll('[data-rating]').forEach(b => b.addEventListener('click',() => rate(b.dataset.rating)));
  document.querySelectorAll('[data-pack]').forEach(b => b.addEventListener('click',() => start(b.dataset.pack)));
  $('prev').addEventListener('click',() => move(-1)); $('skip').addEventListener('click',() => move(1)); $('stop').addEventListener('click',finish);
  $('contextToggle').addEventListener('change',e => { state.showContext = e.target.checked; $('quoteBlock').hidden = !state.showContext; save(); });
  $('theme').addEventListener('click',() => { state.theme = state.theme === 'night' ? 'day' : 'night'; document.documentElement.dataset.theme = state.theme; save(); });
  $('retryHard').addEventListener('click',() => start('custom',run().ids.filter(id => ['fuzzy','unknown'].includes(run().answers[id])),'本轮不熟词'));
  $('restart').addEventListener('click',() => start(run().pack,[...run().ids],run().label));
  $('openList').addEventListener('click',() => { listRender(); openDialog('listDialog'); });
  $('searchInput').addEventListener('input',listRender);
  $('wordList').addEventListener('click',e => { const b = e.target.closest('[data-goto]'); if (!b || !byId.has(b.dataset.goto)) return; closeDialog('listDialog'); start('custom',[b.dataset.goto],'单张回想'); });
  $('openSources').addEventListener('click',() => openDialog('sourceDialog'));
  document.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click',() => closeDialog(b.dataset.close)));
  ['export','exportQuick'].forEach(id => $(id).addEventListener('click',download));
  $('import').addEventListener('click',() => $('importInput').click());
  $('importInput').addEventListener('change',async e => {
    const f = e.target.files[0]; if (!f) return;
    try {
      if (f.size > 1048576) throw new Error('记录文件过大，请选择本页或旧版词卡导出的 JSON。');
      const data = JSON.parse(await f.text());
      const legacy = data.app === 'night-vocab-2010t4' && data.version === 1;
      if (!(legacy || data.app === 'word-card' && data.version === 2)) throw new Error('这不是支持的词卡复习记录。');
      const imported = safeRatings(data.ratings);
      const changed = Object.entries(imported).filter(([id,v]) => !state.ratings[id] || Date.parse(v.updatedAt) >= Date.parse(state.ratings[id].updatedAt)).length;
      state.ratings = mergeRatings(state.ratings,imported); save(); render(); listRender();
      toast('已合并 ' + changed + ' 条自评；较旧的记录不会覆盖较新的记录。');
    } catch (err) { toast(err.message || '记录读取失败，原有进度未被修改。'); }
    e.target.value = '';
  });
  $('reset').addEventListener('click',() => {
    if (!confirm('清空本站所有篇目的本地自评和位置？建议先导出备份。此操作不会删除词库。')) return;
    state.ratings = {}; state.runs = {}; save(false); closeDialog('sourceDialog'); start('core'); toast('本站复习记录已清空，词库没有删除。');
  });
  $('speak').addEventListener('click',() => {
    if (!voice || !run() || run().done) return;
    cancelSpeech(); const u = new SpeechSynthesisUtterance(byId.get(run().ids[run().index]).term.replace(/…/g,' something '));
    u.voice = voice; u.lang = voice.lang; u.rate = .85;
    u.onerror = e => { if (!['canceled','interrupted'].includes(e.error)) toast('设备未能播放语音，文字复习不受影响。'); };
    speechSynthesis.speak(u);
  });
  if ('speechSynthesis' in window) speechSynthesis.addEventListener('voiceschanged',voiceState);
  document.addEventListener('keydown',e => {
    if (!run() || run().done || document.querySelector('dialog[open]') || e.ctrlKey || e.metaKey || e.altKey || e.target.matches('input,textarea,select')) return;
    if (e.code === 'Space') { if (e.target.closest('button,summary')) return; e.preventDefault(); flipped = !flipped; applyFlip(); }
    else if (['1','2','3'].includes(e.key)) { e.preventDefault(); rate({1:'known',2:'fuzzy',3:'unknown'}[e.key]); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); move(1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); move(-1); }
  });
  window.addEventListener('storage',e => {
    if (e.key !== KEY || !e.newValue) return;
    try { const next = JSON.parse(e.newValue); if (next.version === 2) { state.ratings = mergeRatings(state.ratings,safeRatings(next.ratings)); if (run()) updateSummary(); } } catch (_) {}
  });
  window.addEventListener('pagehide',cancelSpeech);
  storageLabel(); voiceState(); load(state.deckId);
})();
