import argparse, fcntl, importlib.metadata, os, sys, tempfile, threading, time
from contextlib import contextmanager
import numpy as np
import sounddevice as sd
import soundfile as sf
from pywhispercpp.model import Model
from pywhispercpp.constants import AVAILABLE_MODELS

@contextmanager
def hotkey_listener(hotkey):
    # Must remain alive for the entire session — never stop and restart between recordings.
    # Pasting via kbd.tap() while this listener is active prevents transcribed text from
    # leaking into the terminal's pty buffer on Ctrl+C.
    # See docs/ctrl-c-leak-investigation.md for details.
    from pynput.keyboard import Key, Listener
    pressed = threading.Event()
    released = threading.Event()
    cancelled = threading.Event()
    def on_press(key):
        if key == hotkey:
            cancelled.clear()
            released.clear()
            pressed.set()
        elif key == Key.esc and pressed.is_set():
            # ESC during recording: abort and discard audio
            cancelled.set()
            pressed.clear()
            released.set()  # unblock record()'s wait loop
    def on_release(key):
        if key == hotkey:
            pressed.clear()
            released.set()
    with Listener(on_press=on_press, on_release=on_release) as listener:
        yield pressed, released, cancelled, listener


def record(pressed, released, cancelled, listener):
    """Block until the hotkey is pressed and released, return the audio as an np.ndarray"""
    pressed.wait()
    chunks = []
    with sd.InputStream(samplerate=16000, channels=1, callback=lambda indata, *_: chunks.append(indata.copy())):
        print('recording...')
        while not released.wait(timeout=0.1):
            if not listener.is_alive():
                break
    if not chunks:
        return None
    if cancelled.is_set():
        print('canceled')
        return None
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


def paste(text, kbd):
    """Paste text without leaving our temporary value on the user's clipboard."""
    import pyperclip
    from pynput.keyboard import Key

    previous_text = pyperclip.paste()
    pyperclip.copy(text)
    try:
        with kbd.pressed(Key.cmd):
            kbd.tap('v')
        time.sleep(0.1)  # avoid event racing
    finally:
        # Never overwrite text copied after we installed the transcription.
        if pyperclip.paste() == text:
            pyperclip.copy(previous_text)


def models():
    order = ['tiny', 'base', 'small', 'medium', 'large-v1', 'large-v2', 'large-v3']
    group = {k:[m for m in AVAILABLE_MODELS if m.startswith(k)] for k in order}
    misc = set(AVAILABLE_MODELS) - set([m for ms in group.values() for m in ms])
    if misc: 
        group['misc'] = list(misc)

    lines = [f"  {k + ':':<18}{', '.join(v)}" for k, v in group.items()]
    return 'models:\n' + '\n'.join(lines)


def main():
    from pynput.keyboard import Key, Controller
    p = argparse.ArgumentParser(
        epilog=f'example: %(prog)s --model base --key alt_r\n\n{models()}',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=importlib.metadata.version("whisper-ptt"))
    p.add_argument("--model", default='base', metavar='MODEL', choices=AVAILABLE_MODELS, help="whisper model (see below)")
    p.add_argument("--lang", help="language code (en, zh, ja, etc.), omit for auto-detection")
    p.add_argument("--key", default='alt_r', metavar='KEY', choices=[k.name for k in Key],
                   help="pynput Key name, see https://pynput.readthedocs.io/en/latest/keyboard.html#pynput.keyboard.Key")
    args = p.parse_args()

    # Prevent multiple instances; lock is auto-released on exit
    lock = open("/tmp/whisper-ptt.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        exit("Another instance is already running")

    # Load model and start the record-transcribe-paste loop
    print(f"hotkey: {args.key}; model {args.model}; lang {args.lang}")
    hotkey = getattr(Key, args.key)

    print(f"loading model ...")
    model = Model(args.model, print_realtime=False, print_progress=False, redirect_whispercpp_logs_to=None, language=args.lang)
    print("loaded")

    kbd = Controller()

    with hotkey_listener(hotkey) as (pressed, released, cancelled, listener):
        while True:
            audio = record(pressed, released, cancelled, listener)
            if audio is None: continue
            text = transcribe(model, audio)
            print(f"transcribed: {text}")
            paste(text, kbd)

if __name__ == "__main__":
    assert sys.platform != "win32", "Windows is not supported"
    try:
        main()
    except KeyboardInterrupt:
        pass
