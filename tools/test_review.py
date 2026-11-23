"""Real localhost HTTP + Chromium QA with native localStorage; no user records.
Outputs stay outside the repository. This is not live Pages or physical-device QA.
"""
from pathlib import Path
import copy, functools, http.server, json, os, shutil, threading
from playwright.sync_api import sync_playwright, expect
R=Path(__file__).resolve().parents[1]
O=Path(os.environ.get('REVIEW_TEST_OUTPUT','/tmp/wordcard-review-tests'));O.mkdir(parents=True,exist_ok=True)
KEY='exam-reading-review-v1'
OLD={k:' {"syntheticSentinel":"'+k+'", "bytes": 1} ' for k in ['word-card-site-v2','word-card-quick-v1','word-card-recall-v1','zhou-night-vocab-2010t4-v1']}
checks=[];errors=[]
def ok(name,condition):
    assert condition,name
    checks.append(name)
def untouched(page):
    ok('All four legacy keys remain byte-identical',page.evaluate('(keys)=>Object.fromEntries(keys.map(k=>[k,localStorage.getItem(k)]))',list(OLD))==OLD)
def store(page):return page.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',KEY)
def raw_storage(page):return page.evaluate('()=>Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))')
def open_details(page):page.locator('.review-answer:not([hidden]) .review-detail:not([open]) summary').first.click()
def columns_align(page):
    return page.locator('.review-item').first.evaluate('el=>{const a=el.querySelector(".review-item-top").getBoundingClientRect();const b=el.querySelector(".review-answer").getBoundingClientRect();return a.width>0 && b.width>0 && a.x<b.x && Math.abs(a.right-b.left)<2 && Math.abs(a.y-b.y)<2}')
def upload(page,payload):
    page.locator('#reviewImportInput').set_input_files({'name':'synthetic.json','mimeType':'application/json','buffer':(payload if isinstance(payload,str) else json.dumps(payload)).encode()})
    expect(page.locator('#reviewImportInput')).to_have_value('')

def check_real_batch_routes(browser, base, catalog):
    sets = {entry['id']: entry for entry in catalog['sets']}
    context = browser.new_context(viewport={'width': 390, 'height': 844})
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))

    def expected_rows(set_id, sections):
        data = json.loads((R / sets[set_id]['file']).read_text())
        return [row for row in data['items'] if row['text'] in sections]

    def check_rows(name, rows):
        expected = [row['id'] for row in rows]
        expect(page.locator('.review-item')).to_have_count(len(expected))
        actual = page.locator('.review-item').evaluate_all('(els)=>els.map(el=>el.dataset.item)')
        ok(name, bool(expected) and actual == expected)

    try:
        page.goto(base + '/review.html?set=2012-e1&scope=4')
        expect(page.locator('#reviewTitle')).to_have_text(sets['2012-e1']['title'])
        expect(page.locator('#reviewScope')).to_have_value('4')
        scope_values = page.locator('#reviewScope option').evaluate_all('(options)=>options.map(o=>o.value)')
        ok('Single-Text year presents only available scopes', set(scope_values) == {'all', '4'})
        check_rows('2012 Text 4 deep link loads exact rows', expected_rows('2012-e1', [4]))

        page.select_option('#reviewDataset', '2017-e1-other')
        expect(page.locator('#reviewTitle')).to_have_text(sets['2017-e1-other']['title'])
        for value, label in [('1', '完形填空'), ('2', '新题型'), ('3', '翻译')]:
            rows = expected_rows('2017-e1-other', [int(value)])
            page.select_option('#reviewScope', value)
            expect(page.locator('#reviewScope option:checked')).to_contain_text(label)
            check_rows('2017 ' + label + ' loads the correct entries', rows)
            ok(label + ' labels match the entries', label in page.locator('.review-meta').first.inner_text())
            expect(page.locator('.review-answer:visible')).to_have_count(0)
            page.click('#reviewShowAll')
            expect(page.locator('.review-meaning:visible')).to_have_text([row['context_meaning'] for row in rows])
            if value == '2':
                page.reload()
                expect(page.locator('#reviewTitle')).to_have_text(sets['2017-e1-other']['title'])
                expect(page.locator('#reviewScope')).to_have_value('2')
                check_rows('2017 section route survives refresh', rows)
                ok('Ordering section uses passage letters', '选段 ' in page.locator('.review-meta').first.inner_text())

        page.select_option('#reviewDataset', '2015-e1')
        expect(page.locator('#reviewTitle')).to_have_text(sets['2015-e1']['title'])
        for scope, sections in [('1-2', [1,2]), ('3-4', [3,4])]:
            page.select_option('#reviewScope', scope)
            check_rows('Paired reading scope returns after switching batch '+scope, expected_rows('2015-e1', sections))
            expect(page.locator('.review-answer:visible')).to_have_count(0)
    finally:
        context.close()

def check_desktop_pronunciation(browser, base, catalog):
    """Exercise the browser UI with deterministic Edge-style Web Speech events."""
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    context.add_init_script("""
      class MockUtterance extends EventTarget {
        constructor(text) { super(); this.text = text; }
      }
      const voices = [
        {name: 'Microsoft Xiaoxiao', lang: 'zh-CN', default: true, localService: true},
        {name: 'Microsoft Jenny Online (Natural) - English (United States)',
         lang: 'en-US', default: false, localService: false}
      ];
      const calls = [];
      let active;
      function finish(type, error) {
        if (!active) return;
        const utterance = active;
        active = null;
        const event = Object.assign(new Event(type), {error});
        utterance.dispatchEvent(event);
        utterance['on' + type]?.(event);
      }
      const speech = Object.assign(new EventTarget(), {
        getVoices: () => voices,
        cancel() { if (active) { calls.push({type: 'cancel'}); finish('error', 'canceled'); } },
        speak(u) {
          calls.push({type: 'speak', text: u.text, lang: u.lang, voice: u.voice?.name});
          active = u;
          const event = new Event('start');
          u.dispatchEvent(event);
          u.onstart?.(event);
        }
      });
      Object.defineProperty(speech, 'speaking', {get: () => !!active});
      Object.defineProperty(window, 'speechSynthesis', {value: speech});
      Object.defineProperty(window, 'SpeechSynthesisUtterance', {value: MockUtterance});
      window.voiceTest = {calls, finish, addLocal() {
        voices.push({name: 'Microsoft David', lang: 'en-US', localService: true});
      }};
    """)
    try:
        dataset = next(entry for entry in catalog['sets'] if entry['id'] == '2012-e1')
        rows = json.loads((R / dataset['file']).read_text())['items']
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + '/review.html?set=2012-e1&scope=4')
        expect(page.locator('#reviewTitle')).to_have_text(dataset['title'])
        say = page.locator('[data-speak]')
        expect(say).to_have_count(len(rows))
        page.evaluate('(values)=>Object.entries(values).forEach(([k,v])=>localStorage.setItem(k,v))', OLD)
        before = raw_storage(page)

        def hear(index, term, count):
            say.nth(index).click()
            page.wait_for_function(
                "n => voiceTest.calls.filter(c => c.type === 'speak').length === n",
                arg=count)
            spoken = page.evaluate("voiceTest.calls.filter(c => c.type === 'speak').at(-1)")
            ok('Pronounces the displayed English: ' + term, spoken['text'] == term)
            ok('Selects the English voice despite the Chinese system default',
               spoken['lang'].lower() == 'en-us' and 'Jenny' in (spoken['voice'] or ''))
            expect(page.locator('.review-answer:visible')).to_have_count(0)

        hear(0, rows[0]['term'], 1)
        hear(1, rows[1]['term'], 2)
        ok('Changing word cancels previous speech',
           page.evaluate("voiceTest.calls.filter(c => c.type === 'cancel').length") == 1)
        page.evaluate("voiceTest.finish('end')")
        hear(1, rows[1]['term'], 3)
        page.evaluate("voiceTest.finish('end')")
        hear(1, rows[1]['term'], 4)
        page.evaluate("voiceTest.finish('end')")
        ok('Listening and retry leave every storage byte untouched', raw_storage(page) == before)

        page.click('[data-review-view=cards]')
        expect(say).to_have_count(1)
        before = raw_storage(page)
        hear(0, rows[0]['term'], 5)
        page.evaluate("voiceTest.addLocal(); voiceTest.finish('error', 'network')")
        page.wait_for_function("() => voiceTest.calls.at(-1)?.voice === 'Microsoft David'")
        ok('Online failure retries the same English on a local voice',
           page.evaluate("voiceTest.calls.at(-1).text") == rows[0]['term'])
        expect(say).to_have_attribute('data-speech-state', 'speaking')
        page.evaluate("voiceTest.finish('end')")
        expect(say).to_have_attribute('data-speech-state', 'idle')
        expect(page.locator('.review-answer:visible')).to_have_count(0)
        ok('Single item listening leaves ratings and position intact', raw_storage(page) == before)

        other = next(entry for entry in catalog['sets'] if entry['id'] == '2017-e1-other')
        page.select_option('#reviewDataset', other['id'])
        expect(page.locator('#reviewTitle')).to_have_text(other['title'])
        page.select_option('#reviewScope', '1')
        first_cloze = next(row for row in json.loads((R / other['file']).read_text())['items']
                           if row['text'] == 1)
        hear(0, first_cloze['term'], 7)
        page.select_option('#reviewScope', '3')
        expect(say).to_have_attribute('data-speech-state', 'idle')
        ok('Changing the section cancels the old word',
           page.evaluate("!speechSynthesis.speaking && voiceTest.calls.at(-1).type === 'cancel'"))
        # Exercise recovery with the real recording index and bytes. Media events here
        # are simulated; native MP3 decoding and playback are checked in desktop Edge.
        page.evaluate("""() => {
          window.finishedRecordings = 0;
          const clips = new Map();
          const createURL = URL.createObjectURL.bind(URL);
          URL.createObjectURL = blob => {
            const url = createURL(blob);
            clips.set(url, blob);
            return url;
          };
          window.Audio = class {
            async play() {
              const clip = clips.get(this.src);
              if (clip?.type !== 'audio/mpeg' || !clip.size) {
                throw new Error('Missing MP3 clip');
              }
              this.onplaying();
              this.ended = true;
              this.onended();
              window.finishedRecordings++;
            }
          };
        }""")
        before = raw_storage(page)
        say.click()
        page.evaluate("voiceTest.finish('error', 'network')")
        page.evaluate("voiceTest.finish('error', 'synthesis-failed')")
        try:
            page.wait_for_function("() => window.finishedRecordings === 1", timeout=10000)
        except Exception:
            print(page.evaluate("""() => ({
                voiceCalls: voiceTest.calls.slice(-6), error: document.querySelector('#reviewToast').textContent,
                files: performance.getEntriesByType('resource').filter(e=>e.name.includes('/audio/')).map(e=>e.name)
            })"""), flush=True)
            raise
        expect(say).to_have_attribute('data-speech-state', 'idle')
        call_count = page.evaluate("voiceTest.calls.length")
        say.click()
        page.wait_for_function("() => window.finishedRecordings === 2")
        ok('After voice failure the session can play the saved clip again immediately',
           page.evaluate("voiceTest.calls.length") == call_count)
        expect(page.locator('.review-answer:visible')).to_have_count(0)
        ok('Recorded pronunciation preserves every storage byte', raw_storage(page) == before)
        untouched(page)
    finally:
        context.close()

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(R)))
threading.Thread(target=server.serve_forever,daemon=True).start()
BASE=f'http://127.0.0.1:{server.server_port}'
cat=json.loads((R/'data/review/catalog.json').read_text());entry=next(x for x in cat['sets'] if x['id']==cat['defaultSet']);data=json.loads((R/entry['file']).read_text());items=data['items']
try:
 with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+'/');page.evaluate('(values)=>{for(const [k,v] of Object.entries(values))localStorage.setItem(k,v)}',OLD);page.reload()
    ok('Home keeps legacy collapsed and never loads old app',page.locator('#legacy').get_attribute('open') is None and page.locator('script[src*="assets/app.js"]').count()==0)
    untouched(page);page.screenshot(path=str(O/'desktop-home.png'),full_page=True)
    page.goto(BASE+'/review.html');page.wait_for_selector('#reviewWorkspace:visible')
    ok('Real dataset count loaded',page.locator('.review-item').count()==len(items))
    ok('English-first list conceals all answers',page.locator('.review-answer:visible').count()==0 and page.locator('.review-term').first.inner_text()==items[0]['term'])
    ok('Source labels visible', '黄标' in page.locator('#reviewList').inner_text() and '补充' in page.locator('#reviewList').inner_text())
    untouched(page)
    before=raw_storage(page)
    for _ in range(3):
        page.click('#reviewShowAll');ok('One action shows every Chinese meaning',page.locator('.review-answer:visible').count()==len(items) and page.locator('.review-meaning:visible').all_text_contents()==[x['context_meaning'] for x in items])
        ok('English left and Chinese right on desktop',columns_align(page));ok('Book details remain optional in full list',page.locator('.review-detail[open]').count()==0)
        page.click('#reviewHideAll');ok('One action hides every Chinese meaning',page.locator('.review-answer:visible').count()==0 and page.locator('.review-mask:visible').count()==len(items))
    ok('Repeated whole-page show/hide leaves every storage byte unchanged',raw_storage(page)==before)
    page.click('#reviewShowAll');page.screenshot(path=str(O/'desktop-bilingual.png'));page.click('#reviewHideAll')
    for scope in ['1','2','3','4','1-2','3-4','all']:
        page.select_option('#reviewScope',scope)
        expected=[x for x in items if scope=='all' or x['text'] in map(int,scope.split('-'))]
        ok('Scope '+scope+' has exact IDs',page.locator('.review-item').evaluate_all('(els)=>els.map(e=>e.dataset.item)')==[x['id'] for x in expected]);ok('Scope change conceals meanings',page.locator('.review-answer:visible').count()==0);before=raw_storage(page);page.click('#reviewShowAll');ok('Whole-page show follows current scope',page.locator('.review-answer:visible').count()==len(expected));ok('Scope show leaves storage bytes unchanged',raw_storage(page)==before);untouched(page)
    for kind in ['highlight','supplement','option','all']:
        page.select_option('#reviewKind',kind)
        expected=[x for x in items if kind=='all' or kind=='highlight' and x['kind'] not in ['supplement','supplemental'] or kind=='supplement' and x['kind'] in ['supplement','supplemental'] or kind=='option' and x['loc'].startswith('Q')]
        ok('Source filter '+kind,page.locator('.review-item').count()==len(expected));ok('Filter change conceals meanings',page.locator('.review-answer:visible').count()==0);page.click('#reviewShowAll')
    page.fill('#reviewSearch',items[0]['term'].upper());ok('Search change conceals meanings',page.locator('.review-answer:visible').count()==0);ok('Case-insensitive English search',page.locator('.review-item').count()==sum(items[0]['term'].lower() in x['term'].lower() for x in items))
    page.fill('#reviewSearch','__no_such_term__');ok('Empty-search explanation and safe bulk controls',page.locator('#reviewEmpty').is_visible() and page.locator('#reviewShowAll').is_disabled() and page.locator('#reviewHideAll').is_disabled());page.fill('#reviewSearch','')
    page.locator('[data-reveal]').first.click();open_details(page);ok('Reveal contextual meaning and original book definition',items[0]['context_meaning'] in page.locator('.review-answer').first.inner_text() and items[0]['book'][0]['original_meaning'] in page.locator('.review-answer').first.text_content() and page.locator('.review-answer').first.is_visible())
    page.locator('[data-rate=unknown]').first.click();rk=data['id']+'/'+items[0]['id'];ok('Rating saved natively',store(page)['ratings'][rk]['status']=='unknown');untouched(page)
    page.click('#reviewHideAll');ok('Hide all conceals answers',page.locator('.review-answer:visible').count()==0)
    page.select_option('#reviewStatus','hard');ok('Hard filter',page.locator('.review-item').count()==1)
    page.select_option('#reviewStatus','unrated');ok('Unrated filter',page.locator('.review-item').count()==len(items)-1)
    page.select_option('#reviewStatus','known');ok('Known filter',page.locator('.review-item').count()==0);page.select_option('#reviewStatus','all')
    page.click('[data-review-view=cards]');ok('Single card view',page.locator('.review-item').count()==1 and page.locator('#reviewPrev').is_disabled())
    for _ in range(4):page.click('#reviewNext')
    page.click('#reviewPrev');position=page.locator('.review-item').get_attribute('data-item');page.reload();page.wait_for_selector('#reviewWorkspace:visible')
    ok('Native refresh restores card position and ratings',page.locator('.review-item').get_attribute('data-item')==position and store(page)['ratings'][rk]['status']=='unknown')
    page.locator('[data-reveal]').click();page.locator('[data-rate=known]').click();ok('Card rating advances once',page.locator('.review-item').get_attribute('data-item')==items[4]['id'])
    for _ in range(3):page.locator('[data-reveal]').click()
    ok('Repeated reveal toggles consistently',page.locator('.review-answer:visible').count()==1)
    with page.expect_download() as dl:page.click('#reviewExport')
    export=json.loads(Path(dl.value.path()).read_text());ok('Export only review namespace',export['app']=='exam-reading-review' and export['version']==1 and all(k not in json.dumps(export) for k in OLD))
    older=copy.deepcopy(export);older['state']['ratings'][rk]={'status':'known','updatedAt':'2001-01-01T00:00:00Z'};upload(page,older)
    ok('Older import never overwrites newer self-rating',store(page)['ratings'][rk]['status']=='unknown')
    for bad in ['{broken',{'app':'word-card','version':2},{'app':'exam-reading-review','version':2,'state':export['state']}]:
        before=page.evaluate('(k)=>localStorage.getItem(k)',KEY);upload(page,bad);ok('Invalid import rejected without state mutation',page.evaluate('(k)=>localStorage.getItem(k)',KEY)==before and '导入失败' in page.locator('#reviewToast').inner_text())
    untouched(page)
    before=page.evaluate('(k)=>localStorage.getItem(k)',KEY);page.once('dialog',lambda d:d.dismiss());page.click('#reviewReset');ok('Cancelled reset preserves bytes',page.evaluate('(k)=>localStorage.getItem(k)',KEY)==before)
    page.once('dialog',lambda d:d.accept());page.click('#reviewReset');ok('Confirmed reset removes only review key',page.evaluate('(k)=>localStorage.getItem(k)',KEY) is None);untouched(page)
    upload(page,export);ok('Export/import round trip restores ratings',store(page)['ratings']==export['state']['ratings']);untouched(page)
    # Same context means real shared origin storage and genuine cross-tab storage events.
    peer=context.new_page();peer.on('pageerror',lambda e:errors.append(str(e)));peer.goto(BASE+'/review.html');peer.wait_for_selector('#reviewWorkspace:visible')
    expect(peer.locator('#reviewProgress')).to_have_text(f"本试卷已自评 {len(export['state']['ratings'])} / {len(items)} 项")
    page.once('dialog',lambda d:d.accept());page.click('#reviewReset');expect(peer.locator('#reviewProgress')).to_have_text(f'本试卷已自评 0 / {len(items)} 项')
    peer.click('#reviewTheme');ok('Cross-tab reset cannot revive old ratings on later save',store(peer)['ratings']=={} and store(page)['ratings']=={});untouched(peer);peer.close()
    upload(page,export);ok('Ratings restore after cross-tab reset test',store(page)['ratings']==export['state']['ratings']);untouched(page)
    # A second batch is injected only through the test browser; no fixture is committed.
    two=copy.deepcopy(data);two['id']='synthetic-second';two['title']='Synthetic isolation test'
    cats=copy.deepcopy(cat);extra=copy.deepcopy(entry);extra.update(id=two['id'],title=two['title'],file='data/review/synthetic-second.json');cats['sets'].append(extra)
    page.route('**/data/review/catalog.json',lambda r:r.fulfill(json=cats))
    page.route('**/data/review/synthetic-second.json',lambda r:r.fulfill(json=two))
    preserved=copy.deepcopy(store(page)['ratings']);page.reload();page.wait_for_selector('#reviewWorkspace:visible');page.select_option('#reviewDataset',two['id']);expect(page.locator('#reviewTitle')).to_have_text(two['title'])
    page.click('[data-review-view=list]');page.locator('[data-reveal]').first.click();open_details(page);page.locator('[data-rate=fuzzy]').first.click()
    ok('Second batch ratings isolated',all(store(page)['ratings'][k]==v for k,v in preserved.items()) and store(page)['ratings'][two['id']+'/'+items[0]['id']]['status']=='fuzzy')
    page.select_option('#reviewDataset',data['id']);expect(page.locator('#reviewTitle')).to_have_text(data['title']);untouched(page)
    page.click('[data-review-view=cards]')
    # Repeated next reaches the final card without wrapping or out-of-range positions.
    page.evaluate("()=>{for(let i=0;i<200;i++)document.getElementById('reviewNext').click()}")
    ok('Final card boundary stable',page.locator('#reviewNext').is_disabled() and page.locator('.review-item').get_attribute('data-item')==items[-1]['id'])
    page.evaluate("()=>{for(let i=0;i<200;i++)document.getElementById('reviewPrev').click()}")
    ok('First card boundary stable',page.locator('#reviewPrev').is_disabled() and page.locator('.review-item').get_attribute('data-item')==items[0]['id']);untouched(page)
    page.unroute('**/data/review/catalog.json');page.unroute('**/data/review/synthetic-second.json')
    for width in [320,390,600]:
        mobile=browser.new_context(viewport={'width':width,'height':844},is_mobile=True,has_touch=True)
        mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)));mp.goto(BASE+'/review.html');mp.wait_for_selector('#reviewWorkspace:visible')
        ok(f'{width}px concealed list no horizontal overflow',mp.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        before=raw_storage(mp);mp.click('#reviewShowAll');ok(f'{width}px whole page shows all meanings',mp.locator('.review-meaning:visible').count()==len(items));ok(f'{width}px retains English-left Chinese-right columns',columns_align(mp));ok(f'{width}px bilingual list no horizontal overflow',mp.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        mp.locator('#reviewColumns').scroll_into_view_if_needed();mp.screenshot(path=str(O/f'mobile-{width}-bilingual.png'))
        open_details(mp);ok(f'{width}px expanded source details no horizontal overflow',mp.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        mp.click('#reviewHideAll');ok(f'{width}px hide all also conceals source details',mp.locator('.review-answer:visible').count()==0);ok(f'{width}px visibility controls preserve storage bytes',raw_storage(mp)==before)
        mp.click('#reviewShowAll');mp.reload();mp.wait_for_selector('#reviewWorkspace:visible');ok(f'{width}px reload starts concealed',mp.locator('.review-answer:visible').count()==0)
        mp.click('[data-review-view=cards]');mp.click('#reviewShowAll');ok(f'{width}px optional card no horizontal overflow',mp.evaluate('document.documentElement.scrollWidth<=innerWidth'));mobile.close()
    bad=browser.new_page();bad.goto(BASE+'/');bad.evaluate('(k)=>localStorage.setItem(k,"{broken")',KEY);bad.goto(BASE+'/review.html');bad.wait_for_selector('#reviewWorkspace:visible');bad.click('#reviewTheme')
    ok('Corrupt storage disclosed and preserved','无法识别' in bad.locator('#reviewSave').inner_text() and bad.evaluate('(k)=>localStorage.getItem(k)',KEY)=='{broken')
    with bad.expect_download() as dl:bad.click('#reviewExport')
    ok('Protected raw data recoverable in export',json.loads(Path(dl.value.path()).read_text())['unrecognizedOriginal']=='{broken')
    upload(bad,export);expect(bad.locator('#reviewToast')).to_contain_text('当前会话');expect(bad.locator('#reviewToast')).to_contain_text('刷新会丢失')
    ok('Protected import warns about session-only data and preserves raw bytes',bad.evaluate('(k)=>localStorage.getItem(k)',KEY)=='{broken')
    bad.reload();bad.wait_for_selector('#reviewWorkspace:visible');expect(bad.locator('#reviewProgress')).to_have_text(f'本试卷已自评 0 / {len(items)} 项');ok('Protected import correctly does not claim persistence',bad.evaluate('(k)=>localStorage.getItem(k)',KEY)=='{broken')
    failure=browser.new_page();failure.route('**/data/review/catalog.json',lambda route:route.fulfill(status=503,body='unavailable'));failure.goto(BASE+'/review.html');failure.wait_for_selector('#reviewRetry:visible');ok('Fetch failure accurately disclosed','暂未加载成功' in failure.locator('#reviewLoadingMessage').inner_text())
    failure.unroute('**/data/review/catalog.json');failure.click('#reviewRetry');failure.wait_for_selector('#reviewWorkspace:visible');ok('Retry recovers real dataset',failure.locator('.review-item').count()==len(items))
    blocked=browser.new_context();blocked.add_init_script("Storage.prototype.setItem=function(){throw new Error('unavailable')}");bp=blocked.new_page();bp.goto(BASE+'/review.html');bp.wait_for_selector('#reviewWorkspace:visible');bp.locator('[data-reveal]').first.click();open_details(bp);bp.locator('[data-rate=unknown]').first.click();ok('Write failure disclosed but studying usable','不能保存' in bp.locator('#reviewSave').inner_text() and '已自评 1' in bp.locator('#reviewProgress').inner_text())
    legacy=browser.new_page();legacy.goto(BASE+'/#legacy');legacy.wait_for_selector('#workspace:visible');ok('Legacy hash opens unchanged app',legacy.locator('#legacy').get_attribute('open') is not None and legacy.locator('#word').inner_text()=='sympathy')
    legacy.goto(BASE+'/?deck=2012-e1-text2');legacy.wait_for_selector('#workspace:visible');expect(legacy.locator('#deckSelect')).to_have_value('2012-e1-text2');expect(legacy.locator('#deckTitle')).to_have_text('2012 · 英语一 · Text 2');ok('Legacy query loads requested non-default deck',legacy.locator('#legacy').get_attribute('open') is not None)
    legacy.goto(BASE+'/quick.html?deck=2012-e1-text1');legacy.wait_for_selector('#quickWorkspace:visible');expect(legacy.locator('#deckSelect')).to_have_value('2012-e1-text1');quick_data=json.loads((R/'data/decks/2012-e1-text1.json').read_text());expect(legacy.locator('#cardTerm')).to_have_text(quick_data['cards'][0]['term']);ok('Quick deep link loads requested non-default deck',legacy.locator('script[src*="quick.js"]').count()==1)
    check_real_batch_routes(browser, BASE, cat)
    check_desktop_pronunciation(browser, BASE, cat)
    ok('No runtime exceptions in primary review flow',not errors);browser.close()
finally:server.shutdown()
result={'mode':'Real localhost HTTP, Chromium native localStorage; real repository review JSON','checksPassed':len(checks),'checks':checks,'runtimeErrors':errors,'boundaries':['No live deployment test','320/390/600px emulation, not physical phone','Synthetic records only','Source/book factual verification is separate']}
(O/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
