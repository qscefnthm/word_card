'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const KEY = 'exam-reading-review-v1';
  const APP = 'exam-reading-review';
  const validID = id => typeof id === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}$/.test(id) && !['constructor','prototype','__proto__'].includes(id);
  const recordKey = key => typeof key === 'string' && key.split('/').length === 2 && key.split('/').every(validID);
  const object = v => !!v && typeof v === 'object' && !Array.isArray(v);
  const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const names = {known:'认识',fuzzy:'模糊',unknown:'不认识'};
  const scopes = {'all':'Text 1–4 · 全部','1':'Text 1','2':'Text 2','3':'Text 3','4':'Text 4','1-2':'Text 1 + 2 · 第一批','3-4':'Text 3 + 4 · 第二批'};
  const date = value => typeof value === 'string' && Number.isFinite(Date.parse(value)) && Date.parse(value) >= 0 && Date.parse(value) <= Date.now() + 86400000;
  const now = () => new Date().toISOString();
  const fresh = () => ({version:1,theme:'night',dataset:'2014-e1',scope:'all',view:'list',kind:'all',status:'all',ratings:{},positions:{},updatedAt:now()});
  let state = fresh(), catalog, dataset, filtered = [], opened = new Set(), storageOK = true, storageProtected = false, serial = 0, index = 0, toastTimer;
  function sanitize(raw) {
    const out = fresh();
    if (!object(raw) || raw.version !== 1) return out;
    out.theme = raw.theme === 'day' ? 'day' : 'night';
    if (validID(raw.dataset)) out.dataset = raw.dataset;
    if (Object.hasOwn(scopes,raw.scope)) out.scope = raw.scope;
    if (raw.view === 'cards') out.view = 'cards';
    if (['all','highlight','supplement','option'].includes(raw.kind)) out.kind = raw.kind;
    if (['all','hard','unrated','known'].includes(raw.status)) out.status = raw.status;
    if (date(raw.updatedAt)) out.updatedAt = raw.updatedAt;
    if (object(raw.ratings)) for (const [key,value] of Object.entries(raw.ratings)) {
      if (recordKey(key) && object(value) && Object.hasOwn(names,value.status) && date(value.updatedAt)) out.ratings[key] = {status:value.status,updatedAt:value.updatedAt};
    }
    if (object(raw.positions)) for (const [key,value] of Object.entries(raw.positions)) {
      if (recordKey(key) && object(value) && validID(value.id) && date(value.updatedAt)) out.positions[key] = {id:value.id,updatedAt:value.updatedAt};
    }
    return out;
  }
  function merge(a,b) {
    const out = {...a};
    for (const [k,v] of Object.entries(b)) if (!out[k] || Date.parse(v.updatedAt) >= Date.parse(out[k].updatedAt)) out[k]=v;
    return out;
  }
  try {
    const text = localStorage.getItem(KEY);
    try {
      const raw = JSON.parse(text || 'null');
      if (raw && raw.version !== 1) { storageProtected=true; storageOK=false; }
      else state=sanitize(raw);
    } catch (_) { storageProtected=true; storageOK=false; }
  } catch (_) { storageOK=false; }
  document.documentElement.dataset.theme=state.theme;
  function labelStorage() {
    $('reviewSave').textContent = storageProtected ? '已有记录格式无法识别，暂不覆盖。请先导出保留原数据。' : storageOK ? '自评与位置已保存在本浏览器。旧词卡记录独立保留。' : '本浏览器暂不能保存，请离开前导出本模块记录。';
    $('reviewSave').classList.toggle('warning',!storageOK);
  }
  function save() {
    state.updatedAt=now();
    try {
      if (storageProtected) throw new Error('protected');
      const raw=JSON.parse(localStorage.getItem(KEY) || 'null');
      if(raw && raw.version!==1) {storageProtected=true;throw new Error('protected');}
      const previous=sanitize(raw);
      state.ratings=merge(previous.ratings,state.ratings);
      state.positions=merge(previous.positions,state.positions);
      localStorage.setItem(KEY,JSON.stringify(state));storageOK=true;
    } catch (_) { storageOK=false; }
    labelStorage();
  }
  function toast(message) { $('reviewToast').textContent=message;$('reviewToast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('reviewToast').hidden=true,4500); }
  const key = item => dataset.id+'/'+item.id;
  const positionKey = () => dataset.id+'/'+state.scope;
  const status = item => state.ratings[key(item)]?.status || '';
  const isSupplement = item => ['supplement','supplemental'].includes(item.kind);
  const isOption = item => /^Q\d/.test(item.loc);
  function source(item) { return `${isSupplement(item)?'补充关键表达':'黄标词与短语'} · ${isOption(item)?'题目 / 选项':'正文表达'}`; }
  function writeRoute() {
    const u = new URL(location.href);u.searchParams.set('set',dataset.id);u.searchParams.set('scope',state.scope);u.hash='';history.replaceState(null,'',u);
  }
  function savePosition(item) { state.positions[positionKey()]={id:item.id,updatedAt:now()};save();updateResume(); }
  function updateResume() { $('reviewResume').hidden=state.view!=='list'||!filtered.some(c=>c.id===state.positions[positionKey()]?.id); }
  function bookHTML(item) {
    const refs=item.book.map(ref=>`<div class="review-book"><p><strong lang="en">${esc(ref.headword)}</strong></p><p class="review-book-ref">红宝书 #${esc(ref.entry_id)} · A4 PDF 第 ${esc(ref.a4_page)} 页 · 英文词表 PDF 第 ${esc(ref.english_page)} 页</p><p>${esc(ref.original_meaning)}</p><p class="review-match">${esc(ref.mapping_note || '')}</p>${ref.transcription_note?`<p class="review-match">转写说明：${esc(ref.transcription_note)}</p>`:''}</div>`).join('');
    return `${refs || '<p class="review-match">已查所提供的两份红宝书 PDF，未找到合适的直接词条或基础词映射。</p>'}<p class="review-match">${esc(item.book_note || item.match || item.book_status_note || item.book_lookup?.note || '')}</p>${item.book_status==='not_found'?`<p class="review-match">查找范围：${esc(item.book_lookup?.search_scope||'')}</p>`:''}`;
  }
  function row(item) {
    const show=opened.has(item.id), id='answer-'+item.id;
    return `<article class="review-item" id="item-${esc(item.id)}" data-item="${esc(item.id)}"><div class="review-item-top"><button class="review-term-button" data-reveal="${esc(item.id)}" aria-expanded="${show}" aria-controls="${id}"><span class="review-term" lang="en">${esc(item.term)}</span><span class="review-meta"><span>Text ${item.text} · ${esc(item.loc)}</span><span class="${isSupplement(item)?'source-supplement':'source-highlight'}">${source(item)}</span></span><span class="review-reveal-hint">${show?'点击收起释义':'点击英文，核对语境义与红宝书'}</span></button><span class="review-state">${names[status(item)]||'未自评'}</span></div><div class="review-answer" id="${id}" ${show?'':'hidden'}><h3>真题语境义 · 整理讲解</h3><p class="review-meaning">${esc(item.context_meaning)}</p><p class="review-note">原文位置：Text ${item.text} · ${esc(item.loc)}${item.source_evidence?.pdf_page?' · 原卷 PDF 第 '+esc(item.source_evidence.pdf_page)+' 页':''}。${item.kind==='highlight'&&item.source_evidence?.highlight_parts?.length?'实际黄标：'+esc(item.source_evidence.highlight_parts.join(' / '))+'。本条可含必要的未标黄上下文。':'补充关键表达，不计为黄标分组。'}</p>${item.note?`<p class="review-note">${esc(item.note)}</p>`:''}<h3>红宝书原释义 · 独立对照</h3>${bookHTML(item)}<div class="review-rating" role="group" aria-label="${esc(item.term)} 的熟悉度">${Object.entries(names).map(([k,v])=>`<button data-rate="${k}" data-id="${item.id}" aria-pressed="${status(item)===k}">${v}</button>`).join('')}</div></div></article>`;
  }
  function applyFilters(restore=true) {
    const query=$('reviewSearch').value.trim().toLowerCase();
    filtered=dataset.items.filter(item => (state.scope==='all'||state.scope.split('-').map(Number).includes(item.text)) && (state.kind==='all'||state.kind==='highlight'&&!isSupplement(item)||state.kind==='supplement'&&isSupplement(item)||state.kind==='option'&&isOption(item)) && (state.status==='all'||state.status==='hard'&&['fuzzy','unknown'].includes(status(item))||state.status==='unrated'&&!status(item)||state.status==='known'&&status(item)==='known') && (!query||item.term.toLowerCase().includes(query)));
    if(restore) index=Math.max(0,filtered.findIndex(c=>c.id===state.positions[positionKey()]?.id));
    index=Math.min(index,Math.max(0,filtered.length-1));render();
  }
  function render() {
    const shown=state.view==='cards'?filtered.slice(index,index+1):filtered;
    $('reviewList').innerHTML=shown.map(row).join('');$('reviewList').classList.toggle('card-mode',state.view==='cards');
    $('reviewEmpty').hidden=filtered.length>0;
    $('reviewCount').textContent=`当前 ${filtered.length} 项 · ${scopes[state.scope]}`;
    const rated=dataset.items.filter(c=>!!status(c)).length;
    $('reviewProgress').textContent=`本试卷已自评 ${rated} / ${dataset.items.length} 项`;
    $('reviewPagination').hidden=state.view!=='cards'||!filtered.length;
    $('reviewPosition').textContent=`${index+1} / ${filtered.length}`;
    $('reviewPrev').disabled=index<=0;$('reviewNext').disabled=index>=filtered.length-1;
    document.querySelectorAll('[data-review-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.reviewView===state.view)));
    updateResume();labelStorage();
  }
  function settingsToUI() { for(const [id,k] of [['reviewDataset','dataset'],['reviewScope','scope'],['reviewKind','kind'],['reviewStatus','status']])$(id).value=state[k]; }
  async function load() {
    const token=++serial;$('reviewWorkspace').hidden=true;$('reviewLoading').hidden=false;$('reviewRetry').hidden=true;$('reviewLoadingMessage').textContent='正在读取复盘内容…';
    try {
      const response=await fetch('./data/review/catalog.json',{cache:'no-cache'});if(!response.ok)throw new Error('catalog');
      const cat=await response.json();if(cat.schemaVersion!==1||!Array.isArray(cat.sets)||!cat.sets.length)throw new Error('catalog schema');
      const params=new URLSearchParams(location.search),requested=params.get('set')||state.dataset;
      const entry=cat.sets.find(x=>x.id===requested)||cat.sets.find(x=>x.id===cat.defaultSet)||cat.sets[0];
      if(!validID(entry.id)||!/^data\/review\/[a-zA-Z0-9_-]+\.json$/.test(entry.file))throw new Error('path');
      const res=await fetch('./'+entry.file,{cache:'no-cache'});if(!res.ok)throw new Error('dataset');
      const data=await res.json();if(data.schemaVersion!==1||data.id!==entry.id||!Array.isArray(data.items)||data.items.length!==entry.count||data.items.some(c=>!validID(c.id)||!Number.isInteger(c.text)||typeof c.term!=='string'||typeof c.context_meaning!=='string'||typeof c.loc!=='string'||!['highlight','supplement'].includes(c.kind)||!['verified','not_found'].includes(c.book_status)||!Array.isArray(c.book)||c.book.some(b=>!object(b)||typeof b.headword!=='string'||typeof b.original_meaning!=='string'||!Number.isInteger(b.entry_id)||!Number.isInteger(b.a4_page)||!Number.isInteger(b.english_page))))throw new Error('dataset schema');
      if(token!==serial)return;
      catalog=cat;dataset=data;state.dataset=dataset.id;
      const selected=params.get('scope');if(Object.hasOwn(scopes,selected))state.scope=selected;
      $('reviewDataset').innerHTML=cat.sets.map(s=>`<option value="${esc(s.id)}">${esc(s.title)}</option>`).join('');
      $('reviewScope').innerHTML=Object.entries(scopes).map(([k,v])=>`<option value="${k}">${v}</option>`).join('');
      settingsToUI();$('reviewTitle').textContent=dataset.title;$('reviewEdition').textContent=`READING REVIEW · ${dataset.version||cat.version}`;
      $('reviewWorkspace').hidden=false;$('reviewLoading').hidden=true;
      ['reviewExport','reviewImport','reviewReset'].forEach(id=>$(id).disabled=false);
      opened.clear();applyFilters();writeRoute();
    } catch(error) { if(token!==serial)return;$('reviewLoadingMessage').textContent='复盘内容暂未加载成功。记录未清空，请检查网络后重试。';$('reviewRetry').hidden=false; }
  }
  $('reviewList').addEventListener('click',event=>{
    const button=event.target.closest('button');if(!button)return;
    const id=button.dataset.reveal||button.dataset.id,item=dataset.items.find(c=>c.id===id);if(!item)return;
    if(button.dataset.reveal){if(opened.has(id))opened.delete(id);else opened.add(id);savePosition(item);render();const focused=$('item-'+id)?.querySelector('[data-reveal]');focused?.focus({preventScroll:true});}
    else if(button.dataset.rate&&Object.hasOwn(names,button.dataset.rate)){
      state.ratings[key(item)]={status:button.dataset.rate,updatedAt:now()};savePosition(item);const previousIndex=index;applyFilters(false);
      if(state.view==='cards' && state.status==='all' && previousIndex<filtered.length-1){index++;savePosition(filtered[index]);render();}
      toast(`已记录：${item.term} · ${names[button.dataset.rate]}`);
    }
  });
  for(const [id,field] of [['reviewScope','scope'],['reviewKind','kind'],['reviewStatus','status']])$(id).addEventListener('change',()=>{state[field]=$(id).value;opened.clear();save();applyFilters();writeRoute();});
  $('reviewDataset').addEventListener('change',()=>{state.dataset=$('reviewDataset').value;state.scope='all';save();const u=new URL(location.href);u.searchParams.set('set',state.dataset);u.searchParams.set('scope','all');history.replaceState(null,'',u);load();});
  $('reviewSearch').addEventListener('input',()=>{opened.clear();applyFilters(false);});
  document.querySelectorAll('[data-review-view]').forEach(b=>b.addEventListener('click',()=>{state.view=b.dataset.reviewView;opened.clear();save();applyFilters();}));
  $('reviewHideAll').addEventListener('click',()=>{opened.clear();render();});
  function move(direction){index=Math.max(0,Math.min(filtered.length-1,index+direction));if(filtered[index]){opened.clear();savePosition(filtered[index]);render();}}
  $('reviewPrev').addEventListener('click',()=>move(-1));$('reviewNext').addEventListener('click',()=>move(1));
  $('reviewResume').addEventListener('click',()=>{$('item-'+state.positions[positionKey()]?.id)?.scrollIntoView({behavior:'smooth',block:'start'});});
  $('reviewTheme').addEventListener('click',()=>{state.theme=state.theme==='night'?'day':'night';document.documentElement.dataset.theme=state.theme;save();});
  $('reviewRetry').addEventListener('click',load);
  $('reviewExport').addEventListener('click',()=>{
    const payload={app:APP,version:1,exportedAt:now(),state};
    if(storageProtected){try{payload.unrecognizedOriginal=localStorage.getItem(KEY);}catch(_){} }
    const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download='exam-reading-review-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  $('reviewImport').addEventListener('click',()=>$('reviewImportInput').click());
  $('reviewImportInput').addEventListener('change',async event=>{
    const input=event.target,file=input.files[0];if(!file)return;
    try {
      if(file.size>5*1024*1024)throw new Error('too large');
      const raw=JSON.parse(await file.text());if(raw.app!==APP||raw.version!==1||!object(raw.state)||raw.state.version!==1)throw new Error('format');
      const incoming=sanitize(raw.state);
      state.ratings=merge(state.ratings,incoming.ratings);state.positions=merge(state.positions,incoming.positions);save();applyFilters();toast(storageOK?'已按时间合并本模块记录，较旧自评不会覆盖较新自评。':'已在当前会话合并，但浏览器尚不能保存。请导出备份，刷新会丢失此次导入。');
    }catch(_){toast('导入失败：请选择本模块导出的 JSON。旧词卡导出请到旧词卡入口导入。');}
    finally { input.value=''; }
  });
  $('reviewReset').addEventListener('click',()=>{
    if(!confirm('只清空真题复盘模块的本地自评、位置和偏好。旧词卡熟悉度、速览位置和草稿不受影响。建议先导出备份。继续吗？'))return;
    try {localStorage.removeItem(KEY);storageProtected=false;storageOK=true;}catch(_){storageOK=false;toast('浏览器未允许清空记录，未确认删除成功。');return;}
    state=fresh();state.dataset=dataset.id;opened.clear();$('reviewSearch').value='';document.documentElement.dataset.theme=state.theme;settingsToUI();applyFilters();writeRoute();labelStorage();toast('本模块记录已清空，旧词卡记录未改动。');
  });
  window.addEventListener('storage',event=>{if(event.key!==KEY||!dataset)return;try{const next=JSON.parse(event.newValue||'null');if(event.newValue===null){state=fresh();state.dataset=dataset.id;opened.clear();$('reviewSearch').value='';settingsToUI();document.documentElement.dataset.theme=state.theme;applyFilters();toast('本模块记录已在另一标签页清空。');return;}if(next?.version===1){const incoming=sanitize(next);state.ratings=merge(state.ratings,incoming.ratings);state.positions=merge(state.positions,incoming.positions);applyFilters(false);}}catch(_){} });
  window.addEventListener('popstate',()=>load());
  load();
})();
