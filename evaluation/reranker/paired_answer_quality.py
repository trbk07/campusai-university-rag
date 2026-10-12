"""Paired semantic answer/citation metrics from role-reviewed outputs.

The collector creates pending assessments. Only supplied, hash-bound human
reviews can establish semantic support; quote matching alone cannot do that.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from evaluation.benchmarks.freeze_human_benchmark import PLACEHOLDER_IDENTITIES
from evaluation.benchmarks.human_record_contract import REVIEWER_ROLES, review_role_error
from evaluation.common.release_artifacts import read_json, sha256, write_json


def answer_digest(answer: dict) -> str:
    return hashlib.sha256(json.dumps(answer, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def evaluate_answer_observations(observations: list[dict], *, owner_identity: str | None = None,
                                 delegation=None) -> dict:
    from campusai.rag.schemas import validate_release_response
    if not observations or len({(row["split"], row["qid"], row["arm"]) for row in observations}) != len(observations):
        raise ValueError("unique paired answer observations required")
    parts = defaultdict(list)
    paired = defaultdict(dict)
    reviewer_roles = set()
    for row in observations:
        if row["arm"] not in {"baseline", "phase7"} or type(row["answerable"]) is not bool:
            raise ValueError("invalid answer arm/label")
        valid, _ = validate_release_response(row["answer"])
        if row.get('provider_error') or row['answer'].get('abstention_reason') == 'llm_error':
            raise ValueError('provider failure cannot establish answer quality')
        review = row["review"]
        reviewer = str(review.get("reviewer", "")).strip().casefold()
        role = review.get("reviewer_role")
        role_error = review_role_error({**review, 'author': row.get('author')},
                                      owner_identity, delegation=delegation, scope='semantic')
        if (not valid or review.get("status") != "approved" or reviewer in PLACEHOLDER_IDENTITIES
                or role_error is not None
                or review.get("answer_sha256") != answer_digest(row["answer"])
                or review.get("all_factual_claims_enumerated") is not True):
            raise ValueError("role-declared semantic review of exact output required")
        reviewer_roles.add(role)
        reviewed_at = datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00"))
        observed_at = datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00"))
        if reviewed_at.tzinfo is None or observed_at.tzinfo is None or reviewed_at < observed_at or reviewed_at > datetime.now(timezone.utc):
            raise ValueError("semantic review timestamp must follow the actual output")
        for field in ("rubric_satisfied", "unsupported_affirmative_answer"):
            if type(review.get(field)) is not bool:
                raise ValueError("explicit answer rubric/FPR verdict required")
        if row["answer"]["abstained"] and review["unsupported_affirmative_answer"]:
            raise ValueError("abstention cannot be an unsupported affirmative answer")
        claims = review["claims"]
        if not isinstance(claims, list) or len({claim["claim_id"] for claim in claims}) != len(claims):
            raise ValueError("unique factual claims required")
        declared = {claim["claim_id"] for claim in row["answer"]["claims"]}
        assessed = {claim["claim_id"] for claim in claims}
        if not declared <= assessed:
            raise ValueError("emitted claims missing from semantic review")
        citations = {citation["chunk_id"] for citation in row["answer"]["citations"]}
        for claim in claims:
            if any(type(claim.get(field)) is not bool for field in ("supported", "requires_citation")):
                raise ValueError("explicit claim support verdict required")
            pairs = claim["citations"]
            if (len({item["chunk_id"] for item in pairs}) != len(pairs)
                    or any(item["chunk_id"] not in citations or type(item.get("supports")) is not bool for item in pairs)):
                raise ValueError("invalid reviewed claim-citation pairs")
            if not claim["supported"] and any(item["supports"] for item in pairs):
                raise ValueError("supporting citation contradicts unsupported claim verdict")
            if "multi_hop" in row.get("tags", []) and claim["supported"] and claim.get("all_hops_supported") is not True:
                raise ValueError("multi-hop claim lacks complete hop support")
        emitted_pairs = {(claim["claim_id"], citation) for claim in row["answer"]["claims"] for citation in claim["citation_ids"]}
        reviewed_pairs = {(claim["claim_id"], item["chunk_id"]) for claim in claims for item in claim["citations"]}
        if not emitted_pairs <= reviewed_pairs:
            raise ValueError("emitted citation pairs missing from review")
        required_gold = row["gold_claim_ids"]
        covered_gold = review["covered_gold_claim_ids"]
        if (not isinstance(required_gold, list) or not isinstance(covered_gold, list)
                or len(set(required_gold)) != len(required_gold) or len(set(covered_gold)) != len(covered_gold)
                or not set(covered_gold) <= set(required_gold) or row["answerable"] and not required_gold):
            raise ValueError("frozen gold claim coverage required")
        if row["answer"]["abstained"] and (covered_gold or row["answerable"] and review["rubric_satisfied"]):
            raise ValueError("abstained answer cannot satisfy positive gold claims")
        if row["answerable"] and review["rubric_satisfied"] and set(covered_gold) != set(required_gold):
            raise ValueError("satisfied answer rubric requires complete gold claim coverage")
        key = (row["split"], row["qid"])
        paired[key][row["arm"]] = row
        parts[(row["split"], row["arm"])].append(row)
    for arms in paired.values():
        if set(arms) != {"baseline", "phase7"}:
            raise ValueError("both answer arms required for each qid")
        for field in ("answerable", "gold_claim_ids", "request_sha256", "rubric_sha256", "record_sha256"):
            if arms["baseline"][field] != arms["phase7"][field]:
                raise ValueError("paired answers differ in frozen inputs")
    result = {}
    for (split, arm), rows in sorted(parts.items()):
        positive = [row for row in rows if row["answerable"]]
        negative = [row for row in rows if not row["answerable"]]
        claims = [claim for row in rows for claim in row["review"]["claims"]]
        pairs = [item for claim in claims for item in claim["citations"]]
        required = [claim for claim in claims if claim["requires_citation"]]
        gold_total = sum(len(row["gold_claim_ids"]) for row in positive)
        ratio = lambda numerator, denominator: {"numerator": numerator, "denominator": denominator,
                                                "value": numerator / denominator if denominator else None}
        metrics = {"records": len(rows), "positive": len(positive), "negative": len(negative),
                   "accuracy": ratio(sum(not row["answer"]["abstained"] and row["review"]["rubric_satisfied"] for row in positive), len(positive)),
                   "answer_fpr": ratio(sum(row["review"]["unsupported_affirmative_answer"] for row in negative), len(negative)),
                   "citation_precision": ratio(sum(item["supports"] for item in pairs), len(pairs)),
                   "citation_recall": ratio(sum(any(item["supports"] for item in claim["citations"]) for claim in required), len(required)),
                   "groundedness": ratio(sum(claim["supported"] for claim in claims), len(claims)),
                   "gold_claim_coverage": ratio(sum(len(row["review"]["covered_gold_claim_ids"]) for row in positive), gold_total)}
        result.setdefault(split, {})[arm] = metrics
    review_mode = ("mixed_review" if len(reviewer_roles) > 1 else
                   'owner_delegated_ai_review' if reviewer_roles == {'owner_delegated_ai'} else
                   "owner_self_review" if reviewer_roles == {"project_owner"} else
                   "independent_review" if reviewer_roles == {"independent_reviewer"} else None)
    result["review_summary"] = {"review_mode": review_mode,
                                "reviewer_roles": sorted(reviewer_roles),
                                "semantic_reviews": len(observations)}
    return result


def answer_quality_errors(metrics: dict) -> list[str]:
    errors = []
    for split in ("human_test", "human_holdout"):
        try:
            before, after = metrics[split]["baseline"], metrics[split]["phase7"]
            if any(part[name]["value"] is None for part in (before, after)
                   for name in ("accuracy", "answer_fpr", "citation_precision", "citation_recall", "groundedness", "gold_claim_coverage")):
                raise ValueError("nonzero metric denominators required")
            if (after["citation_precision"]["value"] < .98 or after["groundedness"]["value"] < .98
                    or after["citation_precision"]["value"] < before["citation_precision"]["value"]
                    or before["accuracy"]["value"] - after["accuracy"]["value"] > .005 + 1e-12
                    or before["citation_recall"]["value"] - after["citation_recall"]["value"] > .005 + 1e-12
                    or after["answer_fpr"]["value"] > .01
                    or after["gold_claim_coverage"]["value"] < before["gold_claim_coverage"]["value"]):
                errors.append(split + ":answer_citation_gate")
        except (ValueError, KeyError, TypeError):
            errors.append(split + ":missing_answer_evidence")
    return errors


def product_answer_quality_errors(metrics: dict) -> list[str]:
    """Apply the stricter frozen product floors to reviewed paired metrics.

    This is the numeric answer gate, not source/provenance, group/sample,
    leakage, live-provider or whole C7-03 acceptance. Those require their own
    bound evidence. Historical reranker thresholds remain unchanged.
    """
    policy = read_json(Path(__file__).resolve().parents[2] / 'configs/grounding_release.json')
    if policy.get('thresholds_frozen') is not True:
        return ['product_thresholds_not_frozen']
    thresholds = policy['thresholds']
    floors = {
        'citation_precision': max(.99, thresholds['citation_precision_min']),
        'groundedness': max(.99, thresholds['grounded_claim_precision_min']),
        'citation_recall': max(.98, thresholds['citation_recall_min'],
                               thresholds['citation_completeness_min']),
        'gold_claim_coverage': max(.95, thresholds['grounded_claim_recall_min']),
    }
    errors = []
    for split in ('human_test', 'human_holdout'):
        try:
            for arm in ('baseline', 'phase7'):
                for name in ('accuracy', 'answer_fpr', *floors):
                    ratio = metrics[split][arm][name]
                    numerator, denominator, value = (ratio[k] for k in
                                                     ('numerator', 'denominator', 'value'))
                    if (type(numerator) is not int or type(denominator) is not int
                            or not 0 <= numerator <= denominator or denominator <= 0
                            or type(value) not in (int, float) or not math.isfinite(value)
                            or abs(value - numerator / denominator) > 1e-12):
                        raise ValueError('invalid ratio')
            for name, minimum in floors.items():
                if metrics[split]['phase7'][name]['value'] < minimum:
                    errors.append(f'{split}:product_{name}_floor')
        except (KeyError, TypeError, ValueError, OverflowError):
            errors.append(split + ':missing_product_answer_evidence')
    if not any(error.endswith(':missing_product_answer_evidence') for error in errors):
        errors.extend(answer_quality_errors(metrics))
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/reranker_answer_quality.json"))
    parser.add_argument("--bindings", type=Path, required=True, help="frozen source/model/index/prompt/rubric identity")
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--review-policy", type=Path, default=Path("data/benchmark/phase7_review_policy.json"))
    args = parser.parse_args(argv)
    if args.output.resolve() in {args.observations.resolve(), args.bindings.resolve(), args.rubric.resolve(), args.review_policy.resolve(),
                                 (args.output.parent / "reranker_answer_protocol.json").resolve()}:
        parser.error("answer report must not overwrite raw observations or frozen inputs")
    raw = read_json(args.observations)
    try:
        review_policy = read_json(args.review_policy)
        owner_identity = (review_policy.get("owner_identity")
                          if review_policy.get("owner_self_review_allowed") is True
                          and review_policy.get("owner_semantic_review_allowed") is True else None)
        if (review_policy.get("allow_independent_review") is not True
                or raw.get("review_policy_sha256") != sha256(args.review_policy)):
            raise ValueError("semantic review policy binding required")
        from evaluation.benchmarks.delegated_review import load_delegation
        delegation = load_delegation(review_policy, root=Path(__file__).resolve().parents[2],
                                     index_sha256=raw['index_sha256'], scope='semantic')
        metrics = evaluate_answer_observations(raw["observations"], owner_identity=owner_identity,
                                             delegation=delegation)
        errors = answer_quality_errors(metrics)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError) as error:
        metrics, errors = {}, [str(error)]
    raw_path = args.observations.resolve()
    if not raw_path.is_relative_to(args.output.parent.resolve()):
        raise ValueError("archive observations under the report directory before packaging")
    rubric_path = args.rubric.resolve()
    if not rubric_path.is_relative_to(args.output.parent.resolve()):
        raise ValueError("archive the frozen rubric under the report directory")
    protocol = read_json(args.output.parent / "reranker_answer_protocol.json")
    if protocol.get("rubric_sha256") != sha256(rubric_path):
        raise ValueError("rubric changed after protocol freeze")
    if protocol.get("review_policy_sha256") != sha256(args.review_policy):
        raise ValueError("semantic review policy changed after protocol freeze")
    report = {**read_json(args.bindings), **protocol, "schema_version": 1, "gate": "S4",
              "status": "pass" if not errors else "conditional", "errors": errors, "metrics": metrics,
              "rubric": {"path": rubric_path.relative_to(args.output.parent.resolve()).as_posix(), "sha256": sha256(rubric_path)},
              "raw": {"path": raw_path.relative_to(args.output.parent.resolve()).as_posix(), "sha256": sha256(raw_path)}}
    write_json(args.output, report)
    print(json.dumps({"status": report["status"], "errors": errors}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
