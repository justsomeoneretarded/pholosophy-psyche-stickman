import re,wave
from difflib import SequenceMatcher
from pathlib import Path
def tokens(text):return re.findall(r'[a-z0-9]+',text.lower())
def load_audio(path):
    import subprocess
    import numpy as np
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-ac','1','-ar','16000','pipe:1'])
    return np.frombuffer(raw,dtype='<f4').copy()
def verify(scenes,audio_dir,model='base.en',strict=True):
    from faster_whisper import WhisperModel
    import numpy as np
    whisper=WhisperModel(model,device='cpu',compute_type='int8',cpu_threads=4,num_workers=1);results=[]
    for i,s in enumerate(scenes):
        path=Path(audio_dir)/f'{i:03d}.wav'
        segments,info=whisper.transcribe(load_audio(path),language='en',word_timestamps=True,beam_size=5,vad_filter=True,condition_on_previous_text=False)
        words=[{'word':w.word.strip(),'start':w.start,'end':w.end,'probability':w.probability} for seg in segments for w in (seg.words or [])]
        heard=' '.join(w['word'] for w in words);match=SequenceMatcher(None,tokens(s.narration),tokens(heard),autojunk=False)
        agreement=match.ratio()
        differences=[{'kind':op,'expected':' '.join(tokens(s.narration)[a:b]),'heard':' '.join(tokens(heard)[c:d])} for op,a,b,c,d in match.get_opcodes() if op!='equal']
        with wave.open(str(path),'rb') as wav:data=np.frombuffer(wav.readframes(wav.getnframes()),dtype=np.int16)
        clipping=float(np.mean(np.abs(data.astype(float))>=32760))
        results.append({'scene_id':s.id,'words':words,'transcript':heard,'word_agreement':agreement,'differences':differences,'clipping_fraction':clipping,'verified':agreement>=.86 and clipping<.001})
    del whisper
    return results
def align(episode,durations,verification):
    cursor=0;timeline=[];captions=[]
    for i,(s,duration) in enumerate(zip(episode.scenes,durations)):
        original=s.duration;s.duration=duration+(.18 if i<len(episode.scenes)-1 else 0)
        words=verification[i]['words'];anchor_report=[]
        for a in s.actions:
            old_start,old_end=a.start,a.end
            a.start=old_start/original*duration;a.end=old_end/original*duration
            # Word token indices can differ from Whisper word indices; map explicitly.
            if a.anchor:
                matched=False
                flat=[];indices=[]
                for wi,word in enumerate(words):
                    ts=tokens(word['word']);flat.extend(ts);indices.extend([wi]*len(ts))
                target=tokens(a.anchor)
                for k in range(len(flat)-len(target)+1):
                    if target and flat[k:k+len(target)]==target:
                        a.start=words[indices[k]]['start'];a.end=min(duration,a.start+(old_end-old_start)/original*duration);matched=True;break
                anchor_report.append({'actor':a.actor,'phrase':a.anchor,'matched':matched,'fallback':None if matched else 'proportional_scene_timing'})
        for actor in s.characters:
            acts=sorted([a for a in s.actions if a.actor==actor],key=lambda a:a.start)
            for a,b in zip(acts,acts[1:]):
                if a.end>b.start:a.end=max(a.start+.01,b.start)
        for k in range(0,len(words),7):
            chunk=words[k:k+7];captions.append({'start':cursor+chunk[0]['start'],'end':cursor+chunk[-1]['end'],'text':' '.join(w['word'] for w in chunk)})
        timeline.append({'scene_id':s.id,'start':cursor,'end':cursor+s.duration,'speech_duration':duration,'actions':[a.model_dump() for a in s.actions],'anchors':anchor_report})
        cursor+=s.duration
    return timeline,captions
def stamp(t,separator=','):
    ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02}{separator}{ms:03}'
def subtitles(captions,out):
    out=Path(out);srt=[];vtt=['WEBVTT\n']
    for i,c in enumerate(captions):
        srt.append(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}\n")
        vtt.append(f"{stamp(c['start'],'.')} --> {stamp(c['end'],'.')}\n{c['text']}\n")
    (out/'subtitles.srt').write_text('\n'.join(srt));(out/'subtitles.vtt').write_text('\n'.join(vtt))
