"""Cheap retrieval-only features for a separately evaluated utility router.

Cross-encoder logits, qids, source identities, pages and labels never enter
inference. The historical hard-query model remains a separate component.
"""
from dataclasses import dataclass, asdict
import math

from .learned_rank_features import FEATURE_NAMES as RANK_NAMES, features
from .route_probability import route_observations

VERSION='retrieval-utility-logistic-v1'
INDICES=(4,5,6,7,9,10,11,12,13,14,15,16,17,18)
FEATURE_NAMES=('operation_required','long_request',*(RANK_NAMES[i] for i in INDICES),
               'retrieval_score_margin','alternative_body_overlap_gap')


def utility_features(query, baseline, pool):
    if not baseline or not pool:
        raise ValueError('utility routing requires actual nonempty retrieval')
    first=features(query,baseline[0],0.,1,1)
    old=route_observations(query,baseline)
    scores=[float(item['score']) for item in baseline[:2]]
    if not all(math.isfinite(score) for score in scores):
        raise ValueError('nonfinite retrieval score')
    margin=(scores[0]-scores[1])/max(abs(scores[0]),1e-6) if len(scores)>1 else 1.
    alternative=max(features(query,item,0.,0,i+1)[4] for i,item in enumerate(pool[:20]))
    values=[old['operation_required'],old['long_request'],*(first[i] for i in INDICES),
            max(-1.,min(1.,margin)),alternative-first[4]]
    return dict(zip(FEATURE_NAMES,values))


@dataclass(frozen=True)
class UtilityRouteModel:
    version:str
    feature_schema:tuple
    means:tuple
    scales:tuple
    weights:tuple
    bias:float
    max_standardized_distance:float=8.

    def __post_init__(self):
        if (self.version!=VERSION or tuple(self.feature_schema)!=FEATURE_NAMES
                or any(len(x)!=len(FEATURE_NAMES) for x in (self.means,self.scales,self.weights))
                or not all(type(x) in (int,float) and math.isfinite(x) for x in
                           (*self.means,*self.scales,*self.weights,self.bias,self.max_standardized_distance))
                or min(self.scales)<.1 or not 1<=self.max_standardized_distance<=8):
            raise ValueError('invalid utility route model')

    def probability(self,values):
        if (set(values)!=set(FEATURE_NAMES) or not all(type(v) in (int,float) and math.isfinite(v) for v in values.values())):
            raise ValueError('invalid utility routing features')
        x=[(values[key]-mean)/scale for key,mean,scale in zip(FEATURE_NAMES,self.means,self.scales)]
        if any(abs(v)>self.max_standardized_distance for v in x):
            return None
        logit=self.bias+sum(w*v for w,v in zip(self.weights,x))
        return 1./(1.+math.exp(-max(-40.,min(40.,logit))))

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls,data):
        if set(data)!=set(cls.__dataclass_fields__):raise ValueError('invalid utility model fields')
        return cls(**{k:tuple(v) if k in ('feature_schema','means','scales','weights') else v for k,v in data.items()})
