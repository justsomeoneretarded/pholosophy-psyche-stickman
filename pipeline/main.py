"""Title to validated essay, verified narration, articulated animation and publishing files."""
import argparse,json,os,time,traceback
from pathlib import Path
from pipeline.config import Config
from pipeline.models import Episode
from pipeline.writing.research import research
from pipeline.writing.story import create,originality
from pipeline.writing.quality import assess
from pipeline.speech.tts import synthesize,concatenate
from pipeline.speech.alignment import verify,align,subtitles
from pipeline.production.render import render,thumbnail
from pipeline.production.audio import design,finish
from pipeline.production.quality import motion_checks,inspect
from pipeline.production.director import prepare
from pipeline.publishing import package,upload
def save(path,data):Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False))
def run(config,out,story=None,whisper_model='base.en',voice_path=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);started=time.monotonic();manifest=out/'config.json'
    if manifest.exists() and json.loads(manifest.read_text())!=config.model_dump():raise ValueError('Output directory has different configuration; choose a new directory')
    save(manifest,config.model_dump());metrics=[]
    (out/'SUCCESS.json').unlink(missing_ok=True)
    if story:
        episode=Episode.model_validate_json(Path(story).read_text());sources,warnings=research(config.title)
    elif (out/'storyboard.original.json').exists():
        episode=Episode.model_validate_json((out/'storyboard.original.json').read_text());sources=json.loads((out/'sources.json').read_text());warnings=['Resumed validated storyboard']
    else:
        sources,warnings=research(config.title);save(out/'sources.json',sources)
        episode,metrics=create(config.title,config.duration_minutes,sources,config.seed,config.style,os.environ.get('OLLAMA_MODEL','qwen3:4b'),checkpoint_dir=out/'writing_checkpoints')
    if episode.title!=config.title:raise ValueError('Storyboard title differs from requested title')
    repairs=prepare(episode,config.size);save(out/'scene_repairs.json',repairs)
    save(out/'storyboard.original.json',episode.model_dump());save(out/'sources.json',sources)
    (out/'research_notes.md').write_text('# Research notes\n\n'+'\n\n'.join(warnings))
    save(out/'claims.json',{'framing':episode.framing,'claims_verified':False,'policy':'No precise empirical claims or attributed quotations are authorized by metadata alone.','review_required':True})
    (out/'script.txt').write_text('\n\n'.join(s.narration for s in episode.scenes))
    content=assess(episode);save(out/'content_report.json',content)
    if not content['passed']:raise ValueError('Content QA failed: '+str(content['failures']))
    history_path,history_record=originality(episode,os.environ.get('STUDIO_HISTORY','.cache/history'))
    voice_path=Path(voice_path or os.environ.get('PIPER_VOICE','.cache/voices/en_US-ljspeech-high.onnx'))
    if config.voice=='custom' and os.environ.get('CUSTOM_VOICE_AUTHORIZED')!='true':raise ValueError('Custom voice needs CUSTOM_VOICE_AUTHORIZED=true and a permitted Piper ONNX model. Audio cloning is not implemented.')
    speech_dir=out/'speech';durations,speech_seconds=synthesize(episode.scenes,speech_dir,voice_path)
    measured=sum(durations)+.18*(len(durations)-1);target=config.duration_minutes*60
    if abs(measured-target)/target>.22 and not story:
        observed_rate=sum(len(s.narration.split()) for s in episode.scenes)/max(.01,sum(durations))*60
        print(f'Rewriting to measured narrator rate: {observed_rate:.1f} words/minute',flush=True)
        episode,extra=create(config.title,config.duration_minutes,sources,config.seed,config.style,os.environ.get('OLLAMA_MODEL','qwen3:4b'),words_per_minute=observed_rate,checkpoint_dir=out/'writing_checkpoints')
        metrics.extend(extra)
        repairs=prepare(episode,config.size);save(out/'scene_repairs.json',repairs)
        content=assess(episode);save(out/'content_report.json',content)
        if not content['passed']:raise ValueError('Rewritten content QA failed: '+str(content['failures']))
        save(out/'storyboard.original.json',episode.model_dump())
        (out/'script.txt').write_text('\n\n'.join(s.narration for s in episode.scenes))
        history_path,history_record=originality(episode,os.environ.get('STUDIO_HISTORY','.cache/history'))
        durations,extra_seconds=synthesize(episode.scenes,speech_dir,voice_path);speech_seconds+=extra_seconds
    print('Verifying narration with Whisper CPU INT8',flush=True)
    verification=verify(episode.scenes,speech_dir,whisper_model);save(out/'speech_verification.json',verification)
    defective=[i for i,v in enumerate(verification) if not v['verified']]
    if defective:
        # One bounded regeneration retry; no unchecked speech is silently accepted.
        for i in defective:(speech_dir/f'{i:03d}.wav').unlink()
        durations,retry_seconds=synthesize(episode.scenes,speech_dir,voice_path,rate=1.04);speech_seconds+=retry_seconds
        verification=verify(episode.scenes,speech_dir,whisper_model);save(out/'speech_verification.json',verification)
        if any(not v['verified'] for v in verification):raise ValueError('Speech verification failed after regeneration; inspect speech_verification.json')
    measured=sum(durations)+.18*(len(durations)-1);target=config.duration_minutes*60
    if abs(measured-target)/target>.22:raise ValueError(f'Measured narration {measured:.1f}s outside 22% target tolerance ({target:.1f}s); no audio stretching applied')
    concatenate([speech_dir/f'{i:03d}.wav' for i in range(len(episode.scenes))],out/'narration.wav')
    timeline,captions=align(episode,durations,verification);save(out/'scene_timeline.json',timeline);save(out/'storyboard.json',episode.model_dump());save(out/'captions.json',captions);subtitles(captions,out)
    motion=motion_checks(episode,config.size);save(out/'motion_report.json',motion)
    if not motion['passed']:raise ValueError('Motion QA failed: '+str(motion['issues'][:5]))
    bench=render(episode,timeline,captions,out,config.size,30,config.quality)
    events=design(timeline,episode,out,config.music,config.seed);save(out/'sound_cues.json',events)
    finish(out,timeline[-1]['end']);thumbnail(episode,out);package(episode,timeline,sources,out)
    save(out/'audio_licenses.json',{'music':'Original procedural synthesis, GPL-3.0-or-later','effects':'Original procedural synthesis, GPL-3.0-or-later','narration':{'engine':'Piper GPL-3.0-or-later','voice':str(voice_path),'model_card':'https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/high/MODEL_CARD','dataset_license':'LJ Speech dataset is public domain; see downloaded model card'}})
    qa=inspect(out,config.size,30,target);qa['motion']=motion;qa['speech_verified']=all(v['verified'] for v in verification);qa['artistic_quality']='Requires editorial review, no artistic numerical score';save(out/'quality_report.json',qa)
    report={'elapsed_seconds':time.monotonic()-started,'speech_seconds':speech_seconds,'render':bench,'model_metrics':metrics,'warnings':warnings,'limitations':['Metadata retrieval is not full-text fact checking','Chatterbox not benchmarked','Advanced object interactions are experimental','No audio voice cloning','No monetization guarantee']}
    save(out/'production_metrics.json',report);(out/'production_report.md').write_text('# Production report\n\n'+json.dumps(report,indent=2)+'\n\nTechnical QA passed: '+str(qa['passed']))
    if not qa['passed']:raise ValueError('Technical QA failed: '+str(qa['issues']))
    history_path.write_text(json.dumps(history_record))
    if config.upload_to_youtube:upload(out)
    save(out/'SUCCESS.json',{'status':'complete','duration':qa['duration_seconds']})
    print(json.dumps({'status':'complete','output':str(out),'duration':measured,'benchmark':bench}),flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--title');parser.add_argument('--minutes',type=float,default=6);parser.add_argument('--out',default='outputs/video');parser.add_argument('--storyboard');parser.add_argument('--whisper-model',default='base.en');parser.add_argument('--voice-path');args=parser.parse_args()
    config=Config.environment() if 'STUDIO_INPUTS' in os.environ else Config(title=args.title,duration_minutes=args.minutes)
    try:run(config,args.out,args.storyboard,args.whisper_model,args.voice_path)
    except Exception:
        Path(args.out).mkdir(parents=True,exist_ok=True);(Path(args.out)/'FAILURE.txt').write_text(traceback.format_exc());raise
if __name__=='__main__':main()
