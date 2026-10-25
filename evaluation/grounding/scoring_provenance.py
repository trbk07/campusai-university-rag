"""Permit explicit scorer-only repairs without relabeling native inference."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
import subprocess

from evaluation.common.release_artifacts import source_identity

# None of these files constructs a model request or changes application output.
SCORER_FILES = frozenset({
    "evaluation/grounding/grounding_metrics.py",
    "evaluation/grounding/score_native_predictions.py",
    "evaluation/grounding/validate_grounding_release.py",
    "evaluation/grounding/scoring_provenance.py",
    "evaluation/grounding/checkpoint_release.py",
})


def source_tree_dirty(root: Path) -> bool:
    """Generated evidence is bound as data; edited or untracked source is dirty."""
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'],
                               cwd=root, text=True).strip():
        return True
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'],
                                        cwd=root).decode('utf-8').split('\0')
    manifests = {'plan.md', 'pyproject.toml', 'requirements.txt', 'requirements-dev.txt', 'uv.lock', 'poetry.lock'}
    for name in filter(None, untracked):
        path = Path(name)
        if name in manifests or path.parts[0] in {'src', 'scripts', 'tests', 'configs'}:
            return True
        if path.parts[0] == 'evaluation' and not name.startswith('evaluation/results/'):
            return True
    return False


def _source_files(root: Path) -> dict[str, str]:
    paths = set()
    for directory in ("src", "evaluation", "scripts", "tests"):
        paths.update(p for p in (root / directory).rglob("*.py")
                     if p.is_file() and "__pycache__" not in p.parts)
    paths.update(p for p in (root / "configs").rglob("*") if p.is_file()
                 and p.suffix.lower() in {".json", ".toml", ".yaml", ".yml"}
                 and p.name not in {"key.yaml", "gemini.yaml"})
    paths.update(root / name for name in
                 ("pyproject.toml", "requirements.txt", "requirements-dev.txt", "uv.lock", "poetry.lock")
                 if (root / name).is_file())
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def bind_scoring_source(inference_root: Path, scoring_root: Path) -> dict:
    """Compare physical trees; only named scoring files and tests may differ."""
    scoring_root, inference_root = scoring_root.resolve(), inference_root.resolve()
    if inference_root == scoring_root or not inference_root.is_relative_to(scoring_root):
        raise ValueError("inference snapshot must be retained inside the scoring checkout")
    before, after = _source_files(inference_root), _source_files(scoring_root)
    changes = {name: {"inference_sha256": before.get(name), "scoring_sha256": after.get(name)}
               for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    if any(name not in SCORER_FILES and not name.startswith("tests/") for name in changes):
        raise ValueError("inference inputs or collection code changed; new inference required")
    producer, scorer = source_identity(inference_root), source_identity(scoring_root)
    if producer["runtime_sha256"] != scorer["runtime_sha256"]:
        raise ValueError("inference runtime changed; new inference required")
    return {"policy": "physical-scorer-only-v1",
            "inference_checkout": inference_root.relative_to(scoring_root).as_posix(),
            "inference_source_identity": producer,
            "scoring_source_identity": scorer, "changed_files": changes}


def same_scoring_bytes(recorded: dict, current: dict, root: Path, *,
                       allow_document_only_head: bool = False) -> bool:
    """An evidence/docs commit cannot change accepted executable bytes.

    This opt-in is for internal checkpoint closure; native/public callers keep
    exact commit identity. Both physical hashes, Git ancestry and changed paths
    must agree. Benchmark/config/UI/runtime changes are never documentation.
    """
    if recorded==current:
        return True
    if (not allow_document_only_head or set(recorded)!=set(current)
            or any(recorded.get(key)!=current.get(key) or not recorded.get(key)
                   for key in ('source_sha256','runtime_sha256'))
            or any(not re.fullmatch('[a-f0-9]{40}',str(value.get('commit','')))
                   for value in (recorded,current))):
        return False
    ancestor=subprocess.run(['git','merge-base','--is-ancestor',recorded['commit'],current['commit']],
        cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if ancestor.returncode:
        return False
    changed=subprocess.check_output(['git','diff','--name-only','-z',recorded['commit'],
                                     current['commit'],'--'],cwd=root).decode('utf8').split('\0')
    return all(name in {'plan.md','QA_AUDIT.md'} or name.startswith(('docs/','evaluation/results/'))
               for name in filter(None,changed))


def verify_scoring_source(binding: dict, scoring_root: Path, *,
                          allow_document_only_head: bool = False) -> dict:
    if not isinstance(binding, dict) or not isinstance(binding.get("inference_checkout"), str):
        raise ValueError("invalid scoring source binding")
    actual = bind_scoring_source(scoring_root / binding["inference_checkout"], scoring_root)
    if (allow_document_only_head and same_scoring_bytes(binding['scoring_source_identity'],
            actual['scoring_source_identity'],scoring_root,allow_document_only_head=True)):
        actual['scoring_source_identity']=binding['scoring_source_identity']
    if actual != binding:
        raise ValueError("physical scoring source binding changed")
    return actual["inference_source_identity"]
