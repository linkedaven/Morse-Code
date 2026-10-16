import io
import math
import os
import sys
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import morse


def test_roundtrip():
    for text in ["SOS", "HELLO WORLD", "PARIS 73", "A.B,C?"]:
        words, _ = morse.encode(text)
        assert morse.decode(morse.to_morse_string(words)) == text


def test_accents_and_skips():
    words, skipped = morse.encode("café ☃")
    assert morse.to_morse_string(words) == "-.-. .- ..-. ."
    assert skipped == ["☃"]


def test_paris_is_50_units():
    words, _ = morse.encode("PARIS")
    _, total = morse.timeline(words, 20)
    assert round(total / morse.unit_seconds(20)) + 7 == 50


def test_wav_is_valid_and_matches_duration():
    data = morse.synth_wav("SOS", wpm=20)
    with wave.open(io.BytesIO(data)) as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2
        dur = w.getnframes() / w.getframerate()
    _, total = morse.timeline(morse.encode("SOS")[0], 20)
    assert math.isclose(dur, total + 0.3, abs_tol=0.01)


def test_empty_raises():
    try:
        morse.synth_wav("☃")
    except ValueError:
        return
    raise AssertionError("expected ValueError")
