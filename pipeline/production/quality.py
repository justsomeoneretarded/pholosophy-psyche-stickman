import math,subprocess
from pathlib import Path
import numpy as np
from pipeline.animation.scene import actor_pose,character_scale
from pipeline.animation.rig import BONES
from pipeline.production.render import probe
def motion_checks(episode,size=(1920,1080)):
    w,h=size;scale=character_scale(size);world_width=w/scale;world_height=h/scale
    issues=[];stats={'samples':0,'max_joint_step':0.,'max_floor_penetration':0.}
    for s in episode.scenes:
        for actor in s.characters:
            previous=None
            for t in np.arange(0,s.duration,1/30):
                p,a=actor_pose(s,actor,float(t),world_width,world_height);j=p.joints;stats['samples']+=1
                if any(not math.isfinite(v) for pos in j.values() for v in pos):issues.append(f'{s.id}: nonfinite joint')
                for aa,bb in BONES:
                    if math.dist(j[aa],j[bb])>.52:issues.append(f'{s.id}: disconnected limb')
                penetration=max(j['left_foot'][1],j['right_foot'][1]);stats['max_floor_penetration']=max(stats['max_floor_penetration'],penetration)
                if penetration>.025:issues.append(f'{s.id}: foot penetrates floor')
                if previous:
                    delta=max(math.dist(j[k],previous[k]) for k in j);stats['max_joint_step']=max(stats['max_joint_step'],delta)
                    if delta>.25:issues.append(f'{s.id}/{actor}: abrupt joint motion at {t:.2f}')
                if not .02<=j['hip'][0]/world_width<=.97:issues.append(f'{s.id}/{actor}: actor outside safe frame')
                previous=j
    return {'passed':not issues,'issues':sorted(set(issues))[:100],'statistics':stats}
def visual_samples(path):
    """Bounded low-resolution diagnostic samples; never a substitute for visual review."""
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf','fps=1/2,scale=160:90,format=gray','-f','rawvideo','pipe:1'])
    if not raw:return {'sample_count':0,'all_blank':True,'blank_samples':[],'near_static_pairs':[]}
    frames=np.frombuffer(raw,dtype=np.uint8).reshape(-1,90,160).astype(float)
    blank=[i*2 for i,f in enumerate(frames) if float(np.std(f))<1.]
    still=[i*2 for i in range(1,len(frames)) if float(np.mean(np.abs(frames[i]-frames[i-1])))<.02]
    return {'sample_count':len(frames),'all_blank':len(blank)==len(frames),'blank_samples':blank,'near_static_pairs':still,'interpretation':'Near-static pairs are review warnings; a deliberate held pose is not automatically a failure.'}
def audio_levels(path):
    import re
    result=subprocess.run(['ffmpeg','-v','info','-i',str(path),'-vn','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True,check=True)
    tail=result.stderr[-2500:]
    loud=re.findall(r'I:\s*(-?\d+(?:\.\d+)?) LUFS',tail)
    peak=re.findall(r'Peak:\s*(-?\d+(?:\.\d+)?) dBFS',tail)
    return {'integrated_lufs':float(loud[-1]) if loud else None,'true_peak_dbfs':float(peak[-1]) if peak else None}
def inspect(out,size,fps,target,tolerance=.22):
    out=Path(out);data=probe(out/'video.mp4')
    v=next(s for s in data['streams'] if s['codec_type']=='video');a=next(s for s in data['streams'] if s['codec_type']=='audio')
    duration=float(data['format']['duration']);issues=[]
    if (v['width'],v['height'])!=size:issues.append('Wrong resolution')
    if v['codec_name']!='h264' or a['codec_name']!='aac':issues.append('Wrong codecs')
    numerator,denominator=map(float,v['avg_frame_rate'].split('/'))
    if abs(numerator/denominator-fps)>.01:issues.append('Wrong FPS')
    if abs(duration-target)>target*tolerance:issues.append(f'Duration {duration:.2f}s outside target {target:.2f}s tolerance')
    subprocess.run(['ffmpeg','-v','error','-i',str(out/'video.mp4'),'-f','null','-'],check=True)
    visual=visual_samples(out/'video.mp4');levels=audio_levels(out/'video.mp4')
    if visual['all_blank']:issues.append('Decoded visual samples contain no visible content')
    if levels['true_peak_dbfs'] is not None and levels['true_peak_dbfs']>=-.1:issues.append('Final mix true peak is too close to clipping')
    for name in ['video.mp4','thumbnail.png','script.txt','storyboard.json','narration.wav','subtitles.srt','subtitles.vtt','sources.json','claims.json','youtube_description.txt']:
        if not (out/name).is_file() or not (out/name).stat().st_size:issues.append('Missing output '+name)
    return {'passed':not issues,'issues':issues,'duration_seconds':duration,'video':v,'audio':a,'full_decode':'passed','visual_samples':visual,'audio_levels':levels}
