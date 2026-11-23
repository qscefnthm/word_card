#!/usr/bin/env python3
"""Build independently decodable MP3 clips packed by review set.

Requires piper-tts==1.3.0, ffmpeg with libmp3lame, and the model/config from
https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/ljspeech/medium
The US-English female voice was trained from scratch on the public-domain
LJ Speech Dataset. Pass the downloaded ONNX path and put its .json beside it.
"""
import argparse
import concurrent.futures
import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import onnxruntime as ort
from piper import PiperVoice
from piper.config import PiperConfig, SynthesisConfig

ROOT = Path(__file__).resolve().parents[1]
REVIEWS = ROOT / "data" / "review"
MODEL_SHA = "6f52a751e2349abe7a76735eb09dc1875298c77ea2342ffd2fef79ff81b87f22"
CONFIG_SHA = "141d612cc0a95ed7efc1ca936b845c2364967f2e9217c5dbfcf69fc4d6c65860"
CARD = "https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/medium/MODEL_CARD"
VOICE = None


def spoken_text(term):
    text = term.translate(str.maketrans({"’": "'", "“": "", "”": "", '"': ""}))
    text = re.sub(r"\s*(?:…|\.{3,}|/)\s*", ", ", text)
    text = re.sub(r"\b(DNT|GDP|CSR)\b", lambda m: " ".join(m[0]), text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,")


# Piper's phonemizer chooses the adjective "perfect" and noun "objects" in
# these isolated excerpts. Supply each whole phrase so stress is corrected
# without inserting a pause between the verb and the following words.
PHRASE_PHONEMES = {
    "perfect her craft": "pəfˈɛkt hɜː kɹˈaft",
    "objects to behavioural ads": "əbdʒˈɛkts tə bɪhˈeɪvjəɹəl ˈadz",
}

# Fixed pronunciations for these short excerpts were used in the initial recording.
WORD_PHONEMES = {
    "suspects": ("suspects", "sˈʌspɛkts"),
    "steep increase": ("increase", "ˈɪnkɹiːs"),
    "eligible to use": ("use", "jˈuːz"),
    "Protests have erupted": ("Protests", "pɹˈoʊtɛsts"),
    "lead to a decline": ("lead", "lˈiːd"),
}


def open_voice(model):
    global VOICE
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    opts.inter_op_num_threads = 1
    session = ort.InferenceSession(str(model), sess_options=opts, providers=["CPUExecutionProvider"])
    config = PiperConfig.from_dict(json.loads(Path(str(model) + ".json").read_text()))
    VOICE = PiperVoice(session=session, config=config)


def convert(raw, args):
    return subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", *args],
        input=raw, stdout=subprocess.PIPE, check=True,
    ).stdout


def render(text):
    phonetic_text = f"[[{PHRASE_PHONEMES[text]}]]" if text in PHRASE_PHONEMES else text
    if text in WORD_PHONEMES:
        word, phones = WORD_PHONEMES[text]
        phonetic_text = text.replace(word, "[[" + phones + "]]", 1)
    chunks = [c.audio_int16_bytes for c in VOICE.synthesize(
        phonetic_text, syn_config=SynthesisConfig(length_scale=1.05)
    )]
    if not chunks:
        raise ValueError(f"No speech generated for {text!r}")
    sample_rate = str(VOICE.config.sample_rate)
    pcm = (bytes(int(sample_rate) // 7 * 2)).join(chunks)
    mp3 = convert(pcm, [
        "-f", "s16le", "-ar", sample_rate, "-ac", "1", "-i", "pipe:0",
        "-c:a", "libmp3lame", "-b:a", "48k", "-threads", "1",
        "-write_xing", "0", "-map_metadata", "-1", "-f", "mp3", "pipe:1",
    ])
    # Decode the separate clip exactly as the browser receives it, and check
    # duration and energy. A non-empty MP3 can still be silence.
    decoded = convert(mp3, ["-f", "mp3", "-i", "pipe:0", "-f", "s16le", "pipe:1"])
    samples = np.frombuffer(decoded, dtype="<i2").astype(np.float32)
    if not len(pcm) <= len(decoded) <= len(pcm) + 9000 or np.sqrt(np.mean(samples**2)) < 100:
        raise ValueError(f"Silent or truncated MP3 for {text!r}")
    return mp3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    for path, wanted in [(args.model, MODEL_SHA), (Path(str(args.model)+".json"), CONFIG_SHA)]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != wanted:
            raise ValueError(f"Unexpected model or config: {path}")
    catalog = json.loads((REVIEWS / "catalog.json").read_text())
    out = REVIEWS / "audio"
    out.mkdir(exist_ok=True)
    cache = {}
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=args.workers, initializer=open_voice, initargs=(args.model,),
    ) as pool:
        for entry in catalog["sets"]:
            rows = json.loads((ROOT / entry["file"]).read_text())["items"]
            forms = [spoken_text(r["term"]) for r in rows]
            missing = list(dict.fromkeys(x for x in forms if x not in cache))
            for word, clip in zip(missing, pool.map(render, missing, chunksize=3)):
                cache[word] = clip
            buffer = bytearray()
            entries = {}
            for row, form in zip(rows, forms):
                clip = cache[form]
                entries[row["id"]] = dict(offset=len(buffer), length=len(clip),
                                           term=row["term"], spokenText=form)
                buffer.extend(clip)
            manifest = dict(version=1, dataset=entry["id"], codec="audio/mpeg",
                            bytes=len(buffer), sha256=hashlib.sha256(buffer).hexdigest(),
                            voice="Piper en_US-ljspeech-medium", modelCard=CARD, items=entries)
            (out / (entry["id"] + ".mp3")).write_bytes(buffer)
            (out / (entry["id"] + ".json")).write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
            )
            print(f'{entry["id"]}: {len(rows)} clips, {len(buffer)} bytes',flush=True)


if __name__ == "__main__":
    main()
