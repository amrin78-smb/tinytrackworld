#!/usr/bin/env python3
"""Numeric sanity checker for the generated audio (we cannot listen, so we measure).

Usage:
    python3.13 Tools/audio/check_audio.py            # all WAVs under Assets/_Project/Audio
    python3.13 Tools/audio/check_audio.py moo baa    # only matching names
    python3.13 Tools/audio/check_audio.py -v moo     # verbose pitch/spectral track

Prints per file: duration, channels, peak dBFS, RMS dBFS, loudest-100ms dBFS,
DC offset, clipped samples, start/end levels (fades), and for *_loop files the
seam jump (|last-first| vs median |diff|) and a seam high-frequency ratio
(HF energy in a window straddling the seam vs. elsewhere; ~1 = no click).
The track shows, every ~80 ms: level, dominant spectral peak and a YIN f0.
"""
import glob
import os
import sys
import wave

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOOPS = {"crossing_bell"}  # loopable files without "loop" in the name
AUDIO = os.path.join(ROOT, "Assets", "_Project", "Audio")


def read(path):
    with wave.open(path, "rb") as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        assert w.getsampwidth() == 2
        x = np.frombuffer(w.readframes(n), "<i2").astype(float) / 32768.0
    return sr, x.reshape(-1, ch)


def dbfs(v):
    return 20 * np.log10(max(v, 1e-12))


def yin(frame, sr, fmin=60, fmax=1500, thr=0.15):
    n = len(frame) // 2
    x = frame - frame.mean()
    if np.sqrt(np.mean(x ** 2)) < 1e-4:
        return 0.0
    tmax = min(n, int(sr / fmin))
    tmin = int(sr / fmax)
    # YIN difference function d(tau) = sum_j (x[j] - x[j+tau])^2, j < W
    W = n
    xa = x[:W]
    xw = np.lib.stride_tricks.sliding_window_view(x, W)[:tmax + 1]
    d = np.sum((xw - xa[None, :]) ** 2, axis=1)
    cm = d[1:] * np.arange(1, tmax + 1) / np.maximum(np.cumsum(d[1:]), 1e-12)
    cm = np.concatenate([[1.0], cm])
    for tau in range(tmin, tmax):
        if cm[tau] < thr:
            while tau + 1 < tmax and cm[tau + 1] < cm[tau]:
                tau += 1
            # parabolic interpolation
            a, b, c = cm[tau - 1], cm[tau], cm[tau + 1]
            den = a - 2 * b + c
            off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
            return sr / (tau + off)
    return 0.0


def track(m, sr, hop_s=0.08, frame=2048):
    rows = []
    hop = int(hop_s * sr)
    win = np.hanning(frame)
    for s in range(0, max(1, len(m) - frame // 2), hop):
        fr = m[s:s + frame]
        if len(fr) < frame:
            fr = np.pad(fr, (0, frame - len(fr)))
        lv = dbfs(np.sqrt(np.mean(fr ** 2)))
        sp = np.abs(np.fft.rfft(fr * win))
        f = np.fft.rfftfreq(frame, 1 / sr)
        sp[f < 40] = 0
        dom = f[np.argmax(sp)] if lv > -60 else 0
        cen = float(np.sum(f * sp) / (np.sum(sp) + 1e-12)) if lv > -60 else 0
        f0 = yin(fr, sr) if lv > -45 else 0
        rows.append((s / sr, lv, dom, cen, f0))
    return rows


def seam(m, sr):
    d = np.abs(np.diff(m))
    med = np.median(d) + 1e-12
    jump = abs(m[-1] - m[0])
    w = 1024
    def hf(seg):
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
        f = np.fft.rfftfreq(len(seg), 1 / sr)
        return np.sum(sp[f > 6000]) / (np.sum(sp) + 1e-20)
    at = hf(np.concatenate([m[-w:], m[:w]]))
    # compare with the windows just after the start and just before the end;
    # a click at the seam would show up only in the straddling window
    ref = max(hf(m[:2 * w]), hf(m[-2 * w:])) + 1e-12
    # max diff near seam vs max diff elsewhere
    return jump, jump / med, at / ref, np.percentile(d, 99.9)


def summarize(path, verbose):
    sr, x = read(path)
    name = os.path.splitext(os.path.basename(path))[0]
    n, ch = x.shape
    m = x.mean(axis=1)
    peak = np.max(np.abs(x))
    r = np.sqrt(np.mean(x ** 2))
    w = int(0.1 * sr)
    if n > w:
        cs = np.concatenate([[0.0], np.cumsum(m ** 2)])
        st = (cs[w:] - cs[:-w]) / w  # moving 100 ms mean power
    else:
        st = np.array([np.mean(m ** 2) * n / w])
    clipped = int(np.sum(np.abs(x) >= 32766 / 32768))
    dc = float(np.max(np.abs(x.mean(axis=0))))
    line = (f"{name:18s} {n / sr:6.2f}s {ch}ch  peak {dbfs(peak):6.1f}  rms {dbfs(r):6.1f}  "
            f"st100 {dbfs(np.sqrt(st.max())):6.1f}  dc {dc:.1e}  clip {clipped}")
    issues = []
    if peak > 10 ** (-3 / 20) + 1e-9:
        issues.append("peak>-3dBFS")
    if dc > 1e-3:
        issues.append("DC")
    if clipped:
        issues.append("CLIP")
    if "loop" in name or name in LOOPS:
        jump, ratio, hfr, p999 = seam(m, sr)
        line += f"\n{'':18s} seam |jump| {jump:.4f} ({ratio:.1f}x median step, p99.9 step {p999:.4f})  seam HF ratio {hfr:.2f}"
        if jump > p999 or hfr > 3:
            issues.append("SEAM")
    else:
        a, b = np.abs(m[0]), np.abs(m[-1])
        line += f"   first/last |s| {a:.1e}/{b:.1e}"
        if max(a, b) > 1e-3:
            issues.append("no-fade")
    print(line + ("   !! " + ",".join(issues) if issues else "   ok"))
    if verbose or ("loop" not in name and n / sr < 3):
        rows = track(m, sr, 0.08 if n / sr < 3 else max(0.08, n / sr / 30))
        if verbose:
            print(f"    {'t':>5} {'lvl':>6} {'peakHz':>7} {'centHz':>7} {'f0':>6}")
            for t, lv, dom, cen, f0 in rows:
                print(f"    {t:5.2f} {lv:6.1f} {dom:7.0f} {cen:7.0f} {f0:6.0f}")
        else:
            f0s = " ".join(f"{int(round(f0))}" if f0 else "-" for *_, f0 in rows)
            doms = " ".join(f"{int(round(dom))}" if lv > -50 else "-" for _, lv, dom, _, _ in rows)
            print(f"    f0 : {f0s}\n    dom: {doms}")
    return issues


def main(argv):
    verbose = "-v" in argv
    names = [a for a in argv if not a.startswith("-")]
    files = sorted(glob.glob(os.path.join(AUDIO, "**", "*.wav"), recursive=True))
    if names:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0] in names]
    bad = 0
    for f in files:
        bad += bool(summarize(f, verbose))
    print(f"\n{len(files)} files, {bad} with issues")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
