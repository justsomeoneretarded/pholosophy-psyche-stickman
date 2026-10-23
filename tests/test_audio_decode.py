import wave
import numpy as np
from pipeline.speech.alignment import load_audio
def test_generated_pcm_is_resampled_to_whisper_input(tmp_path):
    path=tmp_path/'input.wav'
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(22050)
        t=np.arange(2205)/22050
        wav.writeframes((np.sin(2*np.pi*440*t)*1000).astype('<i2').tobytes())
    audio=load_audio(path)
    assert len(audio)==1600
    assert audio.dtype==np.float32
    assert np.max(np.abs(audio))<.04
