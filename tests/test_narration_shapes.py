import pytest
from story.essay import beat_narration
def test_narration_objects_never_turn_into_spoken_python_dictionary_representations():
    assert beat_narration({'narration':[{'text':'Alex pauses. He considers the question.'}]})==['Alex pauses.','He considers the question.']
    with pytest.raises(ValueError,match='serialized metadata'):
        beat_narration({'narration':["{'text': 'Alex pauses.'}"]})
def test_invalid_narration_data_receives_a_clear_error_instead_of_being_spoken():
    with pytest.raises(ValueError,match='text string'):
        beat_narration({'narration':[{'who':'alex'}]})
