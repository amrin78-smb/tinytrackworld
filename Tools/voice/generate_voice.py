"""Generate voice clips for Tiny Tracks World offline.

English: Kokoro TTS (Apache-2.0). Thai: VachanaTTS (MIT, VITS/Piper based).
Usage: generate_voice.py <voice_lines.json> <output_dir> <models_dir> [keys...]
Writes <output_dir>/<lang>/<key>.wav (16-bit mono): silence trimmed, soft fades,
peak-normalised, short lead-in so the first syllable is never clipped on Android.
"""
import json
import os
import sys
import tempfile

import numpy as np
import soundfile as sf

KOKORO_LANG = {"en": "en-us"}


def tidy(audio, sr):
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    thr = 0.01 * float(np.max(np.abs(audio)) or 1.0)
    idx = np.where(np.abs(audio) > thr)[0]
    if len(idx):
        a = max(0, idx[0] - int(0.03 * sr))
        b = min(len(audio), idx[-1] + int(0.12 * sr))
        audio = audio[a:b]
    fade = int(0.012 * sr)
    if len(audio) > 2 * fade:
        audio[:fade] *= np.linspace(0, 1, fade)
        audio[-fade:] *= np.linspace(1, 0, fade)
    peak = float(np.max(np.abs(audio)) or 1.0)
    audio = audio * (0.89 / peak)  # about -1 dBFS
    lead = np.zeros(int(0.06 * sr), dtype=np.float32)
    return np.concatenate([lead, audio])


class KokoroEngine:
    def __init__(self, models):
        from kokoro_onnx import Kokoro
        self.tts = Kokoro(os.path.join(models, "kokoro-v1.0.onnx"), os.path.join(models, "voices-v1.0.bin"))

    def speak(self, text, voice, speed, lang):
        return self.tts.create(text, voice=voice, speed=speed, lang=KOKORO_LANG.get(lang, lang))


class VachanaEngine:
    def __init__(self, models):
        # VachanaTTS downloads/caches voices in ./voices relative to the working directory.
        self.home = os.path.join(models, "vachana")
        os.makedirs(self.home, exist_ok=True)

    def speak(self, text, voice, speed, lang):
        from vachanatts import TTS
        cwd = os.getcwd()
        os.chdir(self.home)
        try:
            out = os.path.join(tempfile.mkdtemp(), "line.wav")
            TTS(text, voice=voice, output=out, speed=speed)
        finally:
            os.chdir(cwd)
        audio, sr = sf.read(out, dtype="float32")
        return audio, sr


ENGINES = {"kokoro": KokoroEngine, "vachana": VachanaEngine}


def main():
    lines_path, out_dir, models = (os.path.abspath(p) for p in sys.argv[1:4])
    only = set(sys.argv[4:])
    cfg = json.load(open(lines_path, encoding="utf-8"))
    engines = {}
    for lang in cfg["languages"]:
        engine_name, voice = cfg["voices"][lang].split(":", 1)
        if engine_name not in engines:
            engines[engine_name] = ENGINES[engine_name](models)
        engine = engines[engine_name]
        speed = float(cfg.get("speed", {}).get(lang, 0.9))
        os.makedirs(os.path.join(out_dir, lang), exist_ok=True)
        for line in cfg["lines"]:
            if only and line["key"] not in only:
                continue
            text = line.get(lang)
            if not text:
                continue
            audio, sr = engine.speak(text, voice, speed, lang)
            audio = tidy(audio, sr)
            path = os.path.join(out_dir, lang, line["key"] + ".wav")
            sf.write(path, audio, sr, subtype="PCM_16")
            print(f"{lang} {line['key']:<16} {len(audio) / sr:4.1f}s  {text}")


if __name__ == "__main__":
    main()
