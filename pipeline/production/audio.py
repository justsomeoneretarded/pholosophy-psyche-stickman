"""Original procedural music and cues, synthesized in bounded blocks."""
import wave,math,subprocess
from pathlib import Path
import numpy as np
def cue_events(timeline,episode,size=(1920,1080)):
    """Sound events from the planned performance, including automatic walking."""
    from pipeline.animation.scene import character_scale
    from pipeline.animation.acting import plan_for
    from pipeline.animation.rig import LOCOMOTION
    scale=character_scale(size);ww=size[0]/scale;events=[]
    single={'open_door':('door',.45),'leave':None,'flip_switch':('click',.5),'pick_up':('tap',.45),'put_down':('tap',.5),
            'use_phone':('beep',.6),'celebrate':('pop',.1),'high_five':('clap',.45),'clap':None,'jump':('thud',.85),
            'fall':('thud',.6),'drop':('thud',.55),'push':('thud',.3),'flinch':('pop',.05),'hug':('soft',.3),'type':None}
    for s,row in zip(episode.scenes,timeline):
        plan=plan_for(s,ww)
        for actor,segs in plan.tracks.items():
            for g in segs:
                if g.t0>=s.duration:break
                start=row['start']+g.t0;end=row['start']+min(g.t1,s.duration)
                if g.kind=='_move' or g.kind in LOCOMOTION:
                    travel=g.params.get('travel',g.t1-g.t0);speed=g.params.get('speed',.55)
                    step=.44/max(.2,speed)/2 if speed<1.1 else .78/max(.2,speed)/2
                    events.extend((float(t),'step') for t in np.arange(start+.15,min(end,start+travel),max(.16,step)))
                elif g.kind=='clap':
                    events.extend((float(t),'clap') for t in np.arange(start+.3,end,.35))
                elif g.kind=='type':
                    events.extend((float(t),'tap') for t in np.arange(start+.8,end,.13))
                elif single.get(g.kind):
                    kind,at=single[g.kind];events.append((start+min(at,max(.05,end-start-.05)),kind))
        events.append((row['start'],'whoosh'))
    return sorted(events)
def design(timeline,episode,out,music='auto',seed=1):
    rate=22050;duration=timeline[-1]['end'];rng=np.random.default_rng(seed)
    events=cue_events(timeline,episode)
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
                if kind=='step':sound=.05*np.sin(2*np.pi*95*aa)*np.exp(-aa*55)+.012*rng.normal(0,1,len(aa))*np.exp(-aa*80)
                elif kind=='beep':sound=.04*np.sin(2*np.pi*880*aa)*np.exp(-aa*12)
                elif kind=='whoosh':sound=rng.normal(0,.015,len(aa))*np.sin(np.pi*np.minimum(aa,.3)/.3)
                elif kind=='door':sound=.035*np.sin(2*np.pi*(180+500*aa)*aa)*np.exp(-aa*6)
                elif kind=='click':sound=.06*rng.normal(0,1,len(aa))*np.exp(-aa*400)
                elif kind=='clap':sound=.09*rng.normal(0,1,len(aa))*np.exp(-aa*60)
                elif kind=='tap':sound=.03*np.sin(2*np.pi*1400*aa)*np.exp(-aa*150)
                elif kind=='thud':sound=.09*np.sin(2*np.pi*60*aa)*np.exp(-aa*18)
                elif kind=='pop':sound=.05*np.sin(2*np.pi*(600-900*aa)*aa)*np.exp(-aa*20)
                elif kind=='soft':sound=.02*np.sin(2*np.pi*330*aa)*np.sin(np.pi*np.minimum(aa,.3)/.3)
                else:sound=.04*np.sin(2*np.pi*220*aa)*np.exp(-aa*25)
                y[active]+=sound
            wav.writeframes((np.clip(y,-.9,.9)*32767).astype('<i2').tobytes())
    return events
def finish(out,duration):
    out=Path(out)
    filters='[0:a]asplit=2[voice][control];[1:a][control]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=350[bed];[voice][bed]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9[a]'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(out/'narration.wav'),'-i',str(out/'sound_design.wav'),'-i',str(out/'silent.mp4'),'-filter_complex',filters,'-map','2:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(duration),'-movflags','+faststart',str(out/'video.partial.mp4')],check=True)
    (out/'video.partial.mp4').replace(out/'video.mp4')
