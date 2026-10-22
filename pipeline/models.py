from typing import Literal
from pydantic import BaseModel,Field,ConfigDict,model_validator
from pipeline.animation.rig import ACTIONS
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
class Action(Strict):
    actor:str='main'
    action:str
    start:float=Field(ge=0,default=0)
    end:float=Field(gt=0)
    x:float=Field(ge=.05,le=.9,default=.35)
    target:str|None=None
    anchor:str|None=None
    @model_validator(mode='after')
    def valid(self):
        if self.action not in ACTIONS:raise ValueError('Unsupported action '+self.action)
        if self.end<=self.start:raise ValueError('Action end must follow start')
        return self
class Prop(Strict):
    id:str
    kind:Literal['phone','box','chair','desk','door','clock','book','stairs','sign','bench','cup','computer','bed','lamp','mirror','window','wall','bag','table','calendar','rope','ladder','light_switch']
    x:float=Field(ge=.05,le=.95)
    y:float=Field(ge=.1,le=.95,default=.78)
class Scene(Strict):
    id:str
    purpose:str
    narration:str=Field(min_length=15,max_length=3500)
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
    @model_validator(mode='after')
    def valid(self):
        if len(set(self.characters))!=len(self.characters):raise ValueError('Duplicate character')
        ids=[p.id for p in self.props]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate prop')
        for a in self.actions:
            if a.actor not in self.characters:raise ValueError('Unknown actor')
            if a.target and a.target not in ids:raise ValueError('Unknown prop')
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
