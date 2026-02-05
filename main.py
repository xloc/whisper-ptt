#!/usr/bin/env python3
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
from pynput.keyboard import Listener, Key, Controller
import tempfile, threading

model = whisper.load_model("base")
kbd = Controller()
HOTKEY = Key.alt_r

def record(hotkey):
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
    return np.concatenate(chunks)

def transcribe(audio):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio, 16000)
        return model.transcribe(f.name, fp16=False)["text"]

while True:
    audio = record(HOTKEY)
    text = transcribe(audio)
    print(f"transcribed: {text}")
    kbd.type(text)
