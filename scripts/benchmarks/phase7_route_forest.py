"""Fixed shallow retrieval-only forest for isolated dev routing studies."""
from dataclasses import dataclass
import math
import struct

from campusai.retrieval.route_utility import FEATURE_NAMES


@dataclass(frozen=True)
class ForestHead:
    data: dict

    def probability(self, values):
        if set(values)!=set(FEATURE_NAMES) or not all(type(v) in (int,float) and math.isfinite(v) for v in values.values()):
            raise ValueError('invalid forest routing features')
        x=[float(values[k]) for k in FEATURE_NAMES]
        if any(abs((v-m)/s)>8 for v,m,s in zip(x,self.data['means'],self.data['scales'])):
            return None
        # sklearn trees compare float32 inputs against double thresholds.
        # Preserve that conversion when evaluating the portable JSON model.
        x=[struct.unpack('f',struct.pack('f',v))[0] for v in x]
        probabilities=[]
        for tree in self.data['trees']:
            node=0
            while tree['left'][node]!=-1:
                node=tree['left'][node] if x[tree['feature'][node]]<=tree['threshold'][node] else tree['right'][node]
            probabilities.append(tree['positive_probability'][node])
        return sum(probabilities)/len(probabilities)

    def to_dict(self):
        return self.data


def fit_forest(qids, vectors, targets):
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    labels=[int(targets[qid]) for qid in qids]
    if len(qids)!=len(set(qids)) or set(labels)!={0,1}:
        raise ValueError('unique training IDs and both classes required')
    x=np.asarray([[vectors[qid][key] for key in FEATURE_NAMES] for qid in qids],dtype=float)
    if not np.isfinite(x).all():raise ValueError('nonfinite forest training features')
    model=RandomForestClassifier(n_estimators=100,max_depth=4,min_samples_leaf=5,
        class_weight='balanced',max_features=1.,random_state=20261007,n_jobs=1)
    model.fit(x,labels)
    trees=[]
    for estimator in model.estimators_:
        t=estimator.tree_;v=t.value[:,0,:]
        trees.append({'left':t.children_left.tolist(),'right':t.children_right.tolist(),
            'feature':t.feature.tolist(),'threshold':t.threshold.tolist(),
            'positive_probability':(v[:,1]/v.sum(axis=1)).tolist()})
    data={'version':'retrieval-utility-forest-v1','feature_schema':list(FEATURE_NAMES),'input_dtype':'float32',
        'means':x.mean(axis=0).tolist(),'scales':np.maximum(x.std(axis=0),.1).tolist(),
        'parameters':{'trees':100,'max_depth':4,'min_samples_leaf':5,'seed':20261007},'trees':trees}
    head=ForestHead(data)
    for values,probability in zip(x,model.predict_proba(x)[:,1]):
        actual=head.probability(dict(zip(FEATURE_NAMES,map(float,values))))
        if actual is not None and abs(actual-float(probability))>1e-12:
            raise ValueError('exported forest does not reproduce trained probabilities')
    return head
