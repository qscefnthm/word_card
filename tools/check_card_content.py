#!/usr/bin/env python3
"""Content regression guard. Mechanical checks supplement, never replace, source review."""
import base64
import json
import re
from pathlib import Path


def spoken(card):
    text=card.get('spokenText',card['term']).replace('…',' something ').replace('’',"'")
    return re.sub(r'\s+',' ',re.sub(r'\s*/\s*',', ',text)).strip()


def check_content(root, require_audio=True):
    root=Path(root)
    catalog=json.loads((root/'data/catalog.json').read_text(encoding='utf-8'))
    count=0
    shared={}
    for entry in catalog['decks']:
        data=json.loads((root/entry['file']).read_text(encoding='utf-8'))
        audio=None
        if require_audio:
            audio=json.loads((root/'data/audio'/f"{entry['id']}.json").read_text(encoding='utf-8'))
            assert audio['deckId']==entry['id'] and audio['codec']=='audio/mpeg'
            assert set(audio['audio'])=={c['id'] for c in data['cards']}
        for c in data['cards']:
            label=entry['id']+'/'+c['id']
            assert c.get('exampleType') in ('original','supplemental'),label+': unlabelled provenance'
            expected='真题正文原句' if c['exampleType']=='original' else '补充例句（助手编写，非真题原句）'
            assert c['quoteType']==expected,label+': source label mismatch'
            assert c['mark'] in c['quote'],label+': missing target'
            assert c.get('collocation') and c['collocation'] in c['quote'],label+': invalid phrase'
            assert isinstance(c.get('collocationMeaning'),str) and c['collocationMeaning'].strip(),label+': missing phrase meaning'
            assert len(re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*",c['quote']))>=4,label+': example is only a word/fragment'
            assert re.search(r'[.!?][”\"\']?$',c['quote']),label+': missing sentence ending'
            assert re.search('[\u4e00-\u9fff]',c['translation']),label+': missing translation'
            assert not re.search(r'(?:\bhas|\bto|\bas|\bof)\s*[.]?$',c['quote'],re.I),label+': unfinished clause'
            if c['exampleType']=='supplemental':
                assert not c['clue'],label+': invented example cannot be marked exam evidence'
            signature=(c['term'],c['meaning'])
            if c['id'] in shared:
                assert shared[c['id']]==signature,label+': shared headword/meaning conflict'
            shared[c['id']]=signature
            if c['term']=='persuasive':
                assert c['meaning']=='有说服力的，令人信服的',label+': less leaked into word meaning'
            if c['term']=='certain':
                assert '远没有' not in c['meaning'],label+': far less leaked into word meaning'
            if c['term']=='fierce':
                assert not c['meaning'].startswith('更'),label+': comparative leaked into lemma'
            if audio:
                assert audio.get('terms',{}).get(c['id'])==c['term'],label+': stale audio headword'
                assert audio.get('spokenTexts',{}).get(c['id'])==spoken(c),label+': stale spoken text'
                raw=base64.b64decode(audio['audio'][c['id']],validate=True)
                assert len(raw)>128 and (raw.startswith(b'ID3') or raw[0]==255),label+': invalid MP3'
            count+=1
    print(f'PASS content: {len(catalog["decks"])} decks / {count} cards; examples, phrases, labels'+(' and audio metadata.' if require_audio else '.'))
    return count

if __name__=='__main__':check_content(Path(__file__).resolve().parents[1])
