"""Probe existing free-provider access; never print credentials or authorization headers."""
import json,os
from pathlib import Path
from groq import Groq
client=Groq(api_key=os.environ['GROQ_API_KEY'],max_retries=0,timeout=35)
available=[m.id for m in client.models.list().data]
candidates=['openai/gpt-oss-120b','qwen/qwen3.8-27b','openai/gpt-oss-20b','llama-3.3-70b-versatile','llama-3.1-8b-instant']
report={'available_model_ids':available,'probes':[]}
for model in candidates:
    if model not in available:continue
    args={'model':model,'messages':[{'role':'user','content':'Return only JSON: {"ok":true}'}],
          'max_tokens':128,'response_format':{'type':'json_object'}}
    if 'gpt-oss' in model:args['extra_body']={'reasoning_effort':'low'}
    if 'qwen' in model:args['extra_body']={'reasoning_format':'hidden'}
    row={'model':model}
    try:
        raw=client.chat.completions.with_raw_response.create(**args)
        result=raw.parse()
        row.update(status='responded',finish_reason=result.choices[0].finish_reason,
                   usage=result.usage.model_dump(),
                   rate_headers={k:v for k,v in raw.headers.items() if k.lower().startswith('x-ratelimit') or k.lower()=='retry-after'})
    except Exception as exc:
        response=getattr(exc,'response',None)
        row.update(status='error',error_type=type(exc).__name__,body=getattr(exc,'body',str(exc)),
                   rate_headers={k:v for k,v in (response.headers.items() if response is not None else []) if k.lower().startswith('x-ratelimit') or k.lower()=='retry-after'})
    report['probes'].append(row)
Path('model-review').mkdir(exist_ok=True)
Path('model-review/quota.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
