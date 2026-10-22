import json,urllib.request
class Ollama:
    def __init__(self,model='qwen3:4b',url='http://127.0.0.1:11434'):self.model=model;self.url=url
    def generate(self,prompt,schema,seed=1):
        payload={'model':self.model,'prompt':prompt+'\n/no_think','stream':False,'format':schema,'keep_alive':0,'options':{'seed':seed,'temperature':.7,'num_ctx':8192,'num_predict':6500,'num_thread':4}}
        req=urllib.request.Request(self.url+'/api/generate',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=1800) as r:result=json.load(r)
        if result.get('done_reason')=='length':raise RuntimeError('Model exhausted output budget; refusing truncated story')
        return json.loads(result['response']),{k:result.get(k) for k in ('total_duration','eval_count','eval_duration','prompt_eval_count')}
