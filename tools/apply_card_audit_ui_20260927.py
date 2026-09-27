from pathlib import Path
R=Path(__file__).resolve().parents[1]
import hashlib
BASE={
 'quick.html':'7817b52c6020ecb154733d0a324b6b937127a851',
 'index.html':'2f2471700a2083d566530a215435bea4addb7ab0',
 'assets/app.js':'dc8f6bba9028d5dfe6acd2f6ebc0fd444ef8d9be',
 'assets/quick.js':'b9f0d811e48418c46e5e816d651c98e7b17e92fd',
 'assets/app.css':'4188c23afd7596a308cb5454ddf401acf9d033aa',
 'tools/generate_audio.py':'79dd332e00e6f00a1a8d19db0d9fdf6cb6ef1e91',
 'tools/validate.py':'b7c3f9bf0feca5e00887f09e1d76c781822e11b9',
 'AGENTS.md':'c07c6b15631333c1c4838cd966b2329ab0a060d1'
}
for path,expected in BASE.items():
 data=(R/path).read_bytes()
 actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 if actual!=expected:raise ValueError('Source changed since UI audit: '+path)

def swap(path,old,new):
 p=R/path;s=p.read_text();
 if old not in s:raise ValueError('Expected source block missing: '+path+' / '+old[:80])
 s=s.replace(old,new,1);p.write_text(s)

swap('quick.html','<div class="overview-meaning" id="cardMeaning"></div>', '''<div class="overview-meaning" id="cardMeaning"></div>
<div class="usage-pair" id="cardCollocationBlock" hidden>
<div class="overview-label">例句中的搭配 · 单独理解</div>
<p class="usage-en" id="cardCollocation" lang="en"></p>
<p class="usage-zh" id="cardCollocationMeaning"></p>
</div>''')
swap('quick.html','<div class="overview-label">真题语境</div>','<div class="overview-label" id="cardQuoteType">例句来源</div>')
swap('quick.html','./assets/quick.js?v=4','./assets/quick.js?v=20260927-audit')
swap('quick.html','./assets/quick.css?v=2','./assets/quick.css?v=20260927-audit')
swap('quick.html','./assets/app.css?v=3','./assets/app.css?v=20260927-audit')
swap('index.html','<div class="micro-label">真题语境 · 助手讲解</div><p class="meaning" id="meaning"></p>', '''<div class="micro-label">词条本义 · 语境讲解</div><p class="meaning" id="meaning"></p>
<div class="usage-pair" id="collocationBlock" hidden><div class="micro-label">例句中的搭配 · 单独理解</div><p class="usage-en" id="collocation" lang="en"></p><p class="usage-zh" id="collocationMeaning"></p></div>''')
swap('index.html','./assets/app.css?v=3','./assets/app.css?v=20260927-audit')
swap('index.html','./assets/app.js?v=3','./assets/app.js?v=20260927-audit')
swap('index.html','黄色高亮目标词；答案线索通过标签提示，不再给整句加红色波浪线。','黄色高亮目标词，不加红色波浪线。词条释义与搭配释义分开；完整真题原句和另写的补充例句明确标注来源，干扰选项不会当成文章事实。')
swap('assets/quick.js',"    $('cardMeaning').textContent = c.meaning;", """    $('cardMeaning').textContent = c.meaning;
    $('cardQuoteType').textContent = c.quoteType;
    $('cardCollocationBlock').hidden = !(c.collocation && c.collocationMeaning);
    $('cardCollocation').textContent = c.collocation || '';
    $('cardCollocationMeaning').textContent = c.collocationMeaning || '';""")
swap('assets/app.js',"    $('quoteType').textContent = c.quoteType + (c.clue ? ' · 已标注的答案线索' : '');", """    $('quoteType').textContent = c.quoteType;
    $('collocationBlock').hidden = !(c.collocation && c.collocationMeaning);
    $('collocation').textContent = c.collocation || '';
    $('collocationMeaning').textContent = c.collocationMeaning || '';""")
# Inline source labels on the quick list for meaning/phrase correspondence.
swap('assets/quick.js', "'<div class=\"quick-zh\">' + esc(c.meaning) + '</div>' +", """'<div class="quick-zh">' + esc(c.meaning) +
          (c.collocation && c.collocationMeaning ? '<div class="quick-usage"><span lang="en">' + esc(c.collocation) + '</span> — ' + esc(c.collocationMeaning) + '</div>' : '') + '</div>' +""")
for path in ('assets/app.js','assets/quick.js'):
 p=R/path;s=p.read_text();s=s.replace("return card.term.replace(/…/g", "return (card.spokenText || card.term).replace(/…/g")
 p.write_text(s)
css='''
/* Keep the headword meaning separate from the meaning of a longer phrase. */
.usage-pair{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:12px 14px;margin:0 0 20px;overflow-wrap:anywhere}
.usage-pair .usage-en{font:18px/1.55 Georgia,"Times New Roman",serif;color:var(--ink);margin:0 0 5px}
.usage-pair .usage-zh{font-size:13px;line-height:1.7;color:var(--muted);margin:0}
.usage-pair .micro-label,.usage-pair .overview-label{color:var(--dim)}
.quick-usage{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.6;overflow-wrap:anywhere}
.overview-quote,.overview-translation{overflow-wrap:anywhere;text-decoration:none}
'''
with (R/'assets/app.css').open('a') as f:f.write(css)
# Preserve all source identifiers. Record the exact spoken text beside each clip.
swap('tools/generate_audio.py','        audio = {}','        audio = {}\n        terms = {}\n        spoken_texts = {}')
swap('tools/generate_audio.py','            audio[card["id"]] = base64.b64encode(render_mp3(spoken_text(card["term"]))).decode("ascii")', '''            text = spoken_text(card.get("spokenText", card["term"]))
            terms[card["id"]] = card["term"]
            spoken_texts[card["id"]] = text
            audio[card["id"]] = base64.b64encode(render_mp3(text)).decode("ascii")''')
swap('tools/generate_audio.py','            "audio": audio,','            "audio": audio,\n            "terms": terms,\n            "spokenTexts": spoken_texts,')
# The validator required this static-site marker already, but it was absent.
(R/'.nojekyll').touch()

swap('tools/validate.py',"    parser = ResourceParser()\n    parser.feed((ROOT / 'index.html').read_text(encoding='utf-8'))", "    from check_card_content import check_content\n    check_content(ROOT)\n    parser = ResourceParser()\n    for filename in ('index.html', 'quick.html'):\n        parser.feed((ROOT / filename).read_text(encoding='utf-8'))")

with (R/'AGENTS.md').open('a',encoding='utf-8') as f:f.write("\n## Content audit guard (2026-09-27)\n\n- `meaning` describes the displayed `term`. Do not silently include a negation, comparison, subject or object found only in the example.\n- Keep the example's exact phrase in `collocation` and translate that phrase separately in `collocationMeaning`.\n- Every `quote` must be a complete example sentence, not a standalone option, headword or unfinished question stem.\n- Preserve negation, conditions, attribution and scope. Do not turn uncertainty or a rejected claim into an asserted fact by clipping its context.\n- `exampleType: original` uses `quoteType: 真题正文原句` only for a complete sentence checked against the supplied reading. Newly written examples use `exampleType: supplemental` and `quoteType: 补充例句（助手编写，非真题原句）`; they cannot be marked as original answer evidence.\n- Both card views must show example provenance and distinguish headword meaning from phrase meaning.\n- Preserve stable IDs and source-book records during repairs. Shared IDs must have agreeing headword meanings.\n- Regenerate pronunciation after any headword or `spokenText` change. Audio `terms` and `spokenTexts` must match the card.\n- Run `python3 tools/validate.py`, including `check_card_content.py`, plus syntax checks for both page scripts. Mechanical checks do not replace source/content review.\n")
