"""Morse code core: text -> Morse, timing, and WAV synthesis (standard library only)."""
import io
import math
import struct
import unicodedata
import wave

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H": "....",
    "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.",
    "Q": "--.-", "R": ".-.", "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.", "!": "-.-.--", "/": "-..-.",
    "(": "-.--.", ")": "-.--.-", "&": ".-...", ":": "---...", ";": "-.-.-.", "=": "-...-",
    "+": ".-.-.", "-": "-....-", "_": "..--.-", '"': ".-..-.", "$": "...-..-", "@": ".--.-.",
}
REVERSE = {v: k for k, v in MORSE.items()}

SAMPLE_RATE = 22050


def normalize(text):
    """Upper-case and strip accents (e.g. 'é' -> 'E')."""
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").upper()


def encode(text):
    """Return (words, skipped). words = list of words, each a list of (char, code)."""
    words, skipped, cur = [], [], []
    for ch in normalize(text):
        if ch.isspace():
            if cur:
                words.append(cur)
                cur = []
        elif ch in MORSE:
            cur.append((ch, MORSE[ch]))
        elif ch not in skipped:
            skipped.append(ch)
    if cur:
        words.append(cur)
    return words, skipped


def to_morse_string(words):
    return " / ".join(" ".join(code for _, code in w) for w in words)


def decode(morse):
    """Inverse of to_morse_string; unknown groups become '?'."""
    out = []
    for word in morse.strip().split("/"):
        out.append("".join(REVERSE.get(g, "?") for g in word.split()))
    return " ".join(out)


def unit_seconds(wpm):
    """PARIS standard: one unit lasts 1.2 / WPM seconds."""
    return 1.2 / wpm


def timeline(words, wpm):
    """List of (start_s, duration_s) tones, and total duration. Dot=1, dash=3 units;
    gaps: 1 within a letter, 3 between letters, 7 between words."""
    u = unit_seconds(wpm)
    t, tones = 0.0, []
    for wi, word in enumerate(words):
        if wi:
            t += 7 * u
        for li, (_, code) in enumerate(word):
            if li:
                t += 3 * u
            for si, sym in enumerate(code):
                if si:
                    t += u
                d = (1 if sym == "." else 3) * u
                tones.append((t, d))
                t += d
    return tones, t


def synth_wav(text, wpm=15, freq=600, volume=0.5, ramp=0.005):
    """Render text as a mono 16-bit WAV (bytes). Raises ValueError if nothing is encodable."""
    words, _ = encode(text)
    tones, total = timeline(words, wpm)
    if not tones:
        raise ValueError("Nothing to encode.")
    pad = 0.15
    n = int((total + 2 * pad) * SAMPLE_RATE)
    amp = max(0.0, min(1.0, volume)) * 32767 * 0.9
    buf = [0] * n
    for start, dur in tones:
        i0 = int((start + pad) * SAMPLE_RATE)
        i1 = int((start + pad + dur) * SAMPLE_RATE)
        r = max(1, int(ramp * SAMPLE_RATE))
        for i in range(i0, min(i1, n)):
            env = min(1.0, (i - i0) / r, (i1 - i) / r)
            buf[i] = int(amp * env * math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(struct.pack("<%dh" % n, *buf))
    return out.getvalue()
