"""Routing is observable before any CE call and independent of source IDs."""
import copy
import pytest
from campusai.retrieval.route_utility import utility_features,UtilityRouteModel,FEATURE_NAMES,VERSION


def item(name,content,score):
    return {'chunk_id':name,'doc_id':'d','page':1,'content':content,'content_type':'text',
            'score':score,'metadata':{'heading_path':['Registration']}}


def test_source_identity_and_gold_cannot_change_routing_features():
    pool=[item('a','Registration closes on 12 October.',.8),item('b','Registration opens in September.',.7)]
    before=utility_features('When does registration close?',pool,pool)
    changed=copy.deepcopy(pool)
    for record in changed:
        record.update(chunk_id='unrelated-id',doc_id='another-doc',page=999,
                      gold=True,difficulty='hard',ce_logit=100.)
    assert utility_features('When does registration close?',changed,changed)==before


def test_rejects_corrupt_scores_and_unobservable_inputs():
    pool=[item('a','Registration closes in October.',float('nan'))]
    with pytest.raises(ValueError):utility_features('When does registration close?',pool,pool)
    with pytest.raises(ValueError):utility_features('When?',[],[])


def test_utility_model_roundtrip_and_out_of_domain_fallback():
    model=UtilityRouteModel(VERSION,FEATURE_NAMES,(0.,)*len(FEATURE_NAMES),
        (1.,)*len(FEATURE_NAMES),(1.,)*len(FEATURE_NAMES),0.)
    values=dict.fromkeys(FEATURE_NAMES,0.)
    assert UtilityRouteModel.from_dict(model.to_dict()).probability(values)==.5
    values[FEATURE_NAMES[0]]=9.
    assert model.probability(values) is None
