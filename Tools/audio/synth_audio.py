#!/usr/bin/env python3
"""Procedural audio generator for Tiny Tracks World.

Every sound is synthesised from scratch with numpy (no samples, no network).
Deterministic: each sound uses its own seed derived from its name.

Usage (needs numpy; Blender's bundled Python works):
    python3.13 Tools/audio/synth_audio.py            # all sounds
    python3.13 Tools/audio/synth_audio.py moo bell   # only the named ones
    python3.13 Tools/audio/synth_audio.py --list

Loops are built *circularly* (every event/tail is wrapped modulo the loop
length and continuous noise is filtered in the FFT domain over exactly one
loop period) so the seam is mathematically continuous - no crossfade needed.
"""
import os
import sys
import wave
import zlib

import numpy as np

SR = 44100
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = {
    "SFX": os.path.join(ROOT, "Assets", "_Project", "Audio", "SFX"),
    "Ambient": os.path.join(ROOT, "Assets", "_Project", "Audio", "Ambient"),
    "Music": os.path.join(ROOT, "Assets", "_Project", "Audio", "Music"),
}


# ----------------------------------------------------------------------------
# basic helpers
# ----------------------------------------------------------------------------
def rng_for(name):
    return np.random.default_rng(20240611 + zlib.crc32(name.encode()))


def tvec(dur):
    return np.arange(int(round(dur * SR))) / SR


def db(x):
    return 10 ** (x / 20.0)


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)) + 1e-20))


def norm_rms(x):
    return x / rms(x)


def curve(keys, n, smooth_ms=0.0):
    """Piecewise-linear curve from [(time_s, value), ...] sampled at n samples."""
    ts = np.array([k[0] for k in keys], float)
    vs = np.array([k[1] for k in keys], float)
    y = np.interp(np.arange(n) / SR, ts, vs)
    if smooth_ms > 0:
        y = smooth(y, smooth_ms)
    return y


def smooth(y, ms):
    w = max(1, int(SR * ms / 1000.0))
    if w < 2:
        return y
    k = np.hanning(w + 2)[1:-1]
    k /= k.sum()
    yp = np.concatenate([np.full(w, y[0]), y, np.full(w, y[-1])])
    return np.convolve(yp, k, mode="same")[w:-w]


def fft_filter(x, H_fn, circular=False):
    """Zero-phase filter by magnitude response H_fn(freqs). circular=True keeps
    a loop periodic; otherwise the signal is zero-padded (no wrap-around)."""
    n = len(x)
    N = n if circular else int(2 ** np.ceil(np.log2(n + SR // 2)))
    X = np.fft.rfft(x, N)
    f = np.fft.rfftfreq(N, 1.0 / SR)
    y = np.fft.irfft(X * H_fn(f), N)
    return y[:n]


def lp(fc, order=2):
    return lambda f: 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))


def hp(fc, order=2):
    return lambda f: 1.0 / np.sqrt(1.0 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def bp(fc, q):
    """Resonant band-pass magnitude (2nd order), peak gain 1."""
    def H(f):
        f = np.maximum(f, 1e-3)
        return 1.0 / np.sqrt(1.0 + q * q * (f / fc - fc / f) ** 2)
    return H


def chain(*Hs):
    def H(f):
        r = np.ones_like(f)
        for h in Hs:
            r = r * h(f)
        return r
    return H


def env_ad(n, attack, decay_t60, hold=0.0):
    """Attack (linear-ish sine) then exponential decay with given T60 (s)."""
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    a = np.sin(a * np.pi / 2) ** 2
    d = np.where(t < attack + hold, 1.0,
                 10 ** (-3 * (t - attack - hold) / max(decay_t60, 1e-4)))
    return a * d


def place(buf, sig, start_s, gain=1.0, wrap=False):
    """Add sig into buf at start_s. wrap=True folds overflow to the start."""
    s = int(round(start_s * SR))
    L = buf.shape[0]
    sig = sig * gain
    if wrap:
        s %= L
        pos = 0
        while pos < len(sig):
            take = min(len(sig) - pos, L - s)
            buf[s:s + take] += sig[pos:pos + take]
            pos += take
            s = 0
    else:
        e = min(L, s + len(sig))
        if e > s:
            buf[s:e] += sig[:e - s]
    return buf


def pan(x, p):
    """Constant-power pan, p in [-1, 1]. Returns (n, 2)."""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def modal(freqs, amps, t60s, dur, phase_rng=None):
    """Sum of exponentially decaying sinusoids (modal synthesis)."""
    t = tvec(dur)
    y = np.zeros_like(t)
    for i, (f, a, d) in enumerate(zip(freqs, amps, t60s)):
        ph = 0.0 if phase_rng is None else phase_rng.uniform(0, 2 * np.pi)
        y += a * np.sin(2 * np.pi * f * t + ph) * 10 ** (-3 * t / d)
    return y


def tv_noise(n, mag_fn, rng, frame=1024):
    """Time-varying filtered noise. mag_fn(times[frames,1], freqs[1,bins]) ->
    magnitude (frames, bins). Overlap-add of random-phase frames."""
    hop = frame // 2
    nfr = n // hop + 3
    times = ((np.arange(nfr) * hop - hop) + frame / 2) / SR
    freqs = np.fft.rfftfreq(frame, 1.0 / SR)
    M = mag_fn(times[:, None], freqs[None, :])
    ph = rng.standard_normal(M.shape) + 1j * rng.standard_normal(M.shape)
    frames = np.fft.irfft(M * ph, frame, axis=1)
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(frame) / frame)  # periodic
    out = np.zeros(nfr * hop + frame)
    for i in range(nfr):
        out[i * hop:i * hop + frame] += frames[i] * win
    return out[hop:hop + n]


def periodic_noise(n, H_fn, rng):
    """Noise that loops perfectly over n samples (filtered in FFT domain)."""
    return fft_filter(rng.standard_normal(n), H_fn, circular=True)


def formant_mag(f, formants):
    """Cascade of 2-pole resonators: |H| = prod F^2/sqrt((F^2-f^2)^2+(B f)^2)."""
    H = 1.0
    for F, B in formants:
        H = H * (F * F) / np.sqrt((F * F - f * f) ** 2 + (B * f) ** 2)
    return H


def voice(f0, formants, amp, tilt=1.0, breath=0.0, jitter=0.0, shimmer=0.0,
          fmax=7500.0, rng=None, breath_hp=0.0):
    """Source-filter voice by additive synthesis.
    f0: per-sample pitch (Hz). formants: list of (F_array, B_array) per sample.
    Harmonic k gets amplitude k^-tilt * |H(k f0)|, i.e. a glottal-like source
    shaped by a time-varying formant filter. Breath noise uses the same
    formants (sampled per frame)."""
    n = len(f0)
    if jitter > 0:
        jn = smooth(rng.standard_normal(n), 6.0)
        jn /= np.max(np.abs(jn)) + 1e-9
        f0 = f0 * (1 + jitter * jn)
    phase = 2 * np.pi * np.cumsum(f0) / SR
    y = np.zeros(n)
    K = int(fmax / max(np.min(f0), 30))
    for k in range(1, K + 1):
        fk = k * f0
        taper = np.clip((fmax - fk) / (0.15 * fmax), 0, 1)
        if not np.any(taper > 0):
            break
        H = formant_mag(fk, formants)
        y += (k ** -tilt) * H * taper * np.sin(k * phase)
    if shimmer > 0:
        sn = smooth(rng.standard_normal(n), 10.0)
        sn /= np.max(np.abs(sn)) + 1e-9
        y *= 1 + shimmer * sn
    y = norm_rms(y)
    if breath > 0:
        fr_idx = lambda tt: np.clip((tt * SR).astype(int), 0, n - 1)
        def mag(tt, ff):
            idx = fr_idx(tt)
            fm = [(F[idx], B[idx]) for F, B in formants]
            m = formant_mag(ff, fm) * lp(6000)(ff)
            if breath_hp > 0:
                m = m * hp(breath_hp)(ff)
            return m
        nz = norm_rms(tv_noise(n, mag, rng))
        y = y + breath * nz
    return y * amp


def vowel(name, n, scale=1.0):
    """Static formant set (F,B) for a vowel, scaled (small animal -> >1)."""
    table = {
        "i": [(300, 60), (2300, 120), (3000, 200)],
        "e": [(500, 70), (1900, 110), (2600, 200)],
        "a": [(800, 90), (1250, 110), (2600, 200)],
        "o": [(500, 80), (900, 100), (2500, 200)],
        "u": [(330, 70), (750, 90), (2400, 200)],
        "m": [(260, 60), (1100, 400), (2400, 600)],
    }
    return [(np.full(n, F * scale), np.full(n, B * scale)) for F, B in table[name]]


def morph(keys, n, smooth_ms=25.0, scale=1.0):
    """Formant trajectories through vowel keyframes [(t, vowel), ...]."""
    base = {k: vowel(k, 1, scale) for k in "ieaoum"}
    out = []
    for i in range(3):
        Fk = [(t, base[v][i][0][0]) for t, v in keys]
        Bk = [(t, base[v][i][1][0]) for t, v in keys]
        out.append((curve(Fk, n, smooth_ms), curve(Bk, n, smooth_ms)))
    return out


def tone(freq, dur, harm=(1.0,), attack=0.005, t60=1.0, vib=(0, 0), rng=None):
    """Simple harmonic tone with decay envelope. freq may be array."""
    n = int(round(dur * SR))
    f = np.full(n, freq, float) if np.isscalar(freq) else freq
    if vib[0] > 0:
        f = f * (1 + vib[1] * np.sin(2 * np.pi * vib[0] * np.arange(n) / SR))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = sum(a * np.sin((k + 1) * ph) for k, a in enumerate(harm))
    return y * env_ad(n, attack, t60)


def sparkle(rng, notes=(1568, 2093, 2637), gap=0.035, dur=0.5, t60=0.35):
    """Tiny glockenspiel-ish arpeggio of pure tones (soft, not harsh)."""
    buf = np.zeros(int(dur * SR))
    for i, f in enumerate(notes):
        s = modal([f, f * 2.76], [1.0, 0.12], [t60, t60 * 0.3], dur - i * gap)
        s *= env_ad(len(s), 0.002, 10.0)
        place(buf, s, i * gap, 0.8 ** i)
    return buf


# ----------------------------------------------------------------------------
# SFX
# ----------------------------------------------------------------------------
def s_whistle(rng):
    dur = 1.25
    n = int(dur * SR)
    t = np.arange(n) / SR
    # two blasts: short toot then a longer toot (soft attack, pitch scoop)
    gate = (curve([(0, 0), (0.06, 1), (0.30, 1), (0.36, 0.15), (0.42, 0.15),
                   (0.50, 1), (1.05, 1), (1.22, 0), (dur, 0)], n, 15))
    scoop = curve([(0, 0.95), (0.08, 1.0), (0.36, 0.985), (0.42, 0.95),
                   (0.52, 1.0), (1.22, 0.985), (dur, 0.98)], n, 20)
    chord = [440.0, 554.37, 659.26]  # A major triad, mellow register
    y = np.zeros(n)
    for i, f0 in enumerate(chord):
        f = f0 * scoop * (1 + 0.003 * np.sin(2 * np.pi * (5.1 + i) * t))
        ph = 2 * np.pi * np.cumsum(f) / SR
        tonal = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
        # breathy noise resonating at the pipe pitch
        nz = fft_filter(rng.standard_normal(n), bp(f0, 6.0))
        y += norm_rms(tonal) * 0.8 + norm_rms(nz) * 0.45
    hiss = fft_filter(rng.standard_normal(n), chain(hp(1500), lp(4000)))
    y = y / 3 + 0.12 * norm_rms(hiss)
    y = fft_filter(y, lp(3200))
    return y * gate


def s_bell(rng):
    dur = 1.5
    n = int(dur * SR)
    buf = np.zeros(n)
    f0 = 880.0
    ratios = [1.0, 2.32, 4.25, 6.63]
    amps = [1.0, 0.45, 0.18, 0.06]
    t60s = [0.9, 0.5, 0.25, 0.12]
    for i, st in enumerate([0.0, 0.32, 0.64]):
        d = dur - st
        s = modal([f0 * r * (1 + 0.0008 * i) for r in ratios], amps, t60s, d, rng)
        click = fft_filter(rng.standard_normal(len(s)), bp(3000, 1.0)) * env_ad(len(s), 0.0005, 0.01)
        s = s * env_ad(len(s), 0.002, 50) + 0.15 * click / (np.max(np.abs(click)) + 1e-9)
        place(buf, s, st, [1.0, 0.85, 0.9][i])
    return fft_filter(buf, lp(5000))


def chuff(rng, n, strength=1.0):
    nz = fft_filter(rng.standard_normal(n), chain(bp(700, 0.8), lp(1800)))
    body = fft_filter(rng.standard_normal(n), lp(250))
    s = 0.8 * norm_rms(nz) + 0.6 * norm_rms(body)
    e = env_ad(n, 0.012, 0.28)
    return s * e * strength


def s_chug_loop(rng):
    L = int(1.0 * SR)
    buf = np.zeros(L)
    for i, g in enumerate([1.0, 0.72, 0.9, 0.68]):
        place(buf, chuff(rng, int(0.4 * SR), g), i * 0.25, wrap=True)
    hiss = periodic_noise(L, chain(bp(900, 0.7), lp(2500)), rng)
    buf = buf + 0.06 * norm_rms(hiss) * rms(buf)
    return buf


def wood_click(rng, base=900.0, dur=0.12, bright=1.0):
    s = modal([base, base * 1.93, base * 3.1, base * 4.6], [1.0, 0.5, 0.25 * bright, 0.1 * bright],
              [0.05, 0.035, 0.02, 0.012], dur, rng)
    nz = rng.standard_normal(len(s)) * env_ad(len(s), 0.0003, 0.006)
    nz = fft_filter(nz, chain(bp(base * 2, 1.0), lp(5000)))
    return (s + 0.6 * nz / (np.max(np.abs(nz)) + 1e-9)) * env_ad(len(s), 0.0008, 100)


def s_rolling_loop(rng):
    L = int(2.0 * SR)
    buf = np.zeros(L)
    # clickety-clack: wheel pairs over two track joints per loop
    for st, g, b in [(0.06, 1.0, 700), (0.17, 0.8, 640), (1.06, 0.95, 720), (1.17, 0.75, 660),
                     (0.56, 0.25, 820), (1.56, 0.22, 800)]:
        place(buf, wood_click(rng, b, 0.15), st, g, wrap=True)
    click_rms = rms(buf)
    t = np.arange(L) / SR
    rumble = periodic_noise(L, chain(lp(220, 2), hp(40)), rng)
    rumble = norm_rms(rumble) * (1 + 0.25 * np.sin(2 * np.pi * 6.0 * t))  # 12 cycles/loop
    grain = norm_rms(periodic_noise(L, chain(bp(1200, 0.6), lp(3000)), rng))
    return buf + click_rms * (1.6 * rumble + 0.12 * grain)


def s_motor_loop(rng):
    L = int(1.5 * SR)
    t = np.arange(L) / SR
    f0 = 80.0  # 120 cycles per loop -> periodic
    wob = 1 + 0.15 * np.sin(2 * np.pi * 4.0 * t)  # 6 cycles per loop
    hum = sum(a * np.sin(2 * np.pi * f0 * k * t) for k, a in
              [(1, 1.0), (2, 0.55), (3, 0.3), (4, 0.15), (6, 0.06)])
    whine = 0.06 * np.sin(2 * np.pi * 320.0 * t) * (1 + 0.3 * np.sin(2 * np.pi * 2.0 * t))
    nz = norm_rms(periodic_noise(L, chain(bp(300, 0.7), lp(1200)), rng))
    y = norm_rms(hum) * wob + whine * 4 + 0.18 * nz
    return fft_filter(y, lp(1500), circular=True)


def s_track_place(rng):
    dur = 0.45
    s = modal([170, 395, 690, 1120, 1650], [1.0, 0.7, 0.45, 0.2, 0.08],
              [0.18, 0.12, 0.08, 0.05, 0.03], dur, rng)
    thump = fft_filter(rng.standard_normal(len(s)), lp(300)) * env_ad(len(s), 0.001, 0.05)
    tap = fft_filter(rng.standard_normal(len(s)), chain(bp(1500, 0.8), lp(4000))) * env_ad(len(s), 0.0005, 0.015)
    y = s * env_ad(len(s), 0.001, 100) + 0.5 * thump / np.max(np.abs(thump)) + 0.3 * tap / np.max(np.abs(tap))
    return y


def s_track_snap(rng):
    dur = 0.6
    buf = np.zeros(int(dur * SR))
    place(buf, wood_click(rng, 1300, 0.1, 0.6), 0.0, 1.0)
    place(buf, wood_click(rng, 1150, 0.1, 0.6), 0.022, 0.6)
    place(buf, sparkle(rng, (1568, 2093, 2637), 0.04, 0.5, 0.3), 0.05, 0.35)
    return fft_filter(buf, lp(6000))


def s_track_remove(rng):
    dur = 0.45
    n = int(dur * SR)
    pop_f = curve([(0, 260), (0.06, 520), (dur, 560)], n)
    pop = np.sin(2 * np.pi * np.cumsum(pop_f) / SR) * env_ad(n, 0.004, 0.12)
    sweep = curve([(0, 500), (0.35, 1800), (dur, 1800)], n)
    whoosh = tv_noise(n, lambda tt, ff: bp(1.0, 1.0)(ff / np.interp(tt, np.arange(n) / SR, sweep)) * lp(3500)(ff), rng)
    we = curve([(0, 0), (0.08, 1), (0.25, 0.6), (0.4, 0), (dur, 0)], n, 10)
    wood = wood_click(rng, 500, 0.1, 0.3)
    buf = 0.8 * pop + 0.5 * norm_rms(whoosh) * we * 0.4
    place(buf, wood, 0.0, 0.5)
    return buf


def s_invalid(rng):
    dur = 0.5
    buf = np.zeros(int(dur * SR))
    for st, f1, f2 in [(0.0, 349.2, 340), (0.17, 293.7, 270)]:
        n = int(0.3 * SR)
        f = curve([(0, f1), (0.3, f2)], n)
        s = tone(f, 0.3, harm=(1.0, 0.18, 0.05), attack=0.012, t60=0.45)
        s *= curve([(0, 1), (0.2, 1), (0.3, 0)], n, 10)
        place(buf, s, st)
    return fft_filter(buf, lp(2500))


def s_button(rng):
    dur = 0.16
    n = int(dur * SR)
    f = curve([(0, 380), (0.035, 900), (dur, 980)], n, 3)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.002, 0.11)
    return s + 0.1 * np.sin(2 * 2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.002, 0.05)


def s_button_toggle(rng):
    dur = 0.24
    buf = np.zeros(int(dur * SR))
    for st, fr in [(0.0, 660.0), (0.085, 990.0)]:
        s = tone(fr, 0.14, harm=(1.0, 0.12), attack=0.003, t60=0.12)
        place(buf, s, st)
    return buf


def s_undo(rng):
    dur = 0.5
    n = int(dur * SR)
    t = np.arange(n) / SR
    # reversed whoosh: swell up, filter sweeping down, then a quick release
    sweep = curve([(0, 2600), (0.42, 700), (dur, 650)], n)
    nz = tv_noise(n, lambda tt, ff: bp(1.0, 1.2)(ff / np.interp(tt, t, sweep)) * lp(4000)(ff), rng)
    e = curve([(0, 0), (0.38, 1), (0.44, 0.3), (0.5, 0)], n, 8) ** 1.5
    f = curve([(0, 700), (0.45, 420), (dur, 400)], n)
    tn = np.sin(2 * np.pi * np.cumsum(f) / SR) * curve([(0, 0), (0.3, 0.5), (0.42, 0.6), (0.5, 0)], n, 10)
    return norm_rms(nz) * e * 0.5 + 0.5 * tn


def s_place_decor(rng):
    dur = 0.7
    n = int(dur * SR)
    buf = np.zeros(n)
    m = int(0.18 * SR)
    f = curve([(0, 300), (0.06, 620), (0.18, 640)], m, 4)
    bloop = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(m, 0.004, 0.14)
    place(buf, bloop, 0.0, 1.0)
    place(buf, sparkle(rng, (1318.5, 1760, 2093, 2637), 0.045, 0.6, 0.32), 0.07, 0.35)
    return buf


def vib_tone(f, dur, t60):
    """Soft vibraphone-like tone: partials 1 and 4 with gentle tremolo."""
    t = tvec(dur)
    y = (np.sin(2 * np.pi * f * t) * 10 ** (-3 * t / t60)
         + 0.25 * np.sin(2 * np.pi * 4 * f * t) * 10 ** (-3 * t / (t60 * 0.15))
         + 0.08 * np.sin(2 * np.pi * 2.0 * f * t) * 10 ** (-3 * t / (t60 * 0.4)))
    y *= 1 + 0.12 * np.sin(2 * np.pi * 5.5 * t)
    return y * env_ad(len(t), 0.003, 100)


def s_station_chime(rng):
    dur = 2.1
    buf = np.zeros(int(dur * SR))
    for st, f in [(0.0, 659.26), (0.42, 523.25), (0.84, 783.99)]:
        place(buf, vib_tone(f, dur - st, 1.6), st, 1.0)
    return fft_filter(buf, lp(4500))


def s_crossing_bell(rng):
    L = int(1.0 * SR)
    buf = np.zeros(L)
    f0 = 740.0
    for st in (0.0, 0.5):
        s = modal([f0, f0 * 2.4, f0 * 3.95, f0 * 5.9], [1.0, 0.4, 0.15, 0.05],
                  [0.7, 0.4, 0.2, 0.1], 1.0, rng) * env_ad(L, 0.0015, 100)
        place(buf, s, st, wrap=True)
    return fft_filter(buf, lp(5000), circular=True)


def s_puff(rng):
    dur = 0.55
    n = int(dur * SR)
    t = np.arange(n) / SR
    fc = curve([(0, 1800), (0.4, 500), (dur, 450)], n)
    nz = tv_noise(n, lambda tt, ff: lp(1.0, 2)(ff / np.interp(tt, t, fc)), rng)
    e = env_ad(n, 0.025, 0.4)
    body = fft_filter(rng.standard_normal(n), lp(180)) * env_ad(n, 0.01, 0.15)
    return norm_rms(nz) * e + 0.5 * norm_rms(body) * env_ad(n, 0.01, 0.15)


def soft_brass(f, dur, t60=3.0, attack=0.03):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ff = f * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t / 0.2, 0, 1))
    ph = 2 * np.pi * np.cumsum(ff) / SR
    y = sum((k ** -1.6) * np.sin(k * ph) for k in range(1, 9) if k * f < 4500)
    rel = curve([(0, 1), (max(dur - 0.12, 0), 1), (dur, 0)], n)
    return y * env_ad(n, attack, t60) * rel


def s_tada(rng):
    dur = 1.5
    buf = np.zeros(int(dur * SR))
    for i, f in enumerate([523.25, 659.26, 783.99]):
        place(buf, soft_brass(f, 0.16, 1.0, 0.01), i * 0.1, 0.7)
        place(buf, vib_tone(f * 2, 0.4, 0.4), i * 0.1, 0.12)
    for f in [523.25, 659.26, 783.99, 1046.5]:
        place(buf, soft_brass(f, 1.15, 2.0, 0.02), 0.32, 0.5)
    place(buf, sparkle(rng, (2093, 2637, 3136), 0.05, 0.8, 0.4), 0.34, 0.25)
    return fft_filter(buf, lp(4500))


def s_switch_flip(rng):
    dur = 0.3
    buf = np.zeros(int(dur * SR))
    place(buf, wood_click(rng, 620, 0.15, 0.7), 0.0, 1.0)
    place(buf, wood_click(rng, 880, 0.15, 0.7), 0.045, 0.8)
    return fft_filter(buf, lp(6000))


# ----------------------------------------------------------------------------
# Animals (source-filter / formant synthesis)
# ----------------------------------------------------------------------------
def s_moo(rng):
    dur = 1.35
    n = int(dur * SR)
    t = np.arange(n) / SR
    f0 = curve([(0, 112), (0.18, 126), (0.5, 122), (1.0, 108), (dur, 98)], n, 40)
    f0 = f0 * (1 + 0.012 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.3) / 0.3, 0, 1))
    fm = morph([(0, "m"), (0.16, "m"), (0.32, "u"), (0.8, "o"), (1.1, "u"), (dur, "u")], n, 40, 0.92)
    # nasal 'm' = lowpassed murmur; mouth opens -> brighter
    mouth = curve([(0, 380), (0.16, 420), (0.32, 2600), (1.0, 2200), (dur, 900)], n, 30)
    fm.append((mouth, mouth * 1.4))
    amp = curve([(0, 0), (0.06, 0.55), (0.16, 0.6), (0.3, 1.0), (1.0, 0.9), (1.3, 0), (dur, 0)], n, 25)
    return voice(f0, fm, amp, tilt=0.9, breath=0.12, jitter=0.012, shimmer=0.06, fmax=5000, rng=rng)


def s_baa(rng):
    dur = 1.15
    n = int(dur * SR)
    t = np.arange(n) / SR
    f0 = curve([(0, 330), (0.08, 345), (0.45, 330), (0.55, 315), (dur, 285)], n, 30)
    trem_depth = curve([(0, 0.02), (0.2, 0.05), (0.6, 0.07), (dur, 0.08)], n)
    f0 = f0 * (1 + trem_depth * np.sin(2 * np.pi * 7.5 * t))
    # 'b' closure: formants start low and open into nasal-ish 'ae/eh'
    fm = morph([(0, "u"), (0.05, "a"), (0.45, "a"), (0.55, "e"), (0.7, "a"), (dur, "e")], n, 20, 1.15)
    amp = curve([(0, 0), (0.035, 1.0), (0.42, 0.9), (0.5, 0.55), (0.6, 0.85), (0.95, 0.7), (1.12, 0), (dur, 0)], n, 15)
    amp = amp * (1 + 0.25 * np.sin(2 * np.pi * 7.5 * t))
    return voice(f0, fm, amp, tilt=0.7, breath=0.18, jitter=0.02, shimmer=0.1, fmax=6500, rng=rng)


def s_cluck(rng):
    dur = 1.3
    n = int(dur * SR)
    buf = np.zeros(n)
    # three quick "buk"s
    for i, st in enumerate([0.0, 0.17, 0.34]):
        m = int(0.09 * SR)
        f0 = curve([(0, 430 - 15 * i), (0.09, 330)], m)
        fm = morph([(0, "u"), (0.02, "o"), (0.09, "u")], m, 5, 1.6)
        amp = curve([(0, 0), (0.006, 1), (0.04, 0.7), (0.085, 0), (0.09, 0)], m, 3)
        s = voice(f0, fm, amp, tilt=0.6, breath=0.45, jitter=0.04, fmax=6000, rng=rng)
        place(buf, s, st, 0.85)
    # "bu-kaaw"
    m = int(0.62 * SR)
    t = np.arange(m) / SR
    f0 = curve([(0, 420), (0.07, 400), (0.1, 520), (0.25, 760), (0.45, 640), (0.62, 520)], m, 15)
    fm = morph([(0, "u"), (0.07, "o"), (0.1, "u"), (0.15, "a"), (0.45, "a"), (0.62, "o")], m, 12, 1.5)
    amp = curve([(0, 0), (0.008, 0.8), (0.06, 0.3), (0.09, 0.05), (0.11, 1.0), (0.4, 0.85), (0.6, 0), (0.62, 0)], m, 5)
    s = voice(f0 * (1 + 0.015 * np.sin(2 * np.pi * 22 * t)), fm, amp, tilt=0.55, breath=0.3,
              jitter=0.03, shimmer=0.15, fmax=6500, rng=rng)
    place(buf, s, 0.6, 1.0)
    return buf


def s_bark(rng):
    dur = 0.75
    n = int(dur * SR)
    buf = np.zeros(n)
    for st, p in [(0.0, 1.0), (0.3, 1.08)]:
        m = int(0.22 * SR)
        f0 = curve([(0, 380 * p), (0.03, 470 * p), (0.2, 300 * p), (0.22, 290 * p)], m, 6)
        fm = morph([(0, "u"), (0.03, "a"), (0.12, "o"), (0.22, "u")], m, 8, 1.25)
        amp = curve([(0, 0), (0.008, 1.0), (0.06, 0.85), (0.19, 0.0), (0.22, 0)], m, 4)
        s = voice(f0, fm, amp, tilt=0.5, breath=0.55, jitter=0.05, shimmer=0.2, fmax=6500,
                  rng=rng, breath_hp=200)
        place(buf, s, st, 1.0 if st == 0 else 0.9)
    return buf


def s_meow(rng):
    dur = 0.95
    n = int(dur * SR)
    t = np.arange(n) / SR
    f0 = curve([(0, 480), (0.1, 560), (0.38, 700), (0.6, 640), (0.85, 520), (dur, 500)], n, 30)
    f0 = f0 * (1 + 0.008 * np.sin(2 * np.pi * 6 * t))
    fm = morph([(0, "m"), (0.05, "i"), (0.15, "i"), (0.42, "a"), (0.62, "a"), (0.85, "u"), (dur, "u")], n, 35, 1.25)
    amp = curve([(0, 0), (0.05, 0.5), (0.12, 0.9), (0.45, 1.0), (0.75, 0.7), (0.92, 0), (dur, 0)], n, 20)
    return voice(f0, fm, amp, tilt=0.8, breath=0.1, jitter=0.008, fmax=7000, rng=rng)


def s_neigh(rng):
    dur = 1.35
    n = int(dur * SR)
    t = np.arange(n) / SR
    f0 = curve([(0, 650), (0.08, 980), (0.25, 920), (0.6, 720), (1.0, 520), (1.3, 400), (dur, 390)], n, 40)
    vdepth = curve([(0, 0.0), (0.12, 0.03), (0.5, 0.07), (1.0, 0.09), (dur, 0.09)], n)
    f0 = f0 * (1 + vdepth * np.sin(2 * np.pi * 11.0 * t))
    fm = morph([(0, "i"), (0.3, "e"), (0.9, "e"), (dur, "a")], n, 40, 1.0)
    amp = curve([(0, 0), (0.06, 1.0), (0.8, 0.85), (1.15, 0.5), (1.32, 0), (dur, 0)], n, 20)
    amp = amp * (1 + 0.3 * vdepth / 0.09 * np.sin(2 * np.pi * 11.0 * t))
    return voice(f0, fm, amp, tilt=0.75, breath=0.22, jitter=0.02, shimmer=0.1, fmax=6500, rng=rng)


def chirp(f_keys, dur, rng=None):
    n = int(dur * SR)
    f = curve(f_keys, n, 3)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.08 * np.sin(2 * ph)
    e = np.sin(np.pi * np.arange(n) / n) ** 1.5
    return y * e


def s_tweet(rng):
    dur = 1.0
    buf = np.zeros(int(dur * SR))
    place(buf, chirp([(0, 2600), (0.03, 3800), (0.08, 3300)], 0.08), 0.0)
    place(buf, chirp([(0, 2600), (0.03, 3900), (0.08, 3300)], 0.08), 0.14)
    for i in range(5):  # little trill
        place(buf, chirp([(0, 3400), (0.035, 2700)], 0.035), 0.36 + i * 0.05, 0.75)
    place(buf, chirp([(0, 2400), (0.06, 3600), (0.14, 2900)], 0.14), 0.68, 0.9)
    return fft_filter(buf, lp(5500))


# ----------------------------------------------------------------------------
# Ambience
# ----------------------------------------------------------------------------
def s_squeak(rng):
    # Penguin / rabbit: two quick, bright, rising squeaks.
    dur = 0.55
    n = int(dur * SR)
    out = np.zeros(n)
    for start, f_a, f_b in ((0.0, 900, 1500), (0.22, 1000, 1700)):
        m = int(0.18 * SR)
        f0 = curve([(0, f_a), (0.06, f_b), (0.18, f_b * 0.92)], m, 8)
        fm = morph([(0, "i"), (0.18, "i")], m, 10, 1.6)
        amp = curve([(0, 0), (0.015, 1.0), (0.12, 0.8), (0.18, 0)], m, 6)
        place(out, voice(f0, fm, amp, tilt=0.6, breath=0.05, jitter=0.01, fmax=9000, rng=rng), start)
    return out


def s_snort(rng):
    # Reindeer: a soft breathy snort (filtered noise with a little nasal tone).
    dur = 0.6
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    noise = fft_filter(noise, chain(bp(700, 1.2), lp(2500)))
    amp = curve([(0, 0), (0.03, 1.0), (0.18, 0.55), (0.3, 0.9), (0.5, 0.2), (dur, 0)], n, 12)
    t = np.arange(n) / SR
    hum = 0.25 * np.sin(2 * np.pi * 140 * t) * curve([(0, 0), (0.05, 1), (0.4, 0.4), (dur, 0)], n, 20)
    return norm_rms(noise) * amp + hum


def s_quack(rng):
    # Duck: two nasal "wak" calls.
    dur = 0.75
    n = int(dur * SR)
    out = np.zeros(n)
    for start in (0.0, 0.33):
        m = int(0.26 * SR)
        f0 = curve([(0, 420), (0.05, 470), (0.26, 380)], m, 10)
        fm = morph([(0, "a"), (0.12, "a"), (0.26, "u")], m, 15, 1.15)
        amp = curve([(0, 0), (0.02, 1.0), (0.16, 0.85), (0.26, 0)], m, 8)
        place(out, voice(f0, fm, amp, tilt=0.35, breath=0.12, jitter=0.02, shimmer=0.05, fmax=6000, rng=rng), start)
    return out


def s_countryside_loop(rng):
    dur = 24.0
    L = int(dur * SR)
    t = np.arange(L) / SR

    def lfo():  # slow periodic random-ish modulation (integer cycles per loop)
        y = np.zeros(L)
        for k in range(1, 7):
            y += rng.uniform(0.3, 1.0) / k * np.sin(2 * np.pi * k / dur * t + rng.uniform(0, 2 * np.pi))
        return y / np.max(np.abs(y))

    common = periodic_noise(L, chain(lp(500, 1), hp(60)), rng)
    out = np.zeros((L, 2))
    for ch in range(2):
        own = periodic_noise(L, chain(lp(500, 1), hp(60)), rng)
        wind = norm_rms(0.6 * norm_rms(common) + 0.8 * norm_rms(own)) * (0.65 + 0.35 * lfo())
        rustle = norm_rms(periodic_noise(L, chain(bp(3000, 0.7), lp(6000)), rng))
        rg = np.clip(lfo(), 0, None) ** 2
        out[:, ch] = wind + 0.18 * rustle * rg
    # distant birds: soft chirps, low-passed and panned, wrapped around the loop
    birds = np.zeros((L, 2))
    times = np.sort(rng.uniform(0, dur, 14))
    for st in times:
        b = np.zeros(int(0.6 * SR))
        base = rng.uniform(2300, 3300)
        for j in range(rng.integers(2, 5)):
            c = chirp([(0, base), (0.025, base * rng.uniform(1.15, 1.35)), (0.06, base * 1.05)], 0.06)
            place(b, c, j * rng.uniform(0.09, 0.13), rng.uniform(0.6, 1.0))
        b = fft_filter(b, lp(3500))
        place(birds, pan(b, rng.uniform(-0.8, 0.8)), st, rng.uniform(0.5, 1.0), wrap=True)
    out = out / rms(out) + 0.9 * birds / (np.max(np.abs(birds)) + 1e-9) * 2.0
    return out


# ----------------------------------------------------------------------------
# Music
# ----------------------------------------------------------------------------
def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def ks_pluck(freq, dur, rng, t60=1.6, bright=3000.0):
    """Karplus-Strong pluck, block-vectorised; exact pitch via resampling."""
    N = max(8, int(SR / freq))
    f_ks = SR / (N + 0.5)
    r = freq / f_ks
    n_out = int(dur * SR)
    n_ks = int(n_out * r) + 2
    decay = 10 ** (-3 / (t60 * f_ks))
    y = np.zeros(n_ks + N + 1)
    exc = fft_filter(rng.uniform(-1, 1, N), lp(bright, 1))
    exc -= exc.mean()
    y[1:N + 1] = exc
    i = N + 1
    while i < len(y):
        e = min(i + N, len(y))
        y[i:e] = decay * 0.5 * (y[i - N:e - N] + y[i - N - 1:e - N - 1])
        i = e
    y = y[1:]
    out = np.interp(np.arange(n_out) * r, np.arange(len(y)), y)
    return out * env_ad(n_out, 0.002, 100)


def marimba(freq, dur):
    t = tvec(dur)
    y = (np.sin(2 * np.pi * freq * t) * 10 ** (-3 * t / 1.1)
         + 0.22 * np.sin(2 * np.pi * 3.93 * freq * t) * 10 ** (-3 * t / 0.18))
    return y * env_ad(len(t), 0.003, 100)


def bass_note(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t) + 0.08 * np.sin(6 * np.pi * freq * t)
    rel = curve([(0, 1), (dur - 0.08, 1), (dur, 0)], n)
    return y * env_ad(n, 0.008, 1.8) * rel


def s_snowy_loop(rng):
    """Snowy Valley: soft, airy wind (no birds) with occasional gentle wind-chime notes. Seamless loop."""
    dur = 24.0
    L = int(dur * SR)
    t = np.arange(L) / SR

    def lfo():
        y = np.zeros(L)
        for k in range(1, 6):
            y += rng.uniform(0.3, 1.0) / k * np.sin(2 * np.pi * k / dur * t + rng.uniform(0, 2 * np.pi))
        return y / np.max(np.abs(y))

    out = np.zeros((L, 2))
    common = periodic_noise(L, chain(lp(900, 1), hp(120)), rng)
    for ch in range(2):
        own = periodic_noise(L, chain(lp(900, 1), hp(120)), rng)
        wind = norm_rms(0.6 * norm_rms(common) + 0.8 * norm_rms(own)) * (0.55 + 0.45 * lfo())
        whistle = norm_rms(periodic_noise(L, bp(1400, 6.0), rng)) * np.clip(lfo(), 0, None) ** 3
        out[:, ch] = wind + 0.12 * whistle
    # a few soft chime notes (pentatonic), wrapped around the loop
    chimes = np.zeros((L, 2))
    notes = (1046.5, 1174.7, 1318.5, 1568.0, 1760.0)
    for st in np.sort(rng.uniform(0, dur, 7)):
        f = notes[rng.integers(0, len(notes))]
        c = tone(f, 2.2, harm=(1.0, 0.25, 0.08), attack=0.004, t60=1.6, rng=rng)
        place(chimes, pan(c, rng.uniform(-0.6, 0.6)), st, rng.uniform(0.12, 0.22), wrap=True)
    return out + chimes


def s_music_loop(rng):
    bpm = 100.0
    beat = 60.0 / bpm
    bar = 4 * beat
    bars = 24
    L = int(round(bars * bar * SR))
    mix = np.zeros((L, 2))
    chords = {  # I V vi IV in C
        "C": ([60, 64, 67, 72], 48, 55),
        "G": ([59, 62, 67, 71], 43, 50),
        "Am": ([57, 60, 64, 69], 45, 52),
        "F": ([57, 60, 65, 69], 41, 48),
    }
    prog = ["C", "G", "Am", "F"]

    uke = np.zeros(L)
    bass = np.zeros(L)
    shaker = np.zeros(L)
    mel = np.zeros(L)

    for b in range(bars):
        name = prog[b % 4]
        notes, root, fifth = chords[name]
        t0 = b * bar
        # ukulele strums (down on 1 and 3, light up-strums on the "and"s)
        for beat_pos, g, down in [(0, 1.0, True), (1.5, 0.45, False), (2, 0.8, True), (3, 0.5, True), (3.5, 0.4, False)]:
            order = notes if down else notes[::-1]
            for j, m in enumerate(order):
                s = ks_pluck(mtof(m), 1.6, rng, t60=1.4, bright=2500)
                place(uke, s, t0 + beat_pos * beat + j * 0.012, g * (0.9 if j else 1.0), wrap=True)
        # bass: root on 1, fifth on 3
        place(bass, bass_note(mtof(root), 2 * beat - 0.02), t0, 1.0, wrap=True)
        place(bass, bass_note(mtof(fifth if b % 2 == 0 else root), 2 * beat - 0.02), t0 + 2 * beat, 0.85, wrap=True)
        # shaker on eighths
        if b >= 2:
            for k in range(8):
                m = int(0.09 * SR)
                s = fft_filter(rng.standard_normal(m), chain(bp(5000, 0.9), lp(7000))) * env_ad(m, 0.006, 0.07)
                place(shaker, s, t0 + k * beat / 2, 1.0 if k % 2 else 0.55, wrap=True)

    # melody: four-bar phrases (beat, length, midi)
    A = [(0, 1, 76), (1, 1, 79), (2, 1, 76), (3, 1, 72),
         (4, 1, 74), (5, 1, 71), (6, 2, 74),
         (8, .5, 72), (8.5, .5, 76), (9, 1, 81), (10, 1, 79), (11, 1, 76),
         (12, 1, 77), (13, 1, 76), (14, 2, 74)]
    A2 = A[:-3] + [(12, 1, 77), (13, 1, 74), (14, 2, 72)]
    B = [(0, 2, 79), (2, 1, 76), (3, 1, 79),
         (4, 1.5, 79), (5.5, .5, 77), (6, 2, 74),
         (8, 1, 76), (9, 1, 72), (10, 1, 76), (11, 1, 81),
         (12, 3, 77), (15, 1, 76)]
    B2 = B[:-2] + [(12, 1, 77), (13, 1, 81), (14, 2, 79)]
    phrases = [None, A, A2, B, B2, A]  # intro is chords only
    for p, ph in enumerate(phrases):
        if ph is None:
            continue
        for st, ln, m in ph:
            ts = p * 4 * bar + st * beat
            place(mel, marimba(mtof(m), max(1.2, ln * beat + 0.6)), ts, 1.0, wrap=True)
            place(mel, marimba(mtof(m - 12), max(1.0, ln * beat + 0.4)), ts, 0.25, wrap=True)

    uke = norm_rms(uke)
    bass = norm_rms(bass)
    mel = norm_rms(mel)
    shaker = norm_rms(shaker)
    mix += pan(uke, -0.35) * 0.55
    mix += pan(bass, 0.0) * 0.6
    mix += pan(mel, 0.3) * 0.6
    mix += pan(shaker, 0.45) * 0.08

    # circular reverb (keeps loop seamless): decaying stereo noise IR
    ir_n = int(1.3 * SR)
    for ch in range(2):
        ir = rng.standard_normal(ir_n) * 10 ** (-3 * np.arange(ir_n) / SR / 1.3)
        ir = fft_filter(ir, lp(3500))
        ir /= np.sqrt(np.sum(ir ** 2))
        irp = np.zeros(L)
        irp[:ir_n] = ir
        wet = np.fft.irfft(np.fft.rfft(mix[:, ch]) * np.fft.rfft(irp), L)
        mix[:, ch] = mix[:, ch] + 0.35 * wet
    for ch in range(2):
        mix[:, ch] = fft_filter(mix[:, ch], chain(lp(7000, 2), hp(35)), circular=True)
    # gentle bus compression (RMS envelope, circular smoothing) to tame plucks
    pw = np.mean(mix ** 2, axis=1)
    box = np.zeros(L)
    box[:2205] = 1.0 / 2205
    box = np.roll(box, -1102)
    envl = np.sqrt(np.maximum(np.fft.irfft(np.fft.rfft(pw) * np.fft.rfft(box), L), 0))
    thr = np.percentile(envl, 50)
    gain = np.where(envl > thr, (thr / np.maximum(envl, 1e-9)) ** 0.5, 1.0)
    gain = fft_filter(gain, lp(8.0, 2), circular=True)  # smooth, still periodic
    mix = mix * gain[:, None]
    # gentle circular peak limiter: +-10 ms peak envelope, ceiling -4.4 dB
    pk = np.max(np.abs(mix), axis=1)
    w = int(0.010 * SR)
    pk = np.max(np.lib.stride_tricks.sliding_window_view(np.concatenate([pk[-w:], pk, pk[:w]]), 2 * w + 1), axis=1)
    ceil = 0.6 * pk.max()
    g = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    g = fft_filter(g, lp(25.0, 2), circular=True)  # smooth gain -> no distortion
    return mix * g[:, None]


# ----------------------------------------------------------------------------
# registry: name -> (fn, folder, peak dBFS, loop)
# ----------------------------------------------------------------------------
SOUNDS = {
    "whistle": (s_whistle, "SFX", -6.0, False),
    "bell": (s_bell, "SFX", -8.0, False),
    "chug_loop": (s_chug_loop, "SFX", -10.0, True),
    "rolling_loop": (s_rolling_loop, "SFX", -12.0, True),
    "motor_loop": (s_motor_loop, "SFX", -12.0, True),
    "track_place": (s_track_place, "SFX", -8.0, False),
    "track_snap": (s_track_snap, "SFX", -8.0, False),
    "track_remove": (s_track_remove, "SFX", -9.0, False),
    "invalid": (s_invalid, "SFX", -10.0, False),
    "button": (s_button, "SFX", -10.0, False),
    "button_toggle": (s_button_toggle, "SFX", -10.0, False),
    "undo": (s_undo, "SFX", -10.0, False),
    "place_decor": (s_place_decor, "SFX", -9.0, False),
    "station_chime": (s_station_chime, "SFX", -8.0, False),
    "crossing_bell": (s_crossing_bell, "SFX", -10.0, True),
    "puff": (s_puff, "SFX", -9.0, False),
    "tada": (s_tada, "SFX", -6.0, False),
    "switch_flip": (s_switch_flip, "SFX", -9.0, False),
    "moo": (s_moo, "SFX", -6.0, False),
    "baa": (s_baa, "SFX", -6.0, False),
    "cluck": (s_cluck, "SFX", -6.0, False),
    "bark": (s_bark, "SFX", -6.0, False),
    "meow": (s_meow, "SFX", -6.0, False),
    "neigh": (s_neigh, "SFX", -6.0, False),
    "tweet": (s_tweet, "SFX", -8.0, False),
    "squeak": (s_squeak, "SFX", -9.0, False),
    "snort": (s_snort, "SFX", -9.0, False),
    "quack": (s_quack, "SFX", -7.0, False),
    "countryside_loop": (s_countryside_loop, "Ambient", -14.0, True),
    "snowy_loop": (s_snowy_loop, "Ambient", -15.0, True),
    "music_loop": (s_music_loop, "Music", -6.0, True),
}

# Short-term loudness cap: no SFX's loudest 100 ms (RMS) may exceed the
# button's by more than this many dB (keeps the set soft and even).
LOUDNESS_CAP_DB = 6.0


def short_term_db(x, win_s=0.1):
    m = np.mean(np.square(x), axis=1) if x.ndim == 2 else np.square(x)
    w = int(win_s * SR)
    if len(m) <= w:
        return 10 * np.log10(np.mean(m) * len(m) / w + 1e-20)
    c = np.convolve(m, np.ones(w) / w, "valid")
    return 10 * np.log10(np.max(c) + 1e-20)


def finish(x, peak_db, loop):
    x = np.asarray(x, float)
    two = x.ndim == 2
    chans = [x[:, c] for c in range(x.shape[1])] if two else [x]
    out = []
    for c in chans:
        c = fft_filter(c, hp(25, 2), circular=loop)  # remove DC / sub rumble
        c = c - np.mean(c)
        if not loop:
            n = len(c)
            fi, fo = int(0.005 * SR), int(0.010 * SR)
            c[:fi] *= np.linspace(0, 1, fi)
            c[n - fo:] *= np.linspace(1, 0, fo)
        out.append(c)
    y = np.stack(out, axis=1) if two else out[0]
    return y * (db(peak_db) / np.max(np.abs(y)))


def write_wav(path, y):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = np.clip(np.round(y * 32767), -32767, 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2 if y.ndim == 2 else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def render(name):
    fn, folder, peak, loop = SOUNDS[name]
    return finish(fn(rng_for(name)), peak, loop)


def main(argv):
    if "--list" in argv:
        print("\n".join(SOUNDS))
        return 0
    names = [a for a in argv if not a.startswith("-")] or list(SOUNDS)
    bad = [n for n in names if n not in SOUNDS]
    if bad:
        print("unknown sound(s):", ", ".join(bad), file=sys.stderr)
        return 2
    ref = short_term_db(render("button"))
    for name in names:
        y = render(name)
        folder = SOUNDS[name][1]
        note = ""
        if folder == "SFX":
            st = short_term_db(y)
            if st > ref + LOUDNESS_CAP_DB:
                y = y * db(ref + LOUDNESS_CAP_DB - st)
                note = f" (loudness-capped {ref + LOUDNESS_CAP_DB - st:+.1f} dB)"
        path = os.path.join(OUT[folder], name + ".wav")
        write_wav(path, y)
        pk = 20 * np.log10(np.max(np.abs(y)) + 1e-12)
        print(f"{name:18s} {len(y) / SR:6.2f}s  peak {pk:6.1f} dBFS{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
