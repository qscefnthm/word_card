"""Offline quick-view regression using JSON/Storage/history fixtures.
Tests DOM, serialization, error handling and in-memory MP3 playback.
Does not verify live HTTP, CSP, native storage or a HarmonyOS device.
Run from a complete checkout: python3 tools/test_quick_review.py
"""
from pathlib import Path
from bs4 import BeautifulSoup
import json
import os
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('QUICK_TEST_OUTPUT', ROOT / 'test-results-quick'))
OUT.mkdir(parents=True, exist_ok=True)
CAT = json.loads((ROOT / 'data/catalog.json').read_text())
DECKS = {d['id']: json.loads((ROOT / d['file']).read_text()) for d in CAT['decks']}
N1=len(DECKS['2012-e1-text1']['cards'])
N2=len(DECKS['2012-e1-text2']['cards'])
KEY = 'word-card-site-v2'
QKEY = 'word-card-quick-v1'
RKEY = 'word-card-recall-v1'
checks, errors = [], []

soup = BeautifulSoup((ROOT / 'quick.html').read_text(), 'html.parser')
for tag in soup.find_all('script') + soup.find_all('link'):
    tag.decompose()
for tag in soup.find_all('meta', attrs={'http-equiv':True}):
    tag.decompose()
style = soup.new_tag('style')
style.string = (ROOT/'assets/app.css').read_text() + '\n' + (ROOT/'assets/quick.css').read_text() + '\n' + (ROOT/'assets/quick-extras.css').read_text()
soup.head.append(style)
HTML = str(soup)
FIXTURES = {'./data/catalog.json':CAT}
for entry in CAT['decks']:
    FIXTURES['./'+entry['file']] = DECKS[entry['id']]
    FIXTURES['./data/audio/'+entry['id']+'.json'] = json.loads((ROOT/'data/audio'/(entry['id']+'.json')).read_text())

def boot(page, saved=None, blocked=False, fail=False, deckid='2012-e1-text1'):
    page.set_content(HTML)
    saved = saved if saved is not None else {KEY:json.dumps({'version':2,'deckId':deckid,'ratings':{},'runs':{}})}
    page.evaluate("""({fixtures,saved,blocked,fail})=>{
      window.__fixtures=fixtures;window.__saved=saved;window.__failedDeck='';window.__failCatalog=fail;window.__route='';
      Object.defineProperty(window,'localStorage',{configurable:true,value:{
        getItem(k){if(blocked)throw new Error('storage blocked');return Object.prototype.hasOwnProperty.call(window.__saved,k)?window.__saved[k]:null},
        setItem(k,v){if(blocked)throw new Error('storage blocked');window.__saved[k]=String(v)}
      }});
      history.replaceState=(_,__,url)=>{window.__route=url};
      window.fetch=async path=>{
        if((window.__failCatalog && path==='./data/catalog.json') || path==='./data/decks/'+window.__failedDeck+'.json')return new Response('unavailable',{status:503});
        return path in window.__fixtures ? new Response(JSON.stringify(window.__fixtures[path]),{headers:{'Content-Type':'application/json'}}) : new Response('not found',{status:404});
      };
      const NativeAudio=window.Audio;window.__audios=[];
      window.Audio=function(...args){const a=new NativeAudio(...args);window.__audios.push(a);return a};
    }""",{'fixtures':FIXTURES,'saved':saved,'blocked':blocked,'fail':fail})
    page.evaluate((ROOT/'assets/quick-extras.js').read_text())
    page.evaluate((ROOT/'assets/quick.js').read_text())
    if not fail: ready(page)

def switched(page,ident):
    page.wait_for_function('(id) => window.__route.endsWith("deck="+id) && !document.getElementById("quickWorkspace").hidden',arg=ident)

def ok(label, condition):
    assert condition, label
    checks.append(label)

def ready(page):
    page.wait_for_function("!document.getElementById('quickWorkspace').hidden")

def stored(page, key):
    return page.evaluate('(key) => JSON.parse(localStorage.getItem(key))', key)

def watch(page):
    page.on('pageerror', lambda err: errors.append(str(err)))

def select(page, ident):
    page.select_option('#deckSelect', ident)
    switched(page,ident)

with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium'), headless=True, args=['--no-sandbox'])
        ctx = browser.new_context(viewport={'width':1280,'height':950})
        page = ctx.new_page(); watch(page)
        boot(page)
        main = {'version':2,'theme':'night','deckId':'2012-e1-text1','showContext':True,
                'ratings':{'sympathy':{'status':'known','updatedAt':'2026-10-01T00:00:00Z'}},
                'runs':{'untouched':{'ids':['sympathy'],'index':0,'sentinel':'preserve'}}}
        quick = {'version':1,'view':'cards','filter':'all',
                 'indices':{'2012-e1-text1:all':3,'2012-e1-text1:core':2,'2012-e1-text2:all':5}}
        page.evaluate('([a,b,key,qkey])=>{localStorage.setItem(key,JSON.stringify(a));localStorage.setItem(qkey,JSON.stringify(b))}', [main,quick,KEY,QKEY])
        saved=page.evaluate('window.__saved');page=ctx.new_page();watch(page);boot(page,saved)
        ok('Existing paged location restored',page.locator('#cardPosition').inner_text()==f'04 / {N1}')
        ok('Next-deck footer not shown in the middle of paged view',not page.locator('#nextDeckSection').is_visible())
        page.click('[data-view=list]')
        ok('Bilingual list unchanged and has next-deck footer', page.locator('.quick-row').count()==N1 and page.locator('#nextDeckButton').is_visible())
        ok('Next title follows catalog, not computed year numbering','2012 · 英语一 · Text 2' in page.locator('#nextDeckTitle').inner_text())
        page.click('[data-list-mode=english]')
        ok('Selected recall tab matches displayed contents',page.locator('[data-list-mode=english]').get_attribute('aria-pressed')=='true' and page.locator('[data-list-mode=bilingual]').get_attribute('aria-pressed')=='false')
        page.screenshot(path=str(OUT/'desktop-english.png'),animations='disabled')
        ok('English recall displays inputs and hides every answer',page.locator('textarea').count()==N1 and page.locator('.recall-answer:visible').count()==0)
        ok('No original form, notes, or usage hints leak before reveal',page.locator('#quickList .quick-form').count()==0 and page.locator('#quickList .quick-zh').count()==0)
        ok('Search placeholder does not disclose a Chinese meaning',page.locator('#searchInput').get_attribute('placeholder')=='搜索英文词条')
        card = DECKS['2012-e1-text1']['cards'][0]
        row = page.locator('[data-recall-row]').first
        draft = '测试：先想中文 <script>不会执行</script>'
        row.locator('textarea').fill(draft)
        ok('Draft saved separately, with the matching term',stored(page,RKEY)['drafts']['2012-e1-text1/'+card['id']]['text']==draft)
        row.locator('[data-reveal-meaning]').click()
        ok('One click reveals only that meaning and phrase',page.locator('.recall-answer:visible').count()==1 and card['meaning'] in row.locator('.recall-answer').inner_text())
        row.locator('[data-reveal-meaning]').click()
        page.click('#toggleRecallAnswers')
        ok('Explicit show-all reveals current list',page.locator('.recall-answer:visible').count()==N1)
        page.click('#toggleRecallAnswers')
        ok('Hide-all restores English-only view',page.locator('.recall-answer:visible').count()==0)
        page.click('[data-filter=core]')
        ok('Core filtering works in recall view',page.locator('textarea').count()==sum(c['core'] for c in DECKS['2012-e1-text1']['cards']))
        ok('List filtering does not reset saved paged core position',stored(page,QKEY)['indices']['2012-e1-text1:core']==2)
        page.click('[data-filter=all]')
        page.fill('#searchInput','peer pressure')
        ok('Recall searches only displayed English terms',page.locator('[data-recall-row]').count()==1)
        ok('Draft survives search and filter changes',page.locator('textarea').input_value()==draft)
        page.fill('#searchInput','not-a-match-xyz')
        ok('Empty recall search is safe and can still go to next deck',page.locator('textarea').count()==0 and page.locator('#nextDeckButton').is_enabled())
        page.fill('#searchInput','')
        saved=page.evaluate('window.__saved');page=ctx.new_page();watch(page);boot(page,saved)
        ok('Reboot from serialized Storage retains recall mode and typed draft',page.locator('[data-list-mode=english]').get_attribute('aria-pressed')=='true' and page.locator('textarea').first.input_value()==draft)
        ok('Reboot conceals all answers again',page.locator('.recall-answer:visible').count()==0)
        page.click('[data-filter=core]')
        page.click('#nextDeckButton')
        switched(page,'2012-e1-text2')
        ok('Next deck preserves list view, English recall and core filter',page.locator('#listView').is_visible() and page.locator('textarea').count()==sum(c['core'] for c in DECKS['2012-e1-text2']['cards']) and page.locator('[data-filter=core]').get_attribute('aria-pressed')=='true')
        last=CAT['decks'][-1]['id']
        if last!='2012-e1-text2': select(page,last)
        ok('Final catalog entry stops without wrapping',page.locator('#nextDeckButton').is_disabled() and '最后一篇' in page.locator('#nextDeckTitle').inner_text())
        if last!='2012-e1-text2': select(page,'2012-e1-text2')
        page.click('[data-filter=all]'); page.click('[data-view=cards]')
        ok('Destination paged position is not overwritten by list navigation',page.locator('#cardPosition').inner_text()==f'06 / {N2}')
        select(page,'2012-e1-text1')
        ok('Return restores original paged position',page.locator('#cardPosition').inner_text()==f'04 / {N1}')
        for _ in range(N1-4): page.click('#nextCard')
        ok('Next deck option appears on last card before completion',page.locator('#cardPosition').inner_text()==f'{N1} / {N1}' and page.locator('#nextDeckButton').is_visible())
        page.click('#nextCard')
        ok('Next deck option remains on completion screen',page.locator('#quickDone').is_visible() and page.locator('#nextDeckButton').is_visible())
        page.screenshot(path=str(OUT/'desktop-complete.png'),full_page=True,animations='disabled')
        page.evaluate("window.__failedDeck='2012-e1-text2'")
        page.click('#nextDeckButton')
        page.wait_for_function("document.getElementById('nextDeckButton').disabled === false")
        ok('Failed next load preserves old deck and completion screen', page.evaluate("window.__route.endsWith('deck=2012-e1-text1')") and page.locator('#quickDone').is_visible())
        page.evaluate("window.__failedDeck=''")
        page.click('#nextDeckButton');switched(page,'2012-e1-text2')
        ok('Retry next succeeds without duplicate navigation',page.locator('#cardPosition').inner_text()==f'06 / {N2}')
        page.click('[data-view=list]');page.click('[data-list-mode=english]')
        clip = page.locator('.quick-speak').first
        clip.click()
        page.wait_for_function("document.querySelector('.quick-speak.playing') !== null")
        ok('Bundled MP3 plays in offline English recall view',page.evaluate("window.__audios.length > 0 && window.__audios.at(-1).src.startsWith('blob:') && !window.__audios.at(-1).paused"))
        page.click('[data-view=cards]')
        ok('View switch stops pronunciation',page.locator('.playing').count()==0)
        ok('Official ratings and running rounds remain exactly unchanged',stored(page,KEY)['ratings']==main['ratings'] and stored(page,KEY)['runs']==main['runs'])
        # Verify every deck/term in each display without changing source data.
        page.click('[data-view=list]')
        for ident,d in DECKS.items():
            select(page,ident)
            page.click('[data-filter=all]')
            page.click('[data-list-mode=bilingual]')
            assert page.locator('.quick-row').count()==len(d['cards'])
            page.click('[data-list-mode=english]')
            assert page.locator('.recall-row .quick-term').all_text_contents()==[c['term'] for c in d['cards']]
            assert page.locator('.recall-answer:visible').count()==0
            for i,c in enumerate(d['cards']):
                assert c['meaning'] in page.locator('.recall-answer').nth(i).text_content()
        ok('All catalog cards keep correct terms/answers in bilingual and English views',True)
        # Representative mobile layout, long phrases, theme and next deck.
        mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
        mp=mobile.new_page();watch(mp);boot(mp)
        mp.click('[data-view=list]');mp.click('[data-list-mode=english]')
        mp.screenshot(path=str(OUT/'mobile-english.png'),animations='disabled')
        ok('Mobile English list has no horizontal overflow',mp.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        mp.locator('textarea').first.fill('我的测试释义')
        mp.locator('[data-reveal-meaning]').first.click()
        mp.screenshot(path=str(OUT/'mobile-checked.png'))
        mp.click('#theme')
        ok('Mobile day theme and answer layout have no horizontal overflow',mp.evaluate('document.documentElement.scrollWidth <= innerWidth') and mp.locator('html').get_attribute('data-theme')=='day')
        mp.click('[data-list-mode=bilingual]')
        ok('Original bilingual mobile view has no horizontal overflow',mp.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        mp.locator('#nextDeckButton').scroll_into_view_if_needed()
        mp.screenshot(path=str(OUT/'mobile-next.png'))
        mp.click('#nextDeckButton');switched(mp,'2012-e1-text2')
        ok('Mobile next deck resets scroll to top',mp.evaluate('scrollY')==0)
        mp.set_viewport_size({'width':320,'height':700});mp.click('[data-list-mode=english]')
        ok('320px narrow layout fits long terms',mp.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        # Storage fixtures validate fallback handling, not native browser persistence.
        bp=browser.new_page();watch(bp);boot(bp,blocked=True);bp.click('[data-view=list]');bp.click('[data-list-mode=english]')
        bp.locator('textarea').first.fill('临时输入')
        ok('Blocked storage remains usable and clearly warns', '无法保存' in bp.locator('#recallStorage').inner_text())
        xp=browser.new_page();watch(xp);boot(xp,saved={QKEY:json.dumps({'version':1,'view':'list'})})
        ok('Old quick preference without indices does not crash',xp.locator('#listView').is_visible())
        fp=browser.new_page();watch(fp);boot(fp,fail=True);fp.wait_for_selector('#retryQuickLoad:visible')
        fp.evaluate('window.__failCatalog=false');fp.click('#retryQuickLoad');ready(fp)
        ok('Initial load failure recovers using explicit retry',fp.locator('#quickWorkspace').is_visible())
        ok('No JavaScript runtime errors',not errors)
        browser.close()
result={'mode':'Offline DOM with mock JSON fetch/Storage/history; not live HTTP/CSP/native persistence/HarmonyOS',
        'checksPassed':len(checks),'checks':checks,'runtimeErrors':errors}
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
