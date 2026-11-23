#!/usr/bin/env python3
"""Mechanical checks for the separate reading-review module; not source proofreading."""
import hashlib
import json
import re
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$')
FORBIDDEN = {'constructor', 'prototype', '__proto__'}
LEGACY_KEYS = ('word-card-site-v2', 'word-card-quick-v1', 'word-card-recall-v1', 'zhou-night-vocab-2010t4-v1')
def need(ok, message):
    if not ok: raise ValueError(message)
def ident(value): return isinstance(value, str) and ID.fullmatch(value) and value not in FORBIDDEN
def load(path): return json.loads(path.read_text(encoding='utf-8'))

class Resources(HTMLParser):
    def __init__(self): super().__init__(); self.paths=[]; self.ids=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'id' in a: self.ids.append(a['id'])
        if tag=='script':
            need(bool(a.get('src')), 'Inline scripts are not permitted')
            self.paths.append(a['src'])
        elif tag=='link' and 'href' in a: self.paths.append(a['href'])


def check_recordings(set_id, items):
    directory = ROOT / 'data/review/audio'
    index = load(directory / f'{set_id}.json')
    mp3 = (directory / f'{set_id}.mp3').read_bytes()
    need(index['version'] == 1 and index['dataset'] == set_id, f'{set_id}: audio index')
    need(index['codec'] == 'audio/mpeg' and index['bytes'] == len(mp3), f'{set_id}: audio format')
    need(index['sha256'] == hashlib.sha256(mp3).hexdigest(), f'{set_id}: audio checksum')
    tracks = index['items']
    need(set(tracks) == {item['id'] for item in items}, f'{set_id}: audio coverage')
    offset = 0
    for item in items:
        track = tracks[item['id']]
        need(track['term'] == item['term'] and track['spokenText'].strip(), f"{item['id']}: stale speech text")
        length = track['length']
        need(track['offset'] == offset and type(length) is int and length > 0, f"{item['id']}: invalid audio range")
        offset += length
    need(offset == len(mp3), f'{set_id}: audio length mismatch')


def main():
    cat=load(ROOT/'data/review/catalog.json')
    need(cat.get('schemaVersion')==1, 'Review catalog schema')
    need(isinstance(cat.get('version'),str), 'Missing version')
    sets=cat.get('sets',[])
    need(bool(sets), 'Empty review catalog')
    need(cat.get('defaultSet') in {s['id'] for s in sets}, 'Invalid default set')
    need(len({s['id'] for s in sets})==len(sets), 'Duplicate review set')
    total=0
    for entry in sets:
        need(ident(entry['id']), 'Invalid set ID')
        need(re.fullmatch(r'data/review/[A-Za-z0-9_-]+\.json',entry['file']), 'Unsafe data path')
        data=load(ROOT/entry['file'])
        need(data.get('schemaVersion')==1 and data.get('id')==entry['id'], 'Set schema / ID')
        need(data.get('title')==entry['title'], 'Set title mismatch')
        need(isinstance(data.get('version'),str), 'Missing set version')
        items=data.get('items',[])
        need(len(items)==entry['count'] and items, 'Count mismatch')
        ids=set(); references=0; kinds=Counter(); texts=Counter()
        for item in items:
            name=item.get('id')
            need(ident(name) and name not in ids, f'Invalid/duplicate ID {name}')
            ids.add(name)
            for field in ('term','context_meaning','loc'):
                need(isinstance(item.get(field),str) and item[field].strip(),f'{name}: missing {field}')
            need(item.get('kind') in ('highlight','supplement'), f'{name}: source kind')
            other = data.get('sections') == 'cloze-order-translation'
            need(type(item.get('text')) is int and 1<=item['text']<=(3 if other else 4), f'{name}: section number')
            location_pattern = r'选段 [A-G]' if other and item['text'] == 2 else r'[PQ]\d+(?:[–-]\d+)?(?:[A-D])?'
            need(re.fullmatch(location_pattern,item['loc']) is not None, f'{name}: source location')
            need(item.get('book_status') in ('verified','not_found'), f'{name}: unresolved book source')
            need(isinstance(item.get('book'),list), f'{name}: book array')
            need(bool(item['book']) or item['book_status']=='not_found', f'{name}: verified without references')
            lookup=item.get('book_lookup',{})
            need(isinstance(lookup,dict) and lookup.get('term_status') in ('exact_found','mapped','not_found'), f'{name}: unresolved lookup')
            if item['book_status']=='not_found':
                need(not item['book'] and lookup.get('term_status')=='not_found',f'{name}: inconsistent not_found')
            for book in item['book']:
                for field in ('entry_id','a4_page','english_page'):
                    need(type(book.get(field)) is int and book[field]>0,f'{name}: invalid book {field}')
                for field in ('headword','original_meaning','matched_part','mapping_note'):
                    need(isinstance(book.get(field),str) and book[field].strip(),f'{name}: missing book {field}')
                need(book.get('match_type') in ('exact','inflection','derivation','phrase_component'),f'{name}: match type')
                references+=1
            if item['kind']=='highlight':
                evidence=item.get('source_evidence',{})
                need(isinstance(evidence.get('highlight_parts'),list) and evidence['highlight_parts'],f'{name}: missing actual highlight parts')
            kinds[item['kind']]+=1;texts[item['text']]+=1
        if 'counts' in entry:
            need(entry['counts']==dict(kinds),'Catalog source counts mismatch')
        check_recordings(entry['id'], items)
        total+=len(items)
        print(f'PASS review set {entry["id"]}: {len(items)} items; {dict(kinds)}; Text counts {dict(texts)}; {references} verified reference links.')
    for file in ('review.html','index.html','quick.html'):
        parser=Resources();parser.feed((ROOT/file).read_text())
        need(len(parser.ids)==len(set(parser.ids)),f'{file}: duplicate DOM IDs')
        for resource in parser.paths:
            need(resource.startswith('./'),f'Nonlocal resource {resource}')
            need((ROOT/resource.split('?')[0]).is_file(),f'Missing resource {resource}')
    js=(ROOT/'assets/review.js').read_text()
    need("'exam-reading-review-v1'" in js,'Wrong review storage namespace')
    need('localStorage.clear' not in js,'Global storage deletion forbidden')
    need(not any(k in js for k in LEGACY_KEYS),'Review code must not access legacy keys')
    need(not list(ROOT.rglob('*.pdf')),'Do not publish source PDFs')
    need(not list((ROOT/'data/review').rglob('*.png')),'Do not publish private scans')
    print(f'PASS review module: {len(sets)} set(s), {total} entries, resources, source status and storage boundary.')

if __name__=='__main__': main()
