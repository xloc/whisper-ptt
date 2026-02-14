import numpy as np
from pywhispercpp.constants import AVAILABLE_MODELS
from main import transcribe

def test_available_models():
    assert 'base' in AVAILABLE_MODELS
    assert 'tiny' in AVAILABLE_MODELS

def test_transcribe_with_silence():
    """transcribe silent audio - tests file I/O and model invocation"""
    from pywhispercpp.model import Model
    model = Model('tiny', print_realtime=False, print_progress=False, redirect_whispercpp_logs_to=None)
    silence = np.zeros(16000, dtype=np.float32)  # 1 second of silence
    text = transcribe(model, silence)
    assert isinstance(text, str)
