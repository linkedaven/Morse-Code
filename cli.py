"""Command-line use:  python cli.py "SOS" [--wpm 15] [--freq 600] [--wav out.wav]"""
import argparse

import morse


def main():
    ap = argparse.ArgumentParser(description="Text to Morse code")
    ap.add_argument("text")
    ap.add_argument("--wpm", type=float, default=15)
    ap.add_argument("--freq", type=float, default=600)
    ap.add_argument("--volume", type=float, default=0.5)
    ap.add_argument("--wav", help="write audio to this .wav file")
    a = ap.parse_args()
    words, skipped = morse.encode(a.text)
    print(morse.to_morse_string(words))
    if skipped:
        print("skipped:", " ".join(skipped))
    if a.wav:
        with open(a.wav, "wb") as f:
            f.write(morse.synth_wav(a.text, a.wpm, a.freq, a.volume))
        print("wrote", a.wav)


if __name__ == "__main__":
    main()
