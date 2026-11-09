// Supplemental offline DOM regression. Requires linkedom; does not replace browser tests.
const {parseHTML}=require('linkedom');
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const root=require('path').resolve(__dirname,'..');
const code=fs.readFileSync(root+'/assets/review.js','utf8');
const html=fs.readFileSync(root+'/review.html','utf8');
const data=JSON.parse(fs.readFileSync(root+'/data/review/2014-e1.json','utf8'));
const catalog=JSON.parse(fs.readFileSync(root+'/data/review/catalog.json','utf8'));
const KEY='exam-reading-review-v1';
const OLD=['word-card-site-v2','word-card-quick-v1','word-card-recall-v1','zhou-night-vocab-2010t4-v1'];
let checks=[];
function ok(name,value){assert(value,name);checks.push(name);}
const tick=()=>new Promise(r=>setImmediate(r));
async function boot(saved={},options={}) {
 const {window,document}=parseHTML(html);
 Object.defineProperty(window.HTMLSelectElement.prototype,'value',{configurable:true,get(){return [...this.querySelectorAll('option')].find(x=>x.hasAttribute('selected'))?.getAttribute('value')||this.querySelector('option')?.getAttribute('value')||'';},set(v){for(const option of this.querySelectorAll('option')){if(option.getAttribute('value')===v)option.setAttribute('selected','');else option.removeAttribute('selected')}}});
 const localStorage={getItem:k=>{if(options.readError)throw Error('blocked');return saved[k]??null},setItem:(k,v)=>{if(options.writeError)throw Error('blocked');saved[k]=v;},removeItem:k=>delete saved[k]};
 const location=new URL(options.url||'https://example.test/word_card/review.html');
 const history={replaceState:(_a,_b,u)=>{location.href=u.toString();}};
 let blob;
 class FakeURL extends URL {static createObjectURL(b){blob=b;return 'blob:test'}static revokeObjectURL(){}}
 const context={window,document,localStorage,location,history,URL:FakeURL,URLSearchParams,Blob,console,confirm:()=>options.confirm??true,setTimeout:()=>1,clearTimeout:()=>{},fetch:async url=>{if(options.fetchError)return{ok:false};return{ok:true,json:async()=>url.includes('catalog')?structuredClone(catalog):structuredClone(data)}}};
 vm.runInNewContext(code,context);await tick();await tick();
 const $=sel=>document.querySelector(sel);
 const click=sel=>{const el=$(sel);assert(el,sel);el.dispatchEvent(new window.Event('click',{bubbles:true}));};
 const change=(sel,value)=>{$(sel).value=value;$(sel).dispatchEvent(new window.Event('change',{bubbles:true}));};
 const input=(v)=>{$('#reviewSearch').value=v;$('#reviewSearch').dispatchEvent(new window.Event('input',{bubbles:true}));};
 const importData=async payload=>{const input=$('#reviewImportInput');input.files=[{size:100,text:async()=>typeof payload==='string'?payload:JSON.stringify(payload)}];input.dispatchEvent(new window.Event('change',{bubbles:true}));await tick();};
 return{window,document,saved,$,click,change,input,importData,export:async()=>{click('#reviewExport');return JSON.parse(await blob.text())},state:()=>JSON.parse(saved[KEY]||'null')};
}
(async()=>{
 const saved=Object.fromEntries(OLD.map(k=>[k,' SENTINEL '+k+' ']));const original=structuredClone(saved);let p=await boot(saved);
 ok('129 audited items load',p.document.querySelectorAll('.review-item').length===129);
 ok('All meanings start concealed',p.document.querySelectorAll('.review-answer:not([hidden])').length===0);
 for(const scope of ['1','2','3','4','1-2','3-4','all']){p.change('#reviewScope',scope);ok('Scope '+scope,p.document.querySelectorAll('.review-item').length===data.items.filter(x=>scope==='all'||scope.split('-').map(Number).includes(x.text)).length);}
 p.change('#reviewKind','supplement');ok('12 supplemental groups',p.document.querySelectorAll('.review-item').length===12);p.change('#reviewKind','highlight');ok('117 highlight groups',p.document.querySelectorAll('.review-item').length===117);p.change('#reviewKind','all');
 p.input('UPFRONT');ok('Case-insensitive search',p.document.querySelectorAll('.review-item').length===1);p.input('nothing123');ok('Empty filter shown',!p.$('#reviewEmpty').hidden);p.input('');
 p.click('[data-reveal]');ok('Reveals meaning and book',p.document.querySelectorAll('.review-answer:not([hidden])').length===1&&p.$('.review-answer').textContent.includes(data.items[0].book[0].original_meaning));
 p.click('[data-rate="unknown"]');const rk=data.id+'/'+data.items[0].id;ok('Rating records per batch ID',p.state().ratings[rk].status==='unknown');
 p.change('#reviewStatus','hard');ok('Hard filter exact',p.document.querySelectorAll('.review-item').length===1);p.change('#reviewStatus','all');p.click('[data-review-view="cards"]');p.click('#reviewNext');p.click('#reviewNext');const pos=p.$('.review-item').id;p=await boot(saved);ok('Refresh restores view and position',p.$('.review-item').id===pos&&p.state().view==='cards');
 const output=await p.export();ok('Export has only new module',output.app==='exam-reading-review'&&!OLD.some(k=>JSON.stringify(output).includes(k)));
 const old=structuredClone(output);old.state.ratings[rk]={status:'known',updatedAt:'2001-01-01T00:00:00.000Z'};await p.importData(old);ok('Old import cannot replace newer rating',p.state().ratings[rk].status==='unknown');
 const before=saved[KEY];await p.importData('{broken');ok('Malformed import preserves state',saved[KEY]===before);await p.importData({app:'word-card',version:2});ok('Old-card backup rejected',saved[KEY]===before);
 ok('All old keys byte-identical',OLD.every(k=>saved[k]===original[k]));p.click('#reviewReset');ok('Reset only removes new key',saved[KEY]===undefined&&OLD.every(k=>saved[k]===original[k]));await p.importData(output);ok('Backup restores after reset',Object.keys(p.state().ratings).length>0);
 let event=new p.window.Event('storage');event.key=KEY;event.newValue=null;delete saved[KEY];p.window.dispatchEvent(event);p.click('#reviewTheme');ok('Cross-tab reset does not resurrect ratings',Object.keys(p.state().ratings).length===0);
 const corrupt={[KEY]:'{broken'};p=await boot(corrupt);await p.importData(output);ok('Protected corrupt storage is preserved',corrupt[KEY]==='{broken');ok('Protected import gives session-only warning',p.$('#reviewToast').textContent.includes('当前会话'));
 p=await boot({}, {readError:true});ok('Read access failure not called corrupt data',p.$('#reviewSave').textContent.includes('不能保存')&&!p.$('#reviewSave').textContent.includes('格式'));
 p=await boot({}, {writeError:true});p.click('[data-reveal]');p.click('[data-rate="unknown"]');ok('Unavailable writes disclosed',p.$('#reviewSave').textContent.includes('不能保存'));
 p=await boot({}, {fetchError:true});ok('Network failure shown with retry',!p.$('#reviewRetry').hidden&&p.$('#reviewWorkspace').hidden);
 console.log(JSON.stringify({mode:'Node + linkedom DOM, in-memory fetch/storage; NOT browser/CSP/layout/native storage QA',checksPassed:checks.length,checks},null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
