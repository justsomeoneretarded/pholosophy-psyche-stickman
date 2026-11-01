from story.planning import supported_location
import pytest
def test_descriptive_locations_are_mapped_without_dropping_the_scene_into_a_void():
    assert supported_location({'where':'park bench'})['where']=='park'
    assert supported_location({'where':'cafe table'})['where']=='cafe'
    assert supported_location({'where':'stage with open door'})['scene']['base']=='stage'
def test_unknown_locations_require_an_explicit_scene_instead_of_becoming_empty():
    with pytest.raises(ValueError,match='Unsupported where'):
        supported_location({'where':'unsupported place'})

def test_an_explicit_composed_scene_needs_its_environment():
    with pytest.raises(ValueError,match='scene object'):
        supported_location({'where':'scene'},require_scene=True)
