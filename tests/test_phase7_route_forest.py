import json
import pytest
from campusai.retrieval.route_utility import FEATURE_NAMES
from scripts.benchmarks.phase7_route_forest import ForestHead,fit_forest


def test_training_targets_outside_explicit_training_ids_do_not_change_forest():
    ids=[f'q{i}' for i in range(40)]
    vectors={qid:{k:float((i+j)%7)/7 for j,k in enumerate(FEATURE_NAMES)} for i,qid in enumerate(ids)}
    targets={qid:i%2 for i,qid in enumerate(ids)}
    first=fit_forest(ids,vectors,targets).to_dict()
    targets['heldout']=True
    vectors['heldout']={k:999. for k in FEATURE_NAMES}
    second=fit_forest(ids,vectors,targets).to_dict()
    assert first==second
    restored=ForestHead(json.loads(json.dumps(first,allow_nan=False)))
    assert restored.probability(vectors['heldout']) is None
    assert restored.probability(vectors['q0'])==ForestHead(first).probability(vectors['q0'])
    with pytest.raises(ValueError):restored.probability({**vectors['q0'],'gold':True})
