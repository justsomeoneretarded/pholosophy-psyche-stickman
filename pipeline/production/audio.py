"""Original procedural music and cues, synthesized in bounded blocks."""
import wave,math,subprocess
from pathlib import Path
import numpy as np
def design(timeline,episode,out,music='auto',seed=1):
    rate=22050;duration=timeline[-1]['end'];rng=np.random.default_rng(seed);events=[]
    for s,row in zip(episode.scenes,timeline):
        for a in s.actions:
            start=row['start']+a.start;end=row['start']+a.end
            if a.action in ('walk','run','sprint'):
                events.extend((float(t),'step') for t in np.arange(start,end,.425 if a.action=='walk' else .29))
            elif a.action in ('pick_up','drop','open_door','jump','land','fall','use_phone','celebrate'):events.append((start+.4,a.action))
        events.append((row['start'],'whoosh'))
    with wave.open(str(Path(out)/'sound_design.wav'),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate)
        for base in range(0,math.ceil(duration*rate),rate*5):
            count=min(rate*5,math.ceil(duration*rate)-base);t=(np.arange(count)+base)/rate;y=np.zeros(count)
            if music!='none':
                # Integrate frequency for phase continuity at chord boundaries.
                roots=[130.8128,110.,146.8324,97.9989];block=(t//12).astype(int)
                prefix=np.cumsum([0]+roots)*12
                phase=(block//4)*sum(roots)*12+prefix[block%4]+np.array(roots)[block%4]*(t%12)
                for ratio,amp in [(1,.014),(1.25,.008),(1.5,.006)]:y+=amp*np.sin(math.tau*ratio*phase)*(.7+.3*np.sin(t*.15))
                y*=np.minimum(1,t/2)*np.minimum(1,np.maximum(0,(duration-t)/3))
            for onset,kind in events:
                age=t-onset;active=(age>=0)&(age<.3)
                if not np.any(active):continue
                aa=age[active]
                if kind=='step':sound=.055*np.sin(2*np.pi*95*aa)*np.exp(-aa*55)
                elif kind=='use_phone':sound=.045*np.sin(2*np.pi*880*aa)*np.exp(-aa*12)
                elif kind=='whoosh':sound=rng.normal(0,.015,len(aa))*np.sin(np.pi*aa/.3)
                else:sound=.05*np.sin(2*np.pi*220*aa)*np.exp(-aa*25)
                y[active]+=sound
            wav.writeframes((np.clip(y,-.9,.9)*32767).astype('<i2').tobytes())
    return events
def finish(out,duration):
    out=Path(out)
    filters='[0:a]asplit=2[voice][control];[1:a][control]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=350[bed];[voice][bed]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9[a]'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(out/'narration.wav'),'-i',str(out/'sound_design.wav'),'-i',str(out/'silent.mp4'),'-filter_complex',filters,'-map','2:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(duration),'-movflags','+faststart',str(out/'video.partial.mp4')],check=True)
    (out/'video.partial.mp4').replace(out/'video.mp4')
