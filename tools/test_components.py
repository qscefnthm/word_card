"""Offline component tests. No navigation; JSON and Storage are in-memory fixtures.
Does NOT verify native persistent storage, CSP/network loading, or a live deployment.
"""
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
import json
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];O=R/'test-results';O.mkdir(exist_ok=True)
KEY='word-card-site-v2'
s=BeautifulSoup((R/'index.html').read_text(),'html.parser')
for x in s.find_all('script')+s.find_all('link'):x.decompose()
for x in s.find_all('meta',attrs={'http-equiv':True}):x.decompose()
t=s.new_tag('style');t.string=(R/'assets/app.css').read_text();s.head.append(t)
HTML=str(s);JS=(R/'assets/app.js').read_text()
fixtures={'./data/catalog.json':json.loads((R/'data/catalog.json').read_text()),'./data/decks/2010-e1-text4.json':json.loads((R/'data/decks/2010-e1-text4.json').read_text())}
checks=[];errors=[]
def ok(n,b):
    assert b,n
    checks.append(n)
def boot(page,saved=None,blocked=False):
    page.set_content(HTML)
    page.evaluate('''({fixtures,saved,blocked})=>{
        window.__fixtures=fixtures;window.__offline=false;window.__saved=saved||{};
        Object.defineProperty(window,'localStorage',{configurable:true,value:{
            getItem(k){return Object.prototype.hasOwnProperty.call(window.__saved,k)?window.__saved[k]:null},
            setItem(k,v){if(blocked)throw new Error('storage unavailable');window.__saved[k]=String(v)},
            removeItem(k){delete window.__saved[k]}
        }});
        window.fetch=async function(path){
            if(window.__offline)throw new TypeError('Failed to fetch');
            if(!window.__fixtures[path])return new Response('not found',{status:404});
            return new Response(JSON.stringify(window.__fixtures[path]),{headers:{'Content-Type':'application/json'}})
        };
    }''',{'fixtures':fixtures,'saved':saved,'blocked':blocked})
    page.evaluate(JS)
    page.wait_for_function("!document.getElementById('workspace').hidden")
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':1440,'height':1000});page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    boot(page)
    ok('Original 32 cards and 10 core cards load',page.locator('#allPackCount').inner_text()=='32 张' and page.locator('#corePackCount').inner_text()=='10 张')
    ok('Starts with sympathy; answer concealed',page.locator('#word').inner_text()=='sympathy' and not page.locator('#answer').is_visible())
    ok('Rating cannot precede reveal',page.locator('[data-rating=known]').is_disabled())
    page.screenshot(path=str(O/'desktop-front.png'),full_page=True)
    page.click('#reveal');page.click('#bookDetails summary')
    ok('Reveals meaning and real reference ID',page.locator('#meaning').is_visible() and '#4294' in page.locator('#bookEntries').inner_text())
    page.screenshot(path=str(O/'desktop-answer.png'),full_page=True)
    page.click('[data-rating=unknown]');ok('Rating advances and counts exactly once',page.locator('#word').inner_text()=='compromise' and page.locator('#seenCount').inner_text()=='1')
    page.click('#theme');page.uncheck('#contextToggle')
    saved=page.evaluate('window.__saved')
    reload_page=ctx.new_page();reload_page.on('pageerror',lambda e:errors.append(str(e)));boot(reload_page,saved);page=reload_page
    ok('Restores serialized position/theme/context (mock Storage)',page.locator('#word').inner_text()=='compromise' and page.locator('html').get_attribute('data-theme')=='day' and not page.locator('#quoteBlock').is_visible())
    page.click('#openList');page.fill('#searchInput','支持')
    ok('Search uses Chinese meanings but answers remain concealed',page.locator('.word-row').count()>=1 and not page.locator('.row-meaning').first.is_visible())
    page.click('[data-close=listDialog]');page.click('[data-pack=hard]')
    ok('Unfamiliar-only pack filters correctly',page.locator('#word').inner_text()=='sympathy' and '/ 1' in page.locator('#roundPosition').inner_text())
    page.click('#reveal');page.click('[data-rating=known]');ok('Last answer completes round',page.locator('#doneView').is_visible())
    page.evaluate("URL.createObjectURL=(b)=>{window.__exportedBlob=b;return 'about:blank'};HTMLAnchorElement.prototype.click=function(){}")
    page.click('#exportQuick');export=page.evaluate('async()=>JSON.parse(await window.__exportedBlob.text())')
    ok('Export payload retains real self-rating',export['app']=='word-card' and export['ratings']['sympathy']['status']=='known')
    legacy={'app':'night-vocab-2010t4','version':1,'ratings':{'sympathy':{'status':'unknown','updatedAt':'2001-01-01T00:00:00Z'},'lobby':{'status':'fuzzy','updatedAt':'2026-01-01T00:00:00Z'}}}
    page.locator('#importInput').set_input_files({'name':'legacy.json','mimeType':'application/json','buffer':json.dumps(legacy).encode()})
    page.wait_for_timeout(200)
    stored=page.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',KEY)
    ok('Legacy import merges without overwriting newer rating',stored['ratings']['sympathy']['status']=='known' and stored['ratings']['lobby']['status']=='fuzzy')
    page.click('[data-pack=core]');page.click('#skip');ok('Skipping does not count as studied',page.locator('#seenCount').inner_text()=='0')
    page.evaluate('''()=>{const d=window.__fixtures['./data/decks/2010-e1-text4.json'];const c=structuredClone(d.cards[0]);c.id='test-added';c.core=false;d.cards.push(c);const cat=window.__fixtures['./data/catalog.json'];cat.version='test-update';cat.decks[0].count=33;}''')
    page.click('#checkUpdate');page.wait_for_function("document.getElementById('allPackCount').textContent==='33 张'")
    ok('Update preserves ratings and running round snapshot',page.locator('#word').inner_text()=='compromise' and '/ 10' in page.locator('#roundPosition').inner_text() and page.evaluate('(k)=>JSON.parse(localStorage.getItem(k)).ratings.sympathy.status',KEY)=='known')
    page.click('[data-pack=all]');ok('New cards appear when starting a full round','/ 33' in page.locator('#roundPosition').inner_text())
    page.evaluate('window.__offline=true');page.click('#checkUpdate');page.wait_for_selector('#retryLoad:visible')
    ok('Failed update keeps already loaded cards',page.locator('#workspace').is_visible() and page.locator('#retryLoad').is_visible())
    page.evaluate('window.__offline=false');page.click('#retryLoad');page.wait_for_function("document.getElementById('loadingBox').hidden")
    ok('Retry recovers from failed update',page.locator('#allPackCount').inner_text()=='33 张')
    page.evaluate('''()=>{const d=structuredClone(window.__fixtures['./data/decks/2010-e1-text4.json']);d.id='test-deck';d.title='测试篇目';window.__fixtures['./data/decks/test-deck.json']=d;window.__fixtures['./data/catalog.json'].decks.push({id:'test-deck',title:'测试篇目',file:'data/decks/test-deck.json',count:33});}''')
    page.click('[data-pack=core]');page.click('#skip');page.click('#checkUpdate');page.wait_for_selector('#deckSelect option[value=test-deck]',state='attached')
    page.select_option('#deckSelect','test-deck');page.wait_for_function("document.getElementById('deckTitle').textContent==='测试篇目'")
    ok('New deck loads and shares stable term ratings','认识' in page.locator('#priorStatus').inner_text())
    page.select_option('#deckSelect','2010-e1-text4');page.wait_for_function("document.getElementById('word').textContent==='compromise'")
    ok('Each deck retains its own round position',page.locator('#word').inner_text()=='compromise')
    mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1);mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)));boot(mp)
    ok('Separate browser begins independently; no cloud-sync claim',mp.locator('#seenCount').inner_text()=='0' and '不自动同步' in mp.locator('#storageInfo').inner_text())
    ok('Mobile front has no horizontal overflow',mp.evaluate('document.documentElement.scrollWidth <= innerWidth'))
    mp.screenshot(path=str(O/'mobile-front.png'),full_page=True);mp.click('#reveal');mp.click('#bookDetails summary')
    ok('Mobile answer has no horizontal overflow',mp.evaluate('document.documentElement.scrollWidth <= innerWidth'))
    mp.screenshot(path=str(O/'mobile-answer.png'),full_page=True);mp.click('[data-rating=fuzzy]')
    ok('Mobile touch self-rating advances',mp.locator('#word').inner_text()=='compromise')
    bp=browser.new_page();bp.on('pageerror',lambda e:errors.append(str(e)));boot(bp,blocked=True)
    ok('Storage failure visibly disclosed','不能保存' in bp.locator('#storageInfo').inner_text())
    bp.click('#reveal');bp.click('[data-rating=known]');ok('Study remains usable on storage failure',bp.locator('#word').inner_text()=='compromise')
    ok('No JavaScript runtime errors',not errors)
    browser.close()
result={'testMode':'Offline DOM/component tests with in-memory JSON fetch and Storage; not live/network/native-persistence QA','checksPassed':len(checks),'checks':checks,'runtimeErrors':errors}
(O/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
