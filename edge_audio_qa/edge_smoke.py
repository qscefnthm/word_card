"""Observe a genuine Windows Edge click, native TTS or pre-recorded MP3 playback."""
import functools
import hashlib
import http.server
import json
import pathlib
import threading

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


# Forward the original methods untouched. Listeners observe genuine browser events.
# Keep raw URLs, audio bytes and native objects out of the JSON log.
OBSERVE = r"""
(() => {
  const probe = window.audioProbe = {calls: [], events: [], media: []};
  const blobs = new Map();
  const sources = new Map();
  const instances = new WeakMap();
  const create = URL.createObjectURL;
  URL.createObjectURL = function(blob) {
    const url = create.call(this, blob);
    if (blob instanceof Blob) blobs.set(url, blob);
    return url;
  };
  const nativeSpeak = SpeechSynthesis.prototype.speak;
  SpeechSynthesis.prototype.speak = function(utterance) {
    const index = probe.calls.length;
    const voice = utterance.voice;
    probe.calls.push({text: utterance.text, lang: utterance.lang, voice: voice &&
      {name: voice.name, lang: voice.lang, local: voice.localService}});
    for (const type of ['start', 'end', 'error', 'boundary']) {
      utterance.addEventListener(type, (event) => probe.events.push({
        index, type, at: performance.now(), elapsed: event.elapsedTime,
        charIndex: event.charIndex, error: event.error || '', trusted: event.isTrusted
      }));
    }
    return nativeSpeak.call(this, utterance);
  };

  const nativePlay = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function() {
    if (!instances.has(this)) {
      const audio = this, index = probe.media.length;
      instances.set(audio, index);
      const record = {events: [], tag: audio.tagName, sourceKind: '', mime: ''};
      probe.media.push(record);
      const capture = (event) => {
        const src = audio.currentSrc || audio.src;
        if (src) {
          const url = new URL(src, location.href);
          record.sourceKind = url.protocol === 'blob:' ? 'blob' :
            url.protocol === 'data:' ? 'data' : url.origin === location.origin ? 'same-origin' : 'external';
          if (record.sourceKind === 'same-origin') record.path = url.pathname;
          if (record.sourceKind === 'data') record.mime = src.slice(5, 80).split(/[;,]/)[0];
          if (blobs.has(src)) record.mime = blobs.get(src).type;
          sources.set(index, src);
        }
        if (event) record.events.push({
          type: event.type, at: performance.now(), position: audio.currentTime,
          duration: Number.isFinite(audio.duration) ? audio.duration : null,
          muted: audio.muted, volume: audio.volume, error: audio.error?.code,
          trusted: event.isTrusted
        });
      };
      capture();
      for (const type of ['loadedmetadata','playing','timeupdate','ended','error'])
        audio.addEventListener(type, capture);
    }
    return nativePlay.call(this);
  };
  window.finishedSpeech = () => probe.events.some(end => end.type === 'end' && end.trusted &&
    probe.events.some(start => start.type === 'start' && start.trusted && start.index === end.index));
  window.finishedAudio = () => probe.media.findIndex(record => {
    const events = record.events.filter(e => e.trusted);
    const start = events.find(e => e.type === 'playing' && !e.muted && e.volume > 0);
    return record.tag === 'AUDIO' && record.sourceKind !== 'external' && start &&
      events.some(e => e.type === 'timeupdate' && e.position > start.position + .04) &&
      events.some(e => e.type === 'ended' && e.duration > .12 && e.at >= start.at);
  });
  window.inspectRecording = async index => {
    const src = sources.get(index), record = probe.media[index];
    let blob = blobs.get(src);
    if (!blob) {
      if (record.sourceKind === 'data') {
        const comma = src.indexOf(',');
        if (!/;base64,/i.test(src.slice(0, comma + 1))) throw Error('Unexpected data encoding');
        const bytes = Uint8Array.from(atob(src.slice(comma + 1)), c => c.charCodeAt(0));
        blob = new Blob([bytes], {type: record.mime});
      } else {
        if (record.sourceKind !== 'same-origin') throw Error('Unknown source for decoded recording');
        const response = await fetch(src);
        if (!response.ok) throw Error('Could not fetch recording: '+response.status);
        blob = await response.blob();
      }
    }
    const mime = blob.type || record.mime;
    const bytes = await blob.arrayBuffer();
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const sha256 = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
    const sample = new Uint8Array(bytes, 0, Math.min(bytes.byteLength, 8));
    const mp3 = (sample[0] === 0x49 && sample[1] === 0x44 && sample[2] === 0x33) ||
      (sample[0] === 0xff && (sample[1] & 0xe0) === 0xe0 && (sample[1] & 0x06) === 0x02);
    if (!mp3) throw Error('Recording does not have an MP3/ID3 header');
    const decoder = new OfflineAudioContext(1, 1, 24000);
    const pcm = await decoder.decodeAudioData(bytes);
    const channel = pcm.getChannelData(0);
    let peak = 0, energy = 0;
    for (const value of channel) {
      peak = Math.max(peak, Math.abs(value));
      energy += value * value;
    }
    return {mime, type:'MP3', sha256, duration:pcm.duration, channels:pcm.numberOfChannels,
      bytes:blob.size, sampleRate:pcm.sampleRate, peak, rms:Math.sqrt(energy / channel.length)};
  };
})();
"""
VOICES = r"""() => ({
  agent: navigator.userAgent,
  english: speechSynthesis.getVoices().filter(v => /^en(?:[-_]|$)/i.test(v.lang))
    .map(v => ({name:v.name, lang:v.lang, local:v.localService, default:v.default})),
  total: speechSynthesis.getVoices().length
})"""
DONE = "() => finishedSpeech() || finishedAudio() >= 0"


def check_item(browser, base, batch):
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    try:
        page.add_init_script(OBSERVE)
        page.goto(f'{base}/review.html?set={batch}')
        button = page.locator('[data-speak]').first
        button.wait_for()
        try:
            page.wait_for_function('speechSynthesis.getVoices().length > 0', timeout=4000)
        except PlaywrightTimeoutError:
            pass
        row = button.locator('xpath=ancestor::article')
        term = row.locator('.review-term').inner_text()
        print('EDGE ' + json.dumps({'version': browser.version, **page.evaluate(VOICES)}), flush=True)
        raw = page.evaluate('JSON.stringify(localStorage)')
        count = page.locator('.review-answer:visible').count()
        button.click()
        try:
            page.wait_for_function(DONE, timeout=33000)
        except PlaywrightTimeoutError:
            pass
        record = page.evaluate('audioProbe')
        native = page.evaluate('finishedSpeech()')
        index = page.evaluate('finishedAudio()')
        record.update(term=term, batch=batch, nativeCompleted=native,
                      fallbackCompleted=index >= 0, visibleAnswersBefore=count,
                      visibleAnswersAfter=page.locator('.review-answer:visible').count(),
                      progressUnchanged=raw == page.evaluate('JSON.stringify(localStorage)'))
        print('PLAYBACK ' + json.dumps(record, ensure_ascii=True), flush=True)
        assert record['calls'] and record['calls'][0]['text'] == term, 'Wrong or absent initial native utterance'
        assert index >= 0 or native, 'No trusted completed pronunciation, see PLAYBACK events'
        if index >= 0:
            audio = page.evaluate('index => inspectRecording(index)', index)
            print('DECODED_MP3 ' + json.dumps(audio), flush=True)
            directory = pathlib.Path('data/review/audio')
            manifest = json.loads((directory / (batch + '.json')).read_text(encoding='utf-8'))
            item = manifest['items'][button.get_attribute('data-speak')]
            assert item['term'] == term
            with (directory / (batch + '.mp3')).open('rb') as source:
                source.seek(item['offset'])
                intended = source.read(item['length'])
            assert hashlib.sha256(intended).hexdigest() == audio['sha256'], 'Actually played the wrong clip'
            assert audio['duration'] > .12 and audio['peak'] > .015 and audio['rms'] > .001, 'Decoded audio is silent'
        assert record['visibleAnswersAfter'] == count and record['progressUnchanged']
    finally:
        page.close()


def run():
    root = pathlib.Path.cwd()
    assert (root / 'review.html').exists()
    handler = functools.partial(Handler, directory=str(root))
    with http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(channel='msedge', headless=False,
                                             ignore_default_args=['--mute-audio'])
                try:
                    for batch in ('2017-e1', '2015-e1'):
                        check_item(browser, f'http://127.0.0.1:{server.server_port}', batch)
                finally:
                    browser.close()
        finally:
            server.shutdown()


if __name__ == '__main__':
    run()
