from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from evaluation.grounding.grounding_metrics import evaluate_grounding
from evaluation.grounding import scoring_provenance as provenance
from tests.test_native_scoring import native_batches


def _reviewed_row():
    gold = 'Có 70% sinh viên đạt kết quả học tập và rèn luyện loại Khá trở lên;'
    return {'answerable': True, 'abstained': False,
            'claims': [{'text': 'Co 70% sinh vien dat ket qua hoc tap va ren luyen loai Kha tro len',
                        'status': 'supported', 'citation_ids': ['c']}],
            'citations': [{'chunk_id': 'c', 'doc_id': 'doc', 'page': 3, 'quote': gold}],
            'gold_claims': [{'text': gold, 'evidence': [{'doc_id': 'doc', 'page': 3, 'quote': gold}]}]}


def test_ascii_claim_keeps_order_values_and_qualifiers_against_literal_reviewed_quote():
    metrics = evaluate_grounding([_reviewed_row()], allow_reviewed_source_subspan=True)
    assert metrics['grounded_claim_precision'] == metrics['citation_precision'] == 1
    assert metrics['unsupported_claim_leakage'] == 0


@pytest.mark.parametrize('replacement', ['Co 71% sinh vien dat ket qua hoc tap va ren luyen loai Kha tro len',
    'Co 70% sinh vien dat ket qua hoc tap va ren luyen loai Kha',
    'Co 70% sinh vien dat ket qua hoc tap va ren luyen loai Gioi tro len',
    'Co 70% sinh vien khong dat ket qua hoc tap va ren luyen loai Kha tro len',
    'Co 70% sinh vien dat ket qua hoc tap va ren luyen loai Kha tro len va duoc hoc bong'])
def test_ascii_normalization_cannot_change_number_condition_grade_polarity_or_add_fact(replacement):
    row = _reviewed_row(); row['claims'][0]['text'] = replacement
    assert evaluate_grounding([row], allow_reviewed_source_subspan=True)['grounded_claim_precision'] == 0


def test_ascii_claim_does_not_license_edited_quotes_or_wrong_source_coordinates():
    for field, value in [('quote', _reviewed_row()['claims'][0]['text']), ('page', 4), ('doc_id', 'other')]:
        row = _reviewed_row(); row['citations'][0][field] = value
        assert evaluate_grounding([row], allow_reviewed_source_subspan=True)['citation_precision'] == 0


@pytest.fixture
def trees(tmp_path, monkeypatch):
    root = tmp_path / 'scorer'; producer = root / '.release' / 'inference'
    for base in (root, producer):
        for name in ('src/product.py', 'evaluation/grounding/collect_native_predictions.py',
                     'evaluation/grounding/grounding_metrics.py', 'configs/grounding_release.json'):
            path = base / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('original')
    def identity(base):
        files = provenance._source_files(Path(base))
        return {'commit': 'producer' if Path(base) == producer else 'scorer',
                'source_sha256': hashlib.sha256(repr(sorted(files.items())).encode()).hexdigest(),
                'runtime_sha256': 'same-runtime'}
    monkeypatch.setattr(provenance, 'source_identity', identity)
    return root, producer


def test_scorer_only_binding_recomputes_exact_physical_hashes(trees):
    root, producer = trees
    (root / 'evaluation/grounding/grounding_metrics.py').write_text('fixed evaluator')
    binding = provenance.bind_scoring_source(producer, root)
    assert set(binding['changed_files']) == {'evaluation/grounding/grounding_metrics.py'}
    assert provenance.verify_scoring_source(binding, root) == binding['inference_source_identity']
    forged = deepcopy(binding); forged['changed_files'] = {}
    with pytest.raises(ValueError): provenance.verify_scoring_source(forged, root)
    (producer / 'evaluation/grounding/grounding_metrics.py').write_text('modified history')
    with pytest.raises(ValueError): provenance.verify_scoring_source(binding, root)


@pytest.mark.parametrize('name', ['src/product.py', 'evaluation/grounding/collect_native_predictions.py',
                                'configs/grounding_release.json'])
def test_runtime_collector_or_threshold_change_cannot_reuse_native_inference(trees, name):
    root, producer = trees
    (root / name).write_text('changed')
    with pytest.raises(ValueError, match='new inference required'):
        provenance.bind_scoring_source(producer, root)


def test_snapshot_must_be_retained_within_scoring_checkout(trees):
    root, producer = trees
    with pytest.raises(ValueError): provenance.bind_scoring_source(root.parent, root)
    with pytest.raises(ValueError): provenance.bind_scoring_source(root, root)


def test_native_validator_requires_physical_scorer_binding_for_old_source(native_batches):
    import json
    from evaluation.common.release_artifacts import source_identity
    from evaluation.grounding.score_native_predictions import score
    from evaluation.grounding.validate_grounding_release import validate
    root, benchmark, directories = native_batches
    producer = root / '.release' / 'inference'
    for base, value in ((producer, 'old scorer'), (root, 'repaired scorer')):
        path = base / 'evaluation/grounding/grounding_metrics.py'
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value)
    for directory in directories:
        path = directory / 'run.json'; run = json.loads(path.read_text())
        run['source_identity'] = source_identity(producer); path.write_text(json.dumps(run))
    unbound = score(benchmark, directories, root)
    assert 'native_source_identity_mismatch' in unbound['release_errors']
    bound = score(benchmark, directories, root, inference_checkout=producer)
    assert 'native_source_identity_mismatch' not in bound['release_errors']
    assert 'scoring_source_binding_invalid' not in bound['release_errors']
    forged = deepcopy(bound); forged['generation']['scoring_source_binding']['changed_files'] = {}
    assert 'scoring_source_binding_invalid' in validate(forged, root=root)
    path = root / 'src/changed_runtime.py'; path.parent.mkdir(exist_ok=True); path.write_text('changed')
    assert 'scoring_source_binding_invalid' in validate(bound, root=root)
