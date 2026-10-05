"""Failed acceptance consumes exact input bytes without certifying a passing gate."""
from copy import deepcopy
import json

import pytest

from evaluation.common.release_artifacts import sha256
from scripts.benchmarks.create_phase7_fresh_cycle import measured_dev_qids
from scripts.benchmarks.measure_phase7_dev_candidates import dev_rows


def exposure_fixture(tmp_path):
    dataset = tmp_path / 'human_retrieval_dev.jsonl'
    dataset.write_text(json.dumps({'qid': 'human-old', 'split': 'dev'}) + '\n', encoding='utf-8')
    report = {'status': 'conditional', 'errors': ['human_test:hard_coverage_failed'],
              'index_sha256': 'index', 'splits': {'human_dev': {'benchmark_sha256': sha256(dataset),
                  'caps': {'40': {'per_query': [{'qid': 'human-old', 'candidates': []}]}}}}}
    return dataset, report


def test_failed_candidate_measurement_still_consumes_observed_dev(tmp_path):
    dataset, report = exposure_fixture(tmp_path)
    assert measured_dev_qids(report, dataset, 'index') == {'human-old'}
    assert report['status'] == 'conditional'


@pytest.mark.parametrize('change', ['index', 'dataset', 'missing', 'duplicate', 'different_qid', 'unfinished'])
def test_successor_rejects_unbound_or_unpaired_exposure(tmp_path, change):
    dataset, original = exposure_fixture(tmp_path)
    report = deepcopy(original)
    part = report['splits']['human_dev']
    pairs = part['caps']['40']['per_query']
    if change == 'index':
        report['index_sha256'] = 'different'
    elif change == 'dataset':
        dataset.write_text(dataset.read_text(encoding='utf-8') + '\n', encoding='utf-8')
    elif change == 'missing':
        pairs.clear()
    elif change == 'duplicate':
        pairs.append(pairs[0])
    elif change == 'different_qid':
        pairs[0]['qid'] = 'not-measured'
    else:
        report['status'] = 'pending'
    with pytest.raises(ValueError):
        measured_dev_qids(report, dataset, 'index')


def test_dev_study_rejects_heldout_filename_and_split(tmp_path):
    path = tmp_path / 'human_retrieval_test.jsonl'
    path.write_text(json.dumps({'qid': 'heldout', 'split': 'test'}) + '\n', encoding='utf-8')
    with pytest.raises(ValueError):
        dev_rows(path)
    dev = tmp_path / 'human_retrieval_dev.jsonl'
    dev.write_bytes(path.read_bytes())
    with pytest.raises(ValueError):
        dev_rows(dev)


def test_dev_comparison_cli_preserves_table_options_and_restores_serving_hook(tmp_path, monkeypatch):
    import gzip
    from types import SimpleNamespace
    import scripts.benchmarks.measure_phase7_dev_candidates as study
    from campusai.retrieval.calibration import RetrievalPolicy

    index = tmp_path/'index'
    index.mkdir()
    (index/'manifest.json').write_text('{}', encoding='utf-8')
    calibration = tmp_path/'calibration.json'
    calibration.write_text('{}', encoding='utf-8')
    dataset = tmp_path/'human_retrieval_dev.jsonl'
    dataset.write_text(json.dumps({'qid':'dev', 'split':'dev', 'question':'Orbital propulsion engineering credits?',
                                  'answerable':True, 'doc_ids':['doc'], 'context':[]})+'\n', encoding='utf-8')
    table = {'doc_id':'doc', 'chunk_id':'table', 'page':1,
             'content':json.dumps({'headers':['Discipline','Credits'],
                                   'rows':[['Orbital propulsion engineering','3']]})}
    original = study.table_links.linked_table_sources
    observed = []
    class Probe:
        def __init__(self, *args, **kwargs):
            pass
        def generate_candidates(self, **kwargs):
            # Exercise the same keyword contract that HybridRetriever calls,
            # through the temporary comparison hook and actual table matcher.
            ids = study.table_links.linked_table_sources(kwargs['query'], {'table':table}, 40,
                include_named_curriculum=True, named_exact_only=False)
            observed.append(ids)
            return [SimpleNamespace(to_dict=lambda: table)] if ids else []
    monkeypatch.setattr(study, 'HybridRetriever', Probe)
    monkeypatch.setattr(study, 'frozen_evidence', lambda _: {('doc','table'):table})
    monkeypatch.setattr(study.RetrievalPolicy, 'from_report', lambda *args, **kwargs:
                        RetrievalPolicy(mode='hybrid_rrf', threshold=0))
    monkeypatch.setattr(study, 'source_identity', lambda _: {'source_sha256':'fixture'})
    monkeypatch.setattr(study, 'audit_outputs', lambda rows, outputs, *args:
        {'records':1,'answerable':1,'all_gold_recall':float(bool(outputs['dev'])),
         'candidate_misses':[],'per_query':outputs})
    monkeypatch.setattr(study, 'coverage_errors', lambda *args: [])
    output = tmp_path/'study'
    assert study.main(['--dev',str(dataset),'--index-dir',str(index),'--phase6-calibration',str(calibration),
                       '--output-dir',str(output)]) == 0
    assert observed == [[], ['table']]
    assert study.table_links.linked_table_sources is original
    report = json.loads((output/'comparison.json').read_text(encoding='utf-8'))
    assert report['release_eligible'] is False and report['source_stable'] is True
    with gzip.open(output/'named_curriculum_rows.json.gz', 'rt', encoding='utf-8') as stream:
        assert json.load(stream)['per_query']['dev'][0]['chunk_id'] == 'table'
