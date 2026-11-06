#!/usr/bin/env python3
"""Synthesise every sound in the game into assets/audio/*.wav.

Run this only when the sound design changes (needs numpy; the game itself does not).
All music is original and generated here: slow ambient pads, soft piano-like bells,
a gentle wind bed and a synthetic reverb, rendered as seamless loops.
"""
import os
import wave

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "assets", "audio")
RNG = np.random.default_rng(20261107)


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def save(name, data, rate, peak_level=0.89):
    data = np.asarray(data, dtype=np.float64)
    if data.ndim == 1:
        data = data[:, None]
    peak = np.max(np.abs(data)) or 1.0
    data = data / peak * peak_level
    pcm = (data * 32767).astype("<i2")
    with wave.open(os.path.join(OUT, name), "wb") as handle:
        handle.setnchannels(pcm.shape[1])
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())
    print(f"{name}: {len(pcm) / rate:.1f}s")


def lowpass(signal, rate, cutoff, order=4):
    spec = np.fft.rfft(signal, axis=0)
    freqs = np.fft.rfftfreq(signal.shape[0], 1 / rate)
    curve = 1 / (1 + (freqs / cutoff) ** order)
    if signal.ndim == 2:
        curve = curve[:, None]
    return np.fft.irfft(spec * curve, n=signal.shape[0], axis=0)


def bandpass(signal, rate, low, high):
    spec = np.fft.rfft(signal, axis=0)
    freqs = np.fft.rfftfreq(signal.shape[0], 1 / rate)
    curve = (1 / (1 + (freqs / high) ** 4)) * (1 - 1 / (1 + (freqs / low) ** 4))
    return np.fft.irfft(spec * curve, n=signal.shape[0], axis=0)


def circular_reverb(signal, rate, seconds=4.0, mix=0.55, seed=1):
    """Convolve with decaying noise, wrapping the tail so the loop stays seamless."""
    rng = np.random.default_rng(seed)
    n = signal.shape[0]
    out = np.zeros((n, 2))
    length = int(seconds * rate)
    t = np.arange(length) / rate
    for ch in range(2):
        ir = rng.standard_normal(length) * np.exp(-t * 6.9 / seconds)
        ir = lowpass(ir, rate, 3000)
        ramp = int(0.02 * rate)
        ir[:ramp] *= np.linspace(0, 1, ramp)
        ir /= np.sqrt(np.sum(ir ** 2))
        wet = np.fft.irfft(np.fft.rfft(signal[:, ch], n) * np.fft.rfft(ir, n), n)
        out[:, ch] = signal[:, ch] * (1 - mix) + wet * mix * 1.6
    return out


def envelope(n, rate, attack, release):
    env = np.ones(n)
    a = min(n, max(1, int(attack * rate)))
    r = min(n - a, max(1, int(release * rate)))
    env[:a] = np.linspace(0, 1, a) ** 2
    env[n - r:] *= np.linspace(1, 0, r) ** 2
    return env


def pad_voice(m, seconds, rate, bright=1.0):
    n = int(seconds * rate)
    t = np.arange(n) / rate
    out = np.zeros(n)
    for detune in (-0.06, 0.0, 0.07):
        f = midi_hz(m + detune)
        phase = RNG.uniform(0, 2 * np.pi)
        for h, amp in ((1, 1.0), (2, 0.35 * bright), (3, 0.14 * bright), (4, 0.06 * bright)):
            out += amp * np.sin(2 * np.pi * f * h * t + phase * h)
    lfo = 1 + 0.2 * np.sin(2 * np.pi * RNG.uniform(0.05, 0.12) * t + RNG.uniform(0, 6))
    return out * lfo * envelope(n, rate, seconds * 0.4, seconds * 0.45) / 3


def keys(m, seconds, rate, decay=1.6):
    """A soft electric-piano / celesta tone."""
    n = int(seconds * rate)
    t = np.arange(n) / rate
    f = midi_hz(m)
    out = (np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * f * t) * np.exp(-t * 4))
           + 0.25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 2.5)
           + 0.08 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 6))
    env = np.exp(-t * decay)
    a = int(0.006 * rate)
    env[:a] *= np.linspace(0, 1, a)
    return out * env


def place(buffer, sound, start, gain=1.0, pan=0.0):
    """Add a mono sound into a stereo loop buffer, wrapping around the end."""
    n = buffer.shape[0]
    left = gain * np.sqrt((1 - pan) / 2)
    right = gain * np.sqrt((1 + pan) / 2)
    idx = (np.arange(len(sound)) + start) % n
    np.add.at(buffer[:, 0], idx, sound * left)
    np.add.at(buffer[:, 1], idx, sound * right)


def ambient_track(rate, chords, chord_seconds, scale, notes_per_chord, bass, seed, bright):
    global RNG
    RNG = np.random.default_rng(seed)
    n = int(len(chords) * chord_seconds * rate)
    buf = np.zeros((n, 2))
    overlap = 3.0
    for i, chord in enumerate(chords):
        start = int((i * chord_seconds - overlap / 2) * rate)
        for j, m in enumerate(chord):
            voice = pad_voice(m, chord_seconds + overlap, rate, bright)
            place(buf, voice, start, 0.15, pan=(j / max(1, len(chord) - 1)) * 1.2 - 0.6)
        place(buf, pad_voice(bass[i], chord_seconds + overlap, rate, 0.25), start, 0.22)
        # a slow, sparse melody of soft keys, always from the scale
        times = np.sort(RNG.uniform(0.4, chord_seconds - 0.6, notes_per_chord))
        prev = int(RNG.choice(scale))
        for tm in times:
            idx = scale.index(prev) + int(RNG.choice([-2, -1, 1, 1, 2]))
            prev = scale[max(0, min(len(scale) - 1, idx))]
            place(buf, keys(prev, 5.0, rate, decay=RNG.uniform(0.9, 1.5)),
                  int((i * chord_seconds + tm) * rate), RNG.uniform(0.05, 0.08), RNG.uniform(-0.6, 0.6))
    noise = lowpass(RNG.standard_normal((n, 2)), rate, 420)
    swell = 0.5 + 0.5 * np.sin(2 * np.pi * np.arange(n) / n * 4)[:, None]
    buf += noise * 0.01 * swell
    buf = lowpass(buf, rate, 4800)
    return circular_reverb(buf, rate, seconds=5.5, mix=0.55, seed=seed)


def music():
    rate = 22050
    # Title: F major / D minor colours, open and warm
    chords = [[65, 69, 72, 76], [62, 65, 69, 72], [58, 62, 65, 69], [60, 64, 67, 70],
              [65, 69, 72, 77], [57, 60, 64, 67], [58, 62, 65, 72], [60, 65, 67, 70]]
    bass = [41, 38, 34, 36, 41, 33, 34, 36]
    scale = [72, 74, 76, 77, 79, 81, 84, 86]
    save("bgm_title.wav", ambient_track(rate, chords, 7, scale, 3, bass, 11, 0.8), rate)
    # Game: slow A minor / C lydian drift so it calms instead of distracting
    chords = [[57, 60, 64, 71], [53, 57, 60, 64], [60, 64, 67, 71], [55, 59, 62, 66],
              [57, 60, 64, 69], [50, 53, 57, 60, 64], [52, 55, 59, 62], [53, 57, 60, 67]]
    bass = [33, 29, 36, 31, 33, 26, 28, 29]
    scale = [69, 71, 72, 74, 76, 79, 81, 83]
    save("bgm_game.wav", ambient_track(rate, chords, 8, scale, 2, bass, 23, 0.6), rate)


def tone(freq, seconds, rate, kind="sine", decay=8.0, attack=0.003):
    n = int(seconds * rate)
    t = np.arange(n) / rate
    f = np.asarray(freq) if np.ndim(freq) else np.full(n, freq)
    phase = 2 * np.pi * np.cumsum(f) / rate
    if kind == "sine":
        s = np.sin(phase)
    elif kind == "tri":
        s = 2 / np.pi * np.arcsin(np.sin(phase))
    else:  # bell
        s = np.sin(phase) + 0.3 * np.sin(2.76 * phase) * np.exp(-t * 4) + 0.12 * np.sin(5.4 * phase) * np.exp(-t * 8)
    env = np.exp(-t * decay)
    a = max(1, int(attack * rate))
    env[:a] *= np.linspace(0, 1, a)
    return s * env


def effects():
    rate = 44100
    rng = np.random.default_rng(9)

    def cat(*parts):
        return np.concatenate(parts)

    def silence(s):
        return np.zeros(int(s * rate))

    def mix(*sounds):
        n = max(len(s) for s in sounds)
        out = np.zeros(n)
        for s in sounds:
            out[: len(s)] += s
        return out

    def stereo(mono, verb=0.25):
        pad = np.concatenate([mono, np.zeros(int(0.5 * rate))])
        length = int(0.45 * rate)
        t = np.arange(length) / rate
        out = np.zeros((len(pad), 2))
        for ch in range(2):
            ir = rng.standard_normal(length) * np.exp(-t * 12)
            ir /= np.sqrt(np.sum(ir ** 2))
            wet = np.convolve(pad, ir)[: len(pad)]
            out[:, ch] = pad * (1 - verb) + wet * verb
        return out

    def wood(pitch=1.0, seconds=0.16):
        """A wooden piece set down on a board: a filtered knock plus a short body tone."""
        n = int(seconds * rate)
        t = np.arange(n) / rate
        knock = bandpass(rng.standard_normal(n), rate, 900 * pitch, 3800 * pitch) * np.exp(-t * 70)
        body = (np.sin(2 * np.pi * 190 * pitch * t) * 0.9 + np.sin(2 * np.pi * 410 * pitch * t) * 0.4) * np.exp(-t * 38)
        return knock * 0.9 + body

    save("move.wav", stereo(wood(1.0), 0.18), rate)
    save("cpu.wav", stereo(wood(0.85), 0.18), rate)
    save("capture.wav", stereo(mix(wood(1.1), cat(silence(0.07), wood(0.9)),
                                   cat(silence(0.05), tone(midi_hz(84), 0.5, rate, "bell", decay=7) * 0.35)), 0.25), rate)
    save("castle.wav", stereo(mix(wood(1.0), cat(silence(0.13), wood(1.15))), 0.2), rate)
    save("check.wav", stereo(mix(tone(midi_hz(81), 0.7, rate, "bell", decay=5),
                                 cat(silence(0.12), tone(midi_hz(86), 0.8, rate, "bell", decay=5))) * 0.7, 0.35), rate)
    save("promote.wav", stereo(mix(*[cat(silence(i * 0.07), tone(midi_hz(m), 0.7, rate, "bell", decay=5))
                                     for i, m in enumerate([72, 76, 79, 84, 88])]), 0.35), rate)
    save("click.wav", stereo(tone(1100, 0.06, rate, decay=60) * 0.6, 0.1), rate)
    save("hover.wav", tone(2100, 0.03, rate, decay=120) * 0.3, rate)
    n = int(0.05 * rate)
    t = np.arange(n) / rate
    keyclick = bandpass(rng.standard_normal(n), rate, 2000, 7000) * np.exp(-t * 160) + np.sin(2 * np.pi * 900 * t) * np.exp(-t * 120) * 0.3
    save("key.wav", keyclick, rate)
    err = cat(tone(330, 0.12, rate, "tri", decay=8), tone(247, 0.25, rate, "tri", decay=7))
    save("error.wav", stereo(err * 0.8), rate)
    save("tick.wav", tone(1500, 0.05, rate, "sine", decay=70) * 0.7, rate)
    seq = mix(*[cat(silence(i * 0.2), tone(midi_hz(m), 0.6, rate, "tri", decay=4)) for i, m in enumerate([69, 65, 62, 57])])
    save("timeout.wav", stereo(seq, 0.4), rate)
    seq = mix(*[cat(silence(i * 0.12), tone(midi_hz(m), 1.6, rate, "bell", decay=2.5)) for i, m in enumerate([60, 64, 67, 72, 76, 79, 84])],
              cat(silence(0.8), tone(midi_hz(48), 2.0, rate, "tri", decay=1.5) * 0.5))
    save("win.wav", stereo(seq, 0.4), rate)
    seq = mix(*[cat(silence(i * 0.3), tone(midi_hz(m), 1.2, rate, "tri", decay=2.5)) for i, m in enumerate([64, 60, 57, 52])])
    save("lose.wav", stereo(seq, 0.45), rate)
    seq = mix(tone(midi_hz(67), 1.4, rate, "bell", decay=2.5), cat(silence(0.35), tone(midi_hz(72), 1.4, rate, "bell", decay=2.5)))
    save("draw.wav", stereo(seq, 0.4), rate)
    save("start.wav", stereo(mix(tone(midi_hz(64), 0.6, rate, "bell", decay=5),
                                 cat(silence(0.12), tone(midi_hz(71), 0.9, rate, "bell", decay=4))), 0.35), rate)
    save("new_record.wav", stereo(mix(*[cat(silence(i * 0.09), tone(midi_hz(m), 0.9, rate, "bell", decay=4))
                                        for i, m in enumerate([72, 79, 84, 88, 91])]), 0.4), rate)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    effects()
    music()
