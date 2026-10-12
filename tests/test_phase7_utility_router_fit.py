import pytest
from campusai.retrieval.route_utility import FEATURE_NAMES,UtilityRouteModel
from scripts.benchmarks.learn_phase7_utility_route import fit_head


def test_fitted_model_serializes_native_numbers_and_excludes_nontraining_targets():
    vectors={str(i):{name:float(i%2) for name in FEATURE_NAMES} for i in range(12)}
    targets={str(i):bool(i%2) for i in range(12)}
    model=fit_head([str(i) for i in range(10)],vectors,targets)
    targets['10']=True;targets['11']=False
    again=fit_head([str(i) for i in range(10)],vectors,targets)
    assert model.to_dict()==again.to_dict()
    assert UtilityRouteModel.from_dict(model.to_dict()).probability(vectors['1'])>.5


def test_one_class_training_is_rejected():
    vectors={'a':dict.fromkeys(FEATURE_NAMES,0.)}
    with pytest.raises(ValueError,match='both classes'):fit_head(['a'],vectors,{'a':False})
