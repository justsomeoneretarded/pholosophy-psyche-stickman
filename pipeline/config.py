import os,json
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict,field_validator
class Config(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=3,max_length=180)
    duration_minutes:float=Field(default=6,ge=.5,le=10)
    style:Literal['auto','minimalist','cinematic','humorous','dark-philosophical']='auto'
    voice:Literal['auto','custom']='auto'
    format:Literal['16:9','9:16']='16:9'
    quality:Literal['standard','high']='high'
    music:Literal['auto','ambient','cinematic','none']='auto'
    seed:int=Field(default=42,ge=0,le=2147483647)
    upload_to_youtube:bool=False
    @field_validator('title')
    @classmethod
    def clean(cls,v):
        if any(ord(c)<32 for c in v):raise ValueError('Title cannot contain control characters')
        v=v.strip()
        if len(v)<3:raise ValueError('Title must contain at least three non-padding characters')
        return v
    @property
    def size(self):return (1920,1080) if self.format=='16:9' else (1080,1920)
    @classmethod
    def environment(cls):
        data=json.loads(os.environ.get('STUDIO_INPUTS','{}'))
        if not data.get('seed'):data['seed']=42
        return cls.model_validate(data)
