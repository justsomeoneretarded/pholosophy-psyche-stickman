from typing import Literal
from enum import StrEnum
from pydantic import BaseModel,Field,ConfigDict,model_validator
from pipeline.animation.rig import ACTIONS, EMOTIONS
ActionKind=StrEnum('ActionKind',{name:name for name in ACTIONS})
EmotionKind=StrEnum('EmotionKind',{name:name for name in EMOTIONS})
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
class Action(Strict):
    actor:Literal['main','friend','shadow','future']='main'
    action:ActionKind
    start:float=Field(ge=0,default=0)
    end:float=Field(gt=0)
    x:float|None=Field(ge=.05,le=.95,default=None,description='Stage position (0 left .. 1 right) to move to before acting; omit to stay or to walk to the target automatically')
    target:str|None=Field(default=None,description='A declared prop id or another character to act on or with')
    emotion:EmotionKind|None=Field(default=None,description='Emotion shown from this action onward')
    anchor:str|None=None
    @model_validator(mode='after')
    def valid(self):
        if self.end<=self.start:raise ValueError('Action end must follow start')
        return self
class Prop(Strict):
    id:str=Field(pattern=r'^[A-Za-z][A-Za-z0-9_]{0,47}$')
    kind:Literal['phone','box','chair','desk','door','clock','book','stairs','sign','bench','cup','computer','bed','lamp','mirror','window','wall','bag','table','calendar','rope','ladder','light_switch','sofa','plant','tv','rock']
    x:float=Field(ge=.05,le=.95)
    y:float=Field(ge=.1,le=.95,default=.78)
class Scene(Strict):
    id:str=Field(pattern=r'^[A-Za-z][A-Za-z0-9_]{0,47}$')
    purpose:str
    narration:str=Field(default='',max_length=3500)
    duration:float=Field(gt=0,le=90)
    environment:Literal['bedroom','classroom','office','street','park','living_room','cafe','library','hallway','city','void','stage','mindscape','staircase','crossroads','gathering','empty_room','hill','nature']='stage'
    mood:Literal['reflective','hopeful','tense','sad','playful']='reflective'
    camera:Literal['static','push_in','pull_out','pan','track','shake']='static'
    characters:list[Literal['main','friend','shadow','future']]=Field(default_factory=lambda:['main'],min_length=1,max_length=4)
    props:list[Prop]=Field(default_factory=list,max_length=12)
    actions:list[Action]=Field(min_length=1,max_length=30)
    symbol:Literal['none','thought','loop','maze','doors','waves','balance','memory','chains','decision_tree','circles']='none'
    text:str=Field(default='',max_length=55)
    transition:Literal['fade','cut']='fade'
    style:Literal['classic','noir']='classic'
    setpiece:str|None=Field(default=None,pattern=r'^[a-z_]{2,40}$')
    labels:list[str]=Field(default_factory=list,max_length=6)
    amber:bool=False
    voiced:bool=True
    tone:Literal['auto','dark','light']='auto'
    delivery:Literal['calm','normal','dramatic']='calm'
    @model_validator(mode='after')
    def valid(self):
        if len(set(self.characters))!=len(self.characters):raise ValueError('Duplicate character')
        if self.voiced and len(self.narration.strip())<15:raise ValueError('Narrated scenes need at least 15 characters of narration')
        if any(len(l)>24 for l in self.labels):raise ValueError('Labels must be short (24 characters or fewer)')
        ids=[p.id for p in self.props]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate prop')
        for a in self.actions:
            if a.actor not in self.characters:raise ValueError('Unknown actor')
            if a.target and a.target not in ids and a.target not in self.characters:raise ValueError(f'Unknown target {a.target!r}; declared prop IDs are {ids!r} and characters are {self.characters!r}')
            if a.target==a.actor:raise ValueError('An actor cannot target themselves')
            if a.end>self.duration+.01:raise ValueError('Action outside scene')
        for actor in self.characters:
            acts=sorted([a for a in self.actions if a.actor==actor],key=lambda a:a.start)
            if any(a.end>b.start for a,b in zip(acts,acts[1:])):raise ValueError('Overlapping actor actions')
        return self
class Episode(Strict):
    title:str=Field(min_length=3,max_length=180)
    thesis:str=Field(min_length=20)
    metaphor:str=Field(min_length=10)
    framing:Literal['research_grounded','philosophical_exploration']
    scenes:list[Scene]=Field(min_length=2,max_length=90)
    @model_validator(mode='after')
    def valid(self):
        if len({s.id for s in self.scenes})!=len(self.scenes):raise ValueError('Duplicate scene')
        return self
