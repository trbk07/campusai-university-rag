"""Apply repaired grounding to captured real provider outputs, with no egress.

These are new local postprocessing observations; they never masquerade as a
second live generation or current serving acceptance. Exact prompts and final
response hashes must match the authorized original pilot.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from campusai.rag.grounding import GroundedAnswerGenerator
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from scripts.benchmarks.phase7_dev_answer_pilot import results

ROOT = Path(__file__).resolve().parents[2]


class CapturedFinalResponse:
    def __init__(self, prompt, response):
        self.prompt, self.response, self.calls = prompt, response, 0

    def generate_json(self, prompt, **_options):
        if prompt != self.prompt or self.calls:
            raise ValueError('local replay requires one exact captured prompt')
        self.calls += 1
        return json.loads(self.response)


def replay(raw, packet):
    if (raw['attempted_calls'] != len(packet['pairs']) or not raw['source_stable']
            or len(raw['observations']) != len(packet['pairs'])):
        raise ValueError('requires complete source-stable actual pilot')
    observed = {(x['qid'], x['arm']): x for x in raw['observations']}
    if len(observed) != len(raw['observations']):
        raise ValueError('duplicate original pilot arm')
    output = []
    for pair in packet['pairs']:
        original = observed[pair['qid'], pair['arm']]
        if len(original['llm_calls']) != 1:
            raise ValueError('requires one actual original provider call')
        call = original['llm_calls'][0]
        if (call['provider_status'] != 'completed' or call['cached']
                or call['prompt_sha256'] != pair['prompt_sha256']
                or call['response_text_sha256'] != hashlib.sha256(call['response_text'].encode()).hexdigest()):
            raise ValueError('captured provider provenance changed')
        provider = CapturedFinalResponse(pair['prompt'], call['response_text'])
        generator = GroundedAnswerGenerator(provider, max_context_chars=packet['context_budget']['max_chars'],
                                            max_context_tokens=packet['context_budget']['max_tokens'])
        if generator.prompt(pair['question'], results(pair['evidence'])) != pair['prompt']:
            raise ValueError('repaired grounding changed the transmitted prompt')
        answer = generator.answer(pair['question'], results(pair['evidence']))
        if provider.calls != 1:
            raise ValueError('replay bypassed captured provider response')
        output.append({'qid':pair['qid'], 'arm':pair['arm'], 'answer':answer.to_public_dict(),
            'grounding_diagnostics':answer.to_dict(), 'observed_at':datetime.now(timezone.utc).isoformat(),
            'provider_origin':{'prompt_sha256':call['prompt_sha256'], 'response_text_sha256':call['response_text_sha256'],
                'original_observed_at':original['observed_at']}, 'new_provider_calls':0})
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','packet','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('retain previous replay; use a new output')
    raw,packet=read_json(args.raw),read_json(args.packet)
    if raw['packet_sha256']!=sha256(args.packet):raise ValueError('actual pilot packet binding changed')
    before=source_identity(ROOT)
    observations=replay(raw,packet)
    if before!=source_identity(ROOT):raise ValueError('source changed during local replay')
    record={'schema_version':1,'status':'LOCAL_GROUNDING_REPLAY_PENDING_SOURCE_REVIEW',
        'release_eligible':False,'live_provider':False,'provider_response_replay':True,
        'new_provider_calls':0,'test_used':False,'holdout_used':False,'source_identity':before,
        'original_raw_path':args.raw.as_posix(),'original_raw_sha256':sha256(args.raw),
        'packet_path':args.packet.as_posix(),'packet_sha256':sha256(args.packet),
        'observations':observations,'limitations':['Original real responses reused; this is not a fresh live run.',
            'Four positive-only pairs; no negative or multi-hop denominator or full P7-06 acceptance.']}
    write_json(args.output,record)
    print(json.dumps({'replayed_arms':len(observations),'nonabstained_arms':sum(not x['answer']['abstained'] for x in observations),'new_provider_calls':0}))


if __name__=='__main__':main()
