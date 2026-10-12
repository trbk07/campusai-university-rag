from dataclasses import replace
import pytest

from campusai.retrieval.source_context_inputs import contextual_pool
from campusai.retrieval.cross_encoder_provider import ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256


def item(chunk, section, content, doc='a', page=1, kind='text'):
    return {'chunk_id':chunk,'doc_id':doc,'page':page,'content':content,'content_type':kind,
            'metadata':{'section_index':section}}


def test_context_uses_only_same_document_page_scoped_pool_and_preserves_evidence():
    pool=[item('total-label',1,'Total curriculum credits:'),item('value',2,'155'),
          item('other-document',1,'WRONG DOCUMENT','b'),item('other-page',1,'WRONG PAGE',page=2)]
    out=contextual_pool(pool)[1]
    assert out['content']=='155' and out['chunk_id']=='value'
    assert 'Total curriculum credits:' in out['scoring_content']
    assert 'WRONG' not in out['scoring_content']
    assert [x['chunk_id'] for x in out['scoring_context_sources']]==['total-label']


def test_context_never_modifies_tables_or_reads_a_missing_neighbor():
    table=item('table',2,'original table',kind='table')
    assert contextual_pool([table])[0]['scoring_content']==table['content']
    assert contextual_pool([item('isolated',5,'original')])[0]['scoring_context_sources']==[]


def test_duplicate_candidate_coordinates_fail_closed():
    a=item('same',1,'body')
    with pytest.raises(ValueError):contextual_pool([a,a])


def test_provider_cache_binds_context_while_returning_original_coordinates(tmp_path):
    (tmp_path/'config.json').write_text('{}')
    identity=ModelIdentity('BAAI/bge-reranker-v2-m3',tmp_path.name,snapshot_sha256(tmp_path),tmp_path.name,input_format='source_context')
    observed=[]
    class Model:
        def predict(self,pairs,**_kwargs):
            observed.extend(pairs)
            return [float(len(text)) for _q,text in pairs]
    provider=OfflineCrossEncoderReranker(identity,tmp_path,model_loader=lambda:Model(),score_cache_size=8)
    a=RerankCandidate('id','doc','id',2,'original evidence',1,.9,'155\nTotal credits')
    try:
        first=provider.score('total?', [a])[0]
        provider.score('total?', [a])
        provider.score('total?', [replace(a,scoring_content='155\nDifferent source context')])
        assert len(observed)==2
        assert first.chunk_id=='id' and first.page==2
        assert observed[0][1]=='155\nTotal credits'
    finally:provider.close()
