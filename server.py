"""Morse code backend: encoding and WAV synthesis over HTTP.

Run:  python server.py   (opens http://127.0.0.1:8002 in your browser)
"""
import logging
import os
import socket
import sys
import threading
import time
import webbrowser

from flask import Flask, Response, jsonify, request, send_from_directory

import morse

BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, static_folder=os.path.join(BASE, "static"), static_url_path="/static")
MAX_CHARS = 500


def _num(src, key, default, lo, hi):
    try:
        v = float(src.get(key, default))
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number.")
    if not lo <= v <= hi:
        raise ValueError(f"{key} must be between {lo:g} and {hi:g}.")
    return v


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/encode")
def api_encode():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", ""))[:MAX_CHARS]
    try:
        wpm = _num(data, "wpm", 15, 5, 40)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    words, skipped = morse.encode(text)
    tones, total = morse.timeline(words, wpm)
    return jsonify(
        morse=morse.to_morse_string(words),
        words=[[{"ch": c, "code": k} for c, k in w] for w in words],
        skipped=skipped,
        duration_s=total,
        unit_s=morse.unit_seconds(wpm),
        tones=[{"t": t, "dur": d} for t, d in tones],
    )


@app.post("/api/decode")
def api_decode():
    data = request.get_json(silent=True) or {}
    return jsonify(text=morse.decode(str(data.get("morse", ""))[: MAX_CHARS * 8]))


@app.get("/api/audio.wav")
def api_audio():
    args = request.args
    try:
        wpm = _num(args, "wpm", 15, 5, 40)
        freq = _num(args, "freq", 600, 300, 1000)
        vol = _num(args, "vol", 50, 0, 100) / 100
        wav = morse.synth_wav(args.get("text", "")[:MAX_CHARS], wpm, freq, vol)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return Response(wav, mimetype="audio/wav",
                    headers={"Content-Disposition": 'attachment; filename="morse.wav"'})


# ----------------------------------------------------------------------
# Launcher: open the browser, and quit when the browser tab is closed
# ----------------------------------------------------------------------
HOST, PORT = "127.0.0.1", 8002
URL = f"http://{HOST}:{PORT}"
_seen = {"last": time.time(), "bye": None}


@app.post("/api/ping")
def ping():
    _seen["last"] = time.time()
    _seen["bye"] = None
    return jsonify(ok=True)


@app.post("/api/bye")
def bye():
    _seen["bye"] = time.time() + 5
    return jsonify(ok=True)


def _watchdog():
    while True:
        time.sleep(1)
        now = time.time()
        if (_seen["bye"] and now > _seen["bye"]) or now - _seen["last"] > 120:
            os._exit(0)


def _already_running():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, PORT)) == 0


def main():
    if _already_running():
        webbrowser.open(URL)
        return
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w"))
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    threading.Thread(target=_watchdog, daemon=True).start()
    threading.Timer(1.0, webbrowser.open, args=[URL]).start()
    app.run(host=HOST, port=PORT, threaded=True)


if __name__ == "__main__":
    print(f"Morse code server running at {URL}  (Ctrl+C to stop)")
    main()
