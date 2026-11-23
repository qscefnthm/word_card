"""One-off Windows Edge check. Observe native utterances created by the site."""
import functools
import http.server
import json
import os
import pathlib
import threading

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


# Attach passive listeners and forward every call to the original browser method.
# Neither the voice list, playback, events, nor the site's click handlers are mocked.
OBSERVE = """
(() => {
  window.audioProbe = {calls: [], events: []};
  const nativeSpeak = SpeechSynthesis.prototype.speak;
  SpeechSynthesis.prototype.speak = function(utterance) {
    const index = window.audioProbe.calls.length;
    const voice = utterance.voice;
    window.audioProbe.calls.push({text: utterance.text, lang: utterance.lang,
      voice: voice && {name: voice.name, lang: voice.lang, local: voice.localService}});
    for (const type of ['start', 'end', 'error', 'boundary']) {
      utterance.addEventListener(type, (event) => {
        window.audioProbe.events.push({index, type, at: performance.now(),
          elapsed: event.elapsedTime, charIndex: event.charIndex,
          error: event.error || '', trusted: event.isTrusted});
      });
    }
    return nativeSpeak.call(this, utterance);
  };
})();
"""
VOICES = """() => ({
  agent: navigator.userAgent,
  english: speechSynthesis.getVoices().filter(v => /^en(?:[-_]|$)/i.test(v.lang))
    .map(v => ({name:v.name, lang:v.lang, local:v.localService, default:v.default})),
  total: speechSynthesis.getVoices().length
})"""
DONE = """() => audioProbe.events.some(e => e.type === 'end' && e.trusted &&
  audioProbe.events.some(s => s.type === 'start' && s.trusted && s.index === e.index))"""


def run():
    root = pathlib.Path.cwd()
    assert (root / 'review.html').exists(), 'Run in the checkout that contains review.html'
    handler = functools.partial(Handler, directory=str(root))
    with http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(channel='msedge', headless=False,
                                             ignore_default_args=['--mute-audio'])
                try:
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                    page.add_init_script(OBSERVE)
                    page.goto(f'http://127.0.0.1:{server.server_port}/review.html?set=2017-e1&scope=1')
                    btn = page.locator('[data-speak]').first
                    btn.wait_for()
                    page.evaluate('speechSynthesis.getVoices().length')
                    try:
                        page.wait_for_function('speechSynthesis.getVoices().length > 0', timeout=7000)
                    except PlaywrightTimeoutError:
                        pass
                    print('EDGE ' + json.dumps({'version':browser.version, **page.evaluate(VOICES)}), flush=True)
                    print('BUTTON ' + str(btn.get_attribute('aria-label')), flush=True)
                    raw = page.evaluate('JSON.stringify(localStorage)')
                    await_count = page.locator('.review-answer:visible').count()
                    btn.click()
                    try:
                        page.wait_for_function(DONE, timeout=22000)
                    except PlaywrightTimeoutError:
                        pass
                    record = page.evaluate('audioProbe')
                    record['states'] = page.evaluate('({pending:speechSynthesis.pending,speaking:speechSynthesis.speaking,paused:speechSynthesis.paused})')
                    record['visibleAnswersBefore'] = await_count
                    record['visibleAnswersAfter'] = page.locator('.review-answer:visible').count()
                    record['progressUnchanged'] = raw == page.evaluate('JSON.stringify(localStorage)')
                    print('SPEECH ' + json.dumps(record,ensure_ascii=True), flush=True)
                    if not record['calls']:
                        raise RuntimeError('Actual button did not call native speechSynthesis.speak')
                    if not page.evaluate(DONE):
                        raise RuntimeError('No trusted start/end pair from native Windows Edge speech service; see SPEECH log')
                    if record['visibleAnswersAfter'] != await_count or not record['progressUnchanged']:
                        raise RuntimeError('Pronunciation changed visibility or saved progress')
                finally:
                    browser.close()
        finally:
            server.shutdown()


if __name__ == '__main__':
    run()
