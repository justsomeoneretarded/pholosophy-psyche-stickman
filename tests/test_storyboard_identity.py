import pytest
from story.essay import shots_for
class Writer:
    def __init__(self,numbers):self.numbers=numbers
    def json(self,system,user,validate,**kwargs):
        return validate({'beats':[{'beat':n,'shots':[{'dur':3}]} for n in self.numbers]})
@pytest.mark.parametrize('numbers',[[1,2],[1,1]])
def test_storyboard_rejects_extra_or_duplicate_requested_beat_ids(numbers):
    with pytest.raises(ValueError,match='exactly once'):
        shots_for([{'narration':['A complete sentence.']}],0,{'cast':[]},Writer(numbers),'{}')
