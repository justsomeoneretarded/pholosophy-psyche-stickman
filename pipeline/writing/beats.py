"""Beats: the script format for noir essays, and compilation of beats into scenes.

A beat is either narrated (voice-over) or silent (music, sound and picture, with
at most one line of on-screen text). Each beat names a symbolic set piece and a
few labels; the set piece supplies staging, so the writer never choreographs.
"""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pipeline.animation import setpieces
from pipeline.models import Scene, Episode

WORDS_PER_SECOND = 2.35          # calm narration pace used to estimate narrated beats before speech exists
SetPieceName = Literal[tuple(setpieces.REGISTRY)]


class Beat(BaseModel):
    model_config = ConfigDict(extra='ignore')
    mode: Literal['narrated', 'silent']
    narration: str = Field(default='', max_length=900, description='Voice-over text, narrated beats only')
    on_screen: str = Field(default='', max_length=48, description='At most one short line shown on screen, mainly in silent beats')
    setpiece: SetPieceName
    labels: list[str] = Field(default_factory=list, max_length=5)
    tone: Literal['dark', 'light', 'auto'] = 'auto'
    amber: bool = False
    delivery: Literal['calm', 'normal', 'dramatic'] = 'calm'
    seconds: float = Field(default=8, ge=4, le=16, description='Length of a silent beat')

    @model_validator(mode='before')
    @classmethod
    def tolerate(cls, data):
        """Trim small slips (over-long lines, out-of-range lengths) instead of rejecting the whole script."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if isinstance(data.get('on_screen'), str) and len(data['on_screen']) > 48:
            words, kept = data['on_screen'].split(), []
            for w in words:
                if len(' '.join(kept + [w])) > 48:
                    break
                kept.append(w)
            while kept and kept[-1].lower().strip(',;:') in ('a', 'an', 'the', 'but', 'and', 'or', 'of', 'to', 'is', 'not', 'in'):
                kept.pop()
            data['on_screen'] = ' '.join(kept).rstrip(',;:')
        if isinstance(data.get('labels'), list):
            data['labels'] = data['labels'][:5]
        elif isinstance(data.get('labels'), str):
            data['labels'] = [data['labels']]
        try:
            data['seconds'] = max(4., min(16., float(data.get('seconds', 8) or 8)))
        except (TypeError, ValueError):
            data['seconds'] = 8.
        for key, allowed, default in (('tone', ('dark', 'light', 'auto'), 'auto'), ('delivery', ('calm', 'normal', 'dramatic'), 'calm')):
            if data.get(key) not in allowed:
                data[key] = default
        if data.get('setpiece') not in setpieces.REGISTRY:
            data['setpiece'] = setpieces.DEFAULT
        return data

    @field_validator('labels')
    @classmethod
    def short_labels(cls, v):
        return [re.sub(r'\s+', ' ', str(x)).strip()[:24] for x in v if str(x).strip()]


class Script(BaseModel):
    model_config = ConfigDict(extra='ignore')
    title: str = Field(min_length=3, max_length=120)
    thesis: str = Field(min_length=10)
    beats: list[Beat] = Field(min_length=4, max_length=60)
    youtube_titles: list[str] = Field(default_factory=list, max_length=5)
    description: str = ''
    tags: list[str] = Field(default_factory=list, max_length=30)
    pinned_comment: str = ''
    thumbnail_words: str = Field(default='', max_length=40)

    @model_validator(mode='before')
    @classmethod
    def tolerate(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            for key, n in (('youtube_titles', 5), ('tags', 30)):
                if isinstance(data.get(key), list):
                    data[key] = [str(x) for x in data[key]][:n]
            if isinstance(data.get('thumbnail_words'), str):
                data['thumbnail_words'] = data['thumbnail_words'][:40]
        return data


def estimate(beat):
    if beat.mode == 'silent':
        return float(beat.seconds)
    return max(4.0, len(beat.narration.split()) / WORDS_PER_SECOND + .8)


def compile_beat(beat, index):
    piece = setpieces.get(beat.setpiece) or setpieces.get(setpieces.DEFAULT)
    duration = round(estimate(beat), 2)
    built = piece.build(setpieces.Build(beat.labels, duration, beat.amber, beat.tone))
    narrated = beat.mode == 'narrated' and len(beat.narration.strip()) >= 15
    return Scene(
        id=f'beat_{index + 1:03d}', purpose=f'{piece.name}: {", ".join(beat.labels)}'[:200],
        narration=beat.narration.strip() if narrated else '', duration=duration,
        environment=built.get('environment', 'void'), mood='reflective', camera='static',
        characters=built.get('characters', ['main']), props=built.get('props', []), actions=built['actions'],
        text=(beat.on_screen or '').strip()[:48], transition='fade', style='noir', setpiece=piece.name,
        labels=beat.labels, amber=beat.amber, voiced=narrated, tone=beat.tone, delivery=beat.delivery)


def compile_script(script):
    scenes = [compile_beat(b, i) for i, b in enumerate(script.beats)]
    return Episode(title=script.title, thesis=script.thesis, metaphor='Symbolic set pieces',
                   framing='philosophical_exploration', scenes=scenes)
