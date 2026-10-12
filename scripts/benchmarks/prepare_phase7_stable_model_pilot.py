"""Derive a separately authorized stable-model pilot without changing prompts.

The failed preview journal and its unused call allowance remain immutable.
This script performs no provider request and cannot authorize transmission.
"""
import argparse
from copy import deepcopy
from pathlib import Path

from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from scripts.benchmarks.phase7_final_policy_pilot import ROOT, bound_sources, validate_packet


def prepare(parent: Path, output: Path):
    if output.exists():
        raise FileExistsError(output)
    original = read_json(parent)
    validate_packet(original)
    if original['bound_sources'] != bound_sources():
        raise ValueError('original prompt/grounding sources changed')
    packet = deepcopy(original)
    packet.update(model='gemini-3.8-flash',
                  generation_config={'temperature': 1, 'maxOutputTokens': 4096,
                                     'thinkingConfig': {'thinkingLevel': 'low'}},
                  prepared_source_identity=source_identity(ROOT),
                  pricing_reference='p7-06-stable-model-reference-20261008.json',
                  derived_from={'path': parent.relative_to(ROOT).as_posix(),
                                'sha256': sha256(parent), 'prompts_changed': False},
                  preparation_runner_sha256=sha256(Path(__file__)),
                  authorization_inherited=False)
    validate_packet(packet)
    assert packet['pairs'] == original['pairs']
    write_json(output, packet)
    return {'path': output.relative_to(ROOT).as_posix(), 'sha256': sha256(output),
            'model': packet['model'], 'prompt_chars': packet['prompt_chars'],
            'maximum_calls': packet['max_provider_calls'], 'provider_calls_sent': 0}


def main():
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.parent.resolve(), args.output.resolve())))


if __name__ == '__main__':
    main()
