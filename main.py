import argparse, os, sys, tempfile, threading
assert sys.platform != "win32", "Windows is not supported"
import fcntl
from pywhispercpp.model import Model
from pywhispercpp.constants import AVAILABLE_MODELS
import sounddevice as sd
import soundfile as sf
import numpy as np


def record(hotkey):
    from pynput.keyboard import Listener
    """Block until the hotkey is pressed and released, return the audio as an np.ndarray"""
    pressed = threading.Event()
    released = threading.Event()
    def on_press(key):
        if key == hotkey:
            released.clear()
            pressed.set()
    def on_release(key):
        if key == hotkey:
            pressed.clear()
            released.set()
    with Listener(on_press=on_press, on_release=on_release):
        pressed.wait()
        chunks = []
        stream = sd.InputStream(samplerate=16000, channels=1, callback=lambda indata, *_: chunks.append(indata.copy()))
        stream.start()
        print("recording...")
        while not released.wait(timeout=0.1):
            pass
        stream.stop()
        stream.close()
    audio = np.concatenate(chunks)
    print(f"duration: {len(audio) / 16000:.1f}s, rms: {np.sqrt(np.mean(audio ** 2)):.4f}")
    return audio

def transcribe(model, audio) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio, 16000)
    segments = model.transcribe(f.name)
    text = ' '.join(segment.text for segment in segments)
    os.unlink(f.name)
    return text

def main():
    # Prevent multiple instances; lock is auto-released on exit
    lock = open("/tmp/whisper-ptt.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        exit("Another instance is already running")

    from pynput.keyboard import Key, Controller
    p = argparse.ArgumentParser(epilog="example: %(prog)s --model base --key alt_r")
    p.add_argument("--model", default='base', choices=AVAILABLE_MODELS, help="whisper model name")
    p.add_argument("--lang", help="language code (en, zh, ja, etc.), omit for auto-detection")
    p.add_argument("--key", default='alt_r', choices=[k.name for k in Key],
                   help="pynput Key name, see https://pynput.readthedocs.io/en/latest/keyboard.html#pynput.keyboard.Key")
    args = p.parse_args()

    print(f"hotkey: {args.key}; model {args.model}; lang {args.lang}")
    hotkey = getattr(Key, args.key)

    print(f"loading model ...")
    model = Model(args.model, print_realtime=False, print_progress=False, redirect_whispercpp_logs_to=None, language=args.lang)
    print("loaded")

    kbd = Controller()
    try:
        while True:
            audio = record(hotkey)
            text = transcribe(model, audio)
            print(f"transcribed: {text}")
            kbd.type(text)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
