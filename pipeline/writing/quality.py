"""Conservative content gates. These do not pretend to measure artistic quality."""
import re
STOP=set('the a an why what if how do does is are we you people so much everything really'.split())
def assess(episode):
    failures=[];warnings=[];text=' '.join(s.narration for s in episode.scenes)
    topic=set(re.findall(r'[a-z]+',episode.title.lower()))-STOP
    spoken=set(re.findall(r'[a-z]+',text.lower()))
    if topic and not topic&spoken:warnings.append('Title keywords are absent from narration; review whether the argument addresses the question')
    if re.search(r'\b\d+(?:\.\d+)?\s*(?:%|percent|per cent)\b',text,re.I):
        failures.append('Precise numerical psychology claim requires verified source evidence, not bibliography metadata')
    if re.search(r'\b(?:studies|research|scientists|psychologists)\s+(?:prove|proved|show|shows|found|demonstrate)',text,re.I):
        failures.append('Empirical finding asserted without a verified claim-to-source record')
    if re.search(r'\b(?:Nietzsche|Seneca|Marcus Aurelius|Socrates|Aristotle|Plato|Camus)\s+(?:said|wrote|once said)[,:]?\s*[\"“]',text,re.I):
        failures.append('Attributed quotation needs a verified original source')
    if re.search(r'\byou\s+(?:have|must have|suffer from)\s+(?:ADHD|depression|a personality disorder|an anxiety disorder)\b',text,re.I):
        failures.append('Narration diagnoses the viewer')
    sentences=[s.strip().lower() for s in re.split(r'[.!?]+',text) if len(s.split())>6]
    repeated=sorted({s for s in sentences if sentences.count(s)>1})
    if repeated:failures.append('Repeated full narration sentences: '+str(repeated[:3]))
    for s in episode.scenes:
        if all(a.action=='idle' for a in s.actions):failures.append(s.id+': no meaningful character acting')
        if not s.purpose.strip():failures.append(s.id+': missing narrative purpose')
        for a in s.actions:
            if a.anchor and a.anchor.casefold() not in s.narration.casefold():warnings.append(s.id+': anchor phrase not present in script: '+a.anchor)
    warnings.append('Coherence, nuance, originality of argument and visual meaning still require editorial judgment')
    return {'passed':not failures,'failures':failures,'warnings':warnings,'framing':episode.framing}
