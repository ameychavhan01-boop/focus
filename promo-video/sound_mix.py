"""Builds the soundtrack (music + sound effects synced to the animation) for one version.
usage: python3 sound_mix.py A out.wav"""
import subprocess, sys, os
import numpy as np

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 29.0

def load(name):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(HERE, 'sounds', name + '.mp3'),
                          '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()

# each sound: (file, where the audible hit starts inside the file in seconds, base gain)
SFX = {k: (load(k), on, g) for k, on, g in [
    ('whoosh', 0.20, 0.55), ('click', 0.08, 1.6), ('pop', 0.03, 0.40), ('chime', 0.0, 0.55),
    ('impact', 0.0, 0.55), ('sparkle', 0.0, 0.9), ('tick', 0.10, 6.0)]}

def events(ver):
    E = []
    add = lambda name, t, v=1.0: E.append((name, t, v))
    # ---------------- hook
    add('impact', 0.0, 1.0)
    if ver == 'A':
        for t in (0.05, 0.16, 0.27, 0.38): add('pop', t, 0.5)
        add('pop', 0.75, 0.9); add('whoosh', 1.95, 0.9)
    if ver == 'B':
        for i in range(6): add('pop', 0.45 + i * 0.2, 0.8); add('click', 0.45 + i * 0.2, 0.5)
        add('chime', 1.62, 1.0); add('sparkle', 1.62, 0.6); add('whoosh', 2.05, 0.6)
    if ver == 'C':
        for i in range(6): add('tick', 0.55 + i * 0.1, 1.0)
        add('whoosh', 1.25, 0.9); add('pop', 1.62, 1.0); add('chime', 1.65, 0.8)
    # ---------------- intro
    add('whoosh', 2.35, 1.0); add('sparkle', 2.85, 0.35); add('pop', 2.7, 0.5)
    # ---------------- features
    for S in (4.0, 7.0, 10.5, 14.5, 17.5, 20.5):
        add('whoosh', S, 0.45)            # page scroll
        add('tick', S + 0.42, 1.0)        # outline appears
        add('whoosh', S + 0.72, 0.9)      # section lifts out
        add('pop', S + 0.15, 0.45)        # caption
        add('pop', S + 1.3, 0.6); add('pop', S + 1.55, 0.6)   # callouts
    S = 4.0   # Today & Overdue
    for t in (0.95, 1.05): add('tick', S + t, 0.8)
    for i in range(6): add('pop', S + 1.1 + i * 0.04, 0.35)
    for i in range(4): add('tick', S + 1.6 + i * 0.14, 0.7)
    S = 7.0   # board drag & drop
    for i in range(5): add('tick', S + 0.95 + i * 0.06, 0.6)
    add('click', S + 1.72, 1.0); add('whoosh', S + 1.9, 0.35); add('whoosh', S + 2.28, 0.35)
    add('click', S + 2.66, 1.0); add('chime', S + 2.7, 0.9)
    S = 10.5  # habits ticked
    for n in range(4):
        t = S + 1.55 + n * 0.42; add('click', t, 1.0); add('pop', t + 0.1, 0.55)
    add('chime', S + 3.0, 1.0)
    S = 14.5  # charts
    for i in range(7): add('tick', S + 0.95 + i * 0.07, 0.7)
    for i in range(3): add('tick', S + 1.05 + i * 0.3, 0.8)
    add('pop', S + 1.9, 0.8)
    S = 17.5  # goals
    for i in range(4): add('tick', S + 0.95 + i * 0.08, 0.6)
    for i in range(4): add('pop', S + 1.4 + i * 0.06, 0.4)
    add('chime', S + 2.15, 0.6)
    S = 20.5  # weekly review
    for i in range(4): add('pop', S + 1.3 + i * 0.07, 0.5)
    add('pop', S + 1.6, 0.6); add('chime', S + 2.1, 0.8)
    S = 23.5  # calendar + guide
    add('whoosh', S, 0.9); add('pop', S + 0.1, 0.45)
    for i in range(4): add('pop', S + 0.3 + i * 0.1, 0.45)
    add('tick', S + 0.7, 0.8)
    # ---------------- CTA
    C = 25.5
    add('whoosh', C, 1.0); add('pop', C + 0.45, 0.6)
    add('impact', C + 0.6, 0.9); add('sparkle', C + 0.65, 1.0)
    add('pop', C + 0.85, 1.0); add('sparkle', C + 1.2, 0.35)
    for b in range(4): add('tick', C + 1.5 + b * 0.5, 0.5)
    return E

def mix(ver, out):
    n = int(DUR * SR)
    music = load('music')
    # music: start so its beats land on the video's half-second grid, fade in fast, fade out at the end
    off = int(0.011 * SR)
    m = music[off:off + n].copy()
    if len(m) < n: m = np.vstack([m, np.zeros((n - len(m), 2), np.float32)])
    t = np.arange(n) / SR
    env = np.clip(t / 0.08, 0, 1) * np.clip((DUR - t) / 1.4, 0, 1)
    m *= (0.30 * env)[:, None]
    fx = np.zeros((n, 2), np.float32)
    for name, at, v in events(ver):
        clip, onset, g = SFX[name]
        s = int(round((at - onset) * SR)); c = clip
        if s < 0: c = c[-s:]; s = 0
        e = min(n, s + len(c))
        fx[s:e] += c[:e - s] * g * v
    # gentle ducking of music under busy sound-effect moments
    lvl = np.sqrt(np.convolve((fx ** 2).mean(1), np.ones(4800) / 4800, 'same'))
    duck = 1 / (1 + 3.0 * lvl)
    mixd = m * duck[:, None] + fx
    peak = np.abs(mixd).max()
    if peak > 0.95: mixd *= 0.95 / peak
    raw = out + '.raw.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', raw],
                   input=mixd.astype(np.float32).tobytes(), check=True)
    # loudness standard for Reels/Shorts (~ -14 LUFS), true-peak safe
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', str(SR), out], check=True)
    os.remove(raw)
    print('saved', out)

if __name__ == '__main__':
    mix(sys.argv[1].upper(), sys.argv[2])
