import wave,time
from pathlib import Path
def synthesize(scenes,out,voice_path,rate=1.):
    from piper import PiperVoice,SynthesisConfig
    voice=PiperVoice.load(str(voice_path));out=Path(out);out.mkdir(parents=True,exist_ok=True)
    durations=[];elapsed=time.monotonic()
    for i,s in enumerate(scenes):
        path=out/f'{i:03d}.wav'
        if not path.exists():
            with wave.open(str(path),'wb') as wav:voice.synthesize_wav(s.narration,wav,syn_config=SynthesisConfig(length_scale=rate))
        with wave.open(str(path),'rb') as wav:
            if wav.getnchannels()!=1 or wav.getsampwidth()!=2:raise ValueError('Expected mono 16-bit speech')
            durations.append(wav.getnframes()/wav.getframerate())
    del voice
    return durations,time.monotonic()-elapsed
def concatenate(paths,destination,pause=.18):
    with wave.open(str(destination),'wb') as target:
        for i,path in enumerate(paths):
            with wave.open(str(path),'rb') as src:
                if i==0:target.setparams(src.getparams())
                elif src.getframerate()!=target.getframerate():raise ValueError('Voice sample rate changed')
                target.writeframes(src.readframes(src.getnframes()))
                if i<len(paths)-1:target.writeframes(bytes(round(pause*src.getframerate())*2))
