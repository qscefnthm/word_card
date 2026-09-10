#!/usr/bin/env python3
"""Validate the static site and vocabulary without external dependencies."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$')
TEXT_FIELDS = ('term','form','kind','loc','quote','mark','meaning','translation','note','match','quoteType','readingSource')

def require(ok, message):
    if not ok:
        raise ValueError(message)

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script':
            require(bool(attrs.get('src')), 'Inline script is not allowed')
            self.resources.append(attrs['src'])
        if tag == 'link' and 'href' in attrs:
            self.resources.append(attrs['href'])

def main():
    catalog = load(ROOT / 'data/catalog.json')
    require(catalog.get('schemaVersion') == 1, 'Unsupported catalog schema')
    require(isinstance(catalog.get('version'), str), 'Catalog version missing')
    entries = catalog.get('decks', [])
    require(bool(entries), 'Empty catalog')
    require(len({d['id'] for d in entries}) == len(entries), 'Duplicate deck ID')
    require(catalog.get('defaultDeck') in {d['id'] for d in entries}, 'Invalid default deck')
    total = 0
    shared_terms = {}
    for entry in entries:
        require(bool(ID.fullmatch(entry['id'])), 'Invalid deck ID')
        require(bool(re.fullmatch(r'data/decks/[A-Za-z0-9_-]+\.json', entry['file'])), 'Unsafe deck path')
        deck = load(ROOT / entry['file'])
        require(deck.get('schemaVersion') == 1 and deck.get('id') == entry['id'], 'Deck schema or ID mismatch')
        require(deck.get('title') == entry['title'], 'Deck title mismatch')
        cards = deck['cards']
        require(len(cards) == entry['count'], 'Catalog count mismatch')
        ids = set()
        for card in cards:
            ident = card['id']
            require(bool(ID.fullmatch(ident)) and ident not in ('constructor','prototype','__proto__'), 'Invalid card ID')
            require(ident not in ids, 'Duplicate card in deck: ' + ident)
            ids.add(ident)
            require(all(isinstance(card.get(k), str) for k in TEXT_FIELDS), 'Missing string field: ' + ident)
            require(bool(card['term']) and bool(card['mark']) and card['mark'] in card['quote'], 'Invalid target highlight: ' + ident)
            require(isinstance(card.get('core'), bool) and isinstance(card.get('clue'), bool), 'Invalid flag: ' + ident)
            require(isinstance(card['book'], list), 'Invalid book references: ' + ident)
            for ref in card['book']:
                require(all(isinstance(ref.get(k), int) and ref[k] > 0 for k in ('number','page','englishPage')), 'Invalid reference index: ' + ident)
                require(isinstance(ref.get('word'), str) and isinstance(ref.get('definition'), str), 'Missing reference text: ' + ident)
            if ident in shared_terms:
                require(shared_terms[ident] == card['term'], 'A shared ID must identify the same term/sense: ' + ident)
            shared_terms[ident] = card['term']
        total += len(cards)
    parser = ResourceParser()
    parser.feed((ROOT / 'index.html').read_text(encoding='utf-8'))
    for path in parser.resources:
        require(path.startswith('./'), 'Resources must be local and project-relative: ' + path)
        require((ROOT / path.split('?')[0]).is_file(), 'Missing static resource: ' + path)
    require((ROOT / '.nojekyll').is_file(), 'Missing .nojekyll')
    require(not list(ROOT.rglob('*.pdf')), 'Do not publish the full vocabulary PDFs')
    print(f'PASS: {len(entries)} deck(s), {total} cards, local resources and references valid.')

if __name__ == '__main__':
    main()
