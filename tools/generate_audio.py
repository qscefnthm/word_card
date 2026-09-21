#!/usr/bin/env python3
import base64
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.json"
OUT_DIR = ROOT / "data" / "audio"

def spoken_text(term: str) -> str:
    text = term.replace("…", " something ").replace("’", "'")
    text = re.sub(r"\s*/\s*", ", ", text)
    return re.sub(r"\s+", " ", text).strip()

def render_mp3(text: str) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        wav = td / "voice.wav"
        mp3 = td / "voice.mp3"
        subprocess.run(
            ["espeak", "-v", "en-us", "-s", "145", "-p", "45", "-a", "155", "-w", str(wav), text],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "ffmpeg", "-loglevel", "error", "-y", "-i", str(wav),
                "-ac", "1", "-ar", "22050", "-codec:a", "libmp3lame", "-b:a", "40k", str(mp3)
            ],
            check=True,
        )
        return mp3.read_bytes()

def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wanted = set()

    for entry in catalog["decks"]:
        deck_path = ROOT / entry["file"]
        deck = json.loads(deck_path.read_text(encoding="utf-8"))
        audio = {}
        for card in deck["cards"]:
            audio[card["id"]] = base64.b64encode(render_mp3(spoken_text(card["term"]))).decode("ascii")

        target = OUT_DIR / f'{deck["id"]}.json'
        wanted.add(target.name)
        payload = {
            "schemaVersion": 1,
            "deckId": deck["id"],
            "codec": "audio/mpeg",
            "generatedBy": "espeak en-us",
            "audio": audio,
        }
        target.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f'{deck["id"]}: {len(audio)} pronunciation clips')

    for old in OUT_DIR.glob("*.json"):
        if old.name not in wanted:
            old.unlink()

if __name__ == "__main__":
    main()
