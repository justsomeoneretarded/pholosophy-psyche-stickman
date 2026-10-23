import wave,time,hashlib,json
from pathlib import Path
def synthesize(scenes,out,voice_path,rate=1.):
    from piper import PiperVoice,SynthesisConfig
    voice_path=Path(voice_path);voice=PiperVoice.load(str(voice_path));out=Path(out);out.mkdir(parents=True,exist_ok=True)
    durations=[];elapsed=time.monotonic()
    for i,s in enumerate(scenes):
        path=out/f'{i:03d}.wav';marker=path.with_suffix('.sha256')
        signature=hashlib.sha256(json.dumps([s.narration,str(voice_path.resolve()),voice_path.stat().st_size,voice_path.stat().st_mtime_ns,rate]).encode()).hexdigest()
        if not path.exists() or not marker.exists() or marker.read_text()!=signature:
            temporary=path.with_suffix('.partial.wav')
            with wave.open(str(temporary),'wb') as wav:voice.synthesize_wav(s.narration,wav,syn_config=SynthesisConfig(length_scale=rate))
            temporary.replace(path);marker.write_text(signature)
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
