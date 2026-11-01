"""Map the original caption words to ASR anchors without replacing the script."""
import re
from difflib import SequenceMatcher

def align_caption_words(text, recognized, duration):
    original=text.split()
    if not original:return []
    normalize=lambda s:re.findall(r'[a-z0-9]+',s.lower())
    expected=[];expected_index=[]
    for i,word in enumerate(original):
        tokens=normalize(word);expected.extend(tokens);expected_index.extend([i]*len(tokens))
    heard=[];heard_index=[]
    for i,word in enumerate(recognized):
        tokens=normalize(word['word']);heard.extend(tokens);heard_index.extend([i]*len(tokens))
    anchors={}
    for block in SequenceMatcher(None,expected,heard,autojunk=False).get_matching_blocks():
        for offset in range(block.size):
            oi=expected_index[block.a+offset];rec=recognized[heard_index[block.b+offset]]
            lo,hi=anchors.get(oi,(rec['start'],rec['end']))
            anchors[oi]=(min(lo,rec['start']),max(hi,rec['end']))
    result=[]
    for i,word in enumerate(original):
        if i in anchors:
            start,end=anchors[i];source='whisper'
        else:
            before=max((k for k in anchors if k<i),default=None)
            after=min((k for k in anchors if k>i),default=None)
            left=anchors[before][1] if before is not None else 0.
            right=anchors[after][0] if after is not None else duration
            left_index=before+1 if before is not None else 0
            right_index=after if after is not None else len(original)
            count=max(1,right_index-left_index)
            start=left+(right-left)*(i-left_index)/count
            end=left+(right-left)*(i-left_index+1)/count
            source='estimated_between_anchors'
        start=max(0.,min(duration,float(start)));end=max(start,min(duration,float(end)))
        result.append({'word':word,'start':round(start,3),'end':round(end,3),'timing_source':source})
    return result
