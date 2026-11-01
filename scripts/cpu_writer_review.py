"""Measure two actual production planning requests on CPU; not a full-script certification."""
import json,time,os,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from pipeline.writing.llm import Writer
from story.essay import concept_prompt
from story.planning import plan_in_parts
out=Path('model-review');out.mkdir(exist_ok=True)
writer=Writer('ollama:qwen3:4b')
report={'model':'ollama:qwen3:4b','scope':'Production outline and first beat-expansion request only; not a complete script/video test',
        'cpu_count':os.cpu_count(),'memory_total':next(l.strip() for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemTotal:')),'calls':[]}
class ProbeComplete(Exception):pass
class Probe:
    specs=['ollama:qwen3:4b']
    def json(self,*args,**kwargs):
        if len(report['calls'])>=2:raise ProbeComplete()
        started=time.monotonic()
        result=writer.json(*args,**kwargs)
        stats=getattr(writer.clients.get(writer.used),'last_stats',{})
        report['calls'].append({'request':len(report['calls'])+1,'elapsed_seconds_including_any_model_setup':round(time.monotonic()-started,3),
                                'production_schema_validated':True,'inference_stats':stats})
        (out/f'response-{len(report["calls"])}.json').write_text(json.dumps(result,indent=2))
        (out/'cpu.json').write_text(json.dumps(report,indent=2))
        return result
try:
    plan_in_parts(Probe(),concept_prompt('Why We Procrastinate',4),'TOPIC: Why We Procrastinate',lambda x:x,4,out/'planning')
except ProbeComplete:
    report['status']='two production requests passed'
except Exception as exc:
    report['status']='failed';report['error']=type(exc).__name__+': '+str(exc)
    raise
finally:
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/ps',timeout=10) as response:report['loaded_models']=json.load(response)
    except Exception:pass
    (out/'cpu.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
