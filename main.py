#!/usr/bin/env python3
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
from pynput.keyboard import Listener, Key, Controller
import tempfile

model = whisper.load_model("base")
kbd = Controller()
chunks = []
stream = None

HOTKEY = Key.alt_r

def on_press(key):
    global stream
    if key == HOTKEY and stream is None:
        chunks.clear()
        stream = sd.InputStream(samplerate=16000, channels=1, callback=lambda indata, *_: chunks.append(indata.copy()))
        stream.start()
        print("recording...")

def on_release(key):
    global stream
    if key == HOTKEY and stream is not None:
        stream.stop()
        stream.close()
        stream = None
        audio = np.concatenate(chunks)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, 16000)
            text = model.transcribe(f.name)["text"]
            print(f"transcribed: {text}")
            kbd.type(text)

with Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
