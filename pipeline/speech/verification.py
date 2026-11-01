"""Spelling normalization and safeguards for speech verification, without prompt bias."""
import re
from collections import Counter

def speech_tokens(text):
    # ASR cannot distinguish the apostrophe in possessive its versus it's.
    text=re.sub(r"(?<=\w)['’](?=\w)",'',text.lower())
    negatives={'dont':'do not','doesnt':'does not','didnt':'did not','isnt':'is not',
        'arent':'are not','wasnt':'was not','werent':'were not','wont':'will not',
        'wouldnt':'would not','shouldnt':'should not','couldnt':'could not',
        'cant':'can not','cannot':'can not','hasnt':'has not','havent':'have not','hadnt':'had not'}
    result=[]
    for token in re.findall(r'[a-z0-9]+',text):result.extend(negatives.get(token,token).split())
    return result

def negation_change(expected, heard):
    important={'no','not','never','without'}
    a=Counter(w for w in speech_tokens(expected) if w in important)
    b=Counter(w for w in speech_tokens(heard) if w in important)
    return a!=b
