import argparse, tempfile, threading
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
from pynput.keyboard import Listener, Key, Controller


def record(hotkey):
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
        released.wait()
        stream.stop()
        stream.close()
    audio = np.concatenate(chunks)
    print(f"duration: {len(audio) / 16000:.1f}s, rms: {np.sqrt(np.mean(audio ** 2)):.4f}")
    return audio

def transcribe(model, audio) -> str:
    """Return transcribed text"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio, 16000)
        return model.transcribe(f.name, fp16=False)["text"]

def main():
    p = argparse.ArgumentParser(epilog="example: %(prog)s --model base --key alt_r")
    p.add_argument("--model", default='base', choices=whisper.available_models(), help="whisper model name")
    p.add_argument("--key", default='alt_r', choices=[k.name for k in Key], help="pynput Key name, see https://pynput.readthedocs.io/en/latest/keyboard.html#pynput.keyboard.Key")
    args = p.parse_args()

    print(f"hotkey: {args.key}; model {args.model}")
    hotkey = getattr(Key, args.key)

    print(f"loading model ...")
    model = whisper.load_model(args.model)
    print("loaded")

    kbd = Controller()
    while True:
        audio = record(hotkey)
        text = transcribe(model, audio)
        print(f"transcribed: {text}")
        kbd.type(text)

if __name__ == "__main__":
    main()
