import pytest
from pydantic import ValidationError
from pipeline.models import Action,Scene
from pipeline.config import Config
def test_action_schema_exposes_capability_enum_to_model():
    schema=Action.model_json_schema()
    assert 'walk' in schema['$defs']['ActionKind']['enum']
    assert 'execute_python' not in schema['$defs']['ActionKind']['enum']
def test_scene_ids_cannot_be_paths():
    with pytest.raises(ValidationError):
        Scene(id='../../outside',purpose='Bad path',narration='This scene should be rejected before rendering.',duration=1,actions=[Action(action='wave',end=1)])
def test_padding_title_is_rejected():
    with pytest.raises(ValidationError):Config(title='     ')
