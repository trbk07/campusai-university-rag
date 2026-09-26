"""Gold-based Phase 5 claim, citation and abstention metrics."""

from __future__ import annotations

from collections import Counter
import re
from typing import Iterable

from campusai.rag.confidence import calibration_metrics


def _tokens(value: object) -> set[str]:
    return set(re.findall(r"[\wÀ-ỹ]+", str(value).casefold()))


def _similarity(left: dict, right: dict) -> float:
    a, b = _tokens(left.get("text", "")), _tokens(right.get("text", ""))
    return len(a & b) / max(1, len(a | b))


def _evidence_set(claim: dict) -> set[tuple]:
    result = set()
    for item in claim.get("evidence", []):
        if isinstance(item, dict) and item.get("chunk_id"):
            result.add(("chunk", item["chunk_id"]))
        elif isinstance(item, dict) and item.get("doc_id") is not None and item.get("page") is not None:
            result.add(("coord", item["doc_id"], item["page"]))
    return result


def _predicted_evidence(row: dict, claim: dict) -> set[tuple]:
    ids = set(claim.get("citation_ids", claim.get("evidence_ids", [])))
    result = {("chunk", item) for item in ids if item}
    if row.get("citations"):
        for item in row.get("citations", []):
            if not isinstance(item, dict):
                continue
            if item.get("chunk_id") in ids or not result:
                if item.get("chunk_id"):
                    result.add(("chunk", item["chunk_id"]))
                if item.get("doc_id") is not None and item.get("page") is not None:
                    result.add(("coord", item["doc_id"], item["page"]))
    return result


def _expand_gold(claims: list[dict]) -> list[dict]:
    """Make gold atomic at evaluation time without changing the source file."""
    expanded = []
    for claim in claims:
        text = str(claim.get("text", ""))
        parts = [part.strip() for part in re.split(r"\s+(?:and|và)\s+", text, flags=re.I) if part.strip()]
        for part in parts or [text]:
            item = dict(claim)
            item.setdefault("claim_id", f"gold-{len(expanded) + 1}")
            item["text"] = part
            expanded.append(item)
    return expanded


def _pair_claims(predicted: list[dict], gold: list[dict]) -> list[tuple[dict, dict | None]]:
    unused = set(range(len(gold)))
    pairs = []
    for claim in predicted:
        claim_id = claim.get("claim_id")
        if claim_id:
            exact = [i for i in unused if gold[i].get("claim_id") == claim_id]
            if exact:
                index = exact[0]
                unused.remove(index)
                pairs.append((claim, gold[index]))
                continue
        candidates = sorted(((_similarity(claim, gold[i]), i) for i in unused), reverse=True)
        if candidates and candidates[0][0] >= 0.35:
            _, index = candidates[0]
            unused.remove(index)
            pairs.append((claim, gold[index]))
        else:
            pairs.append((claim, None))
    return pairs


def evaluate_grounding(rows: Iterable[dict]) -> dict:
    rows = list(rows)
    row_pairs = [_pair_claims(row.get("claims", []), _expand_gold(row.get("gold_claims", []))) for row in rows]
    pairs = [pair for group in row_pairs for pair in group]
    predicted_claim_count = sum(len(row.get("claims", [])) for row in rows)
    matched_predicted_claim_count = sum(gold is not None for _, gold in pairs)
    matched_gold_claim_count = len({gold.get("claim_id") for _, gold in pairs if gold is not None})
    matched_answerable = [(pred, gold) for pred, gold in pairs
                          if gold is not None and bool(gold.get("answerable", True))]
    grounded = 0
    gold_count = sum(len(_expand_gold(row.get("gold_claims", []))) for row in rows)
    leaked = sum(pred.get("status") in {"supported", "partial", "partially_supported"}
                 and (gold is None or not bool(gold.get("answerable", True)))
                 for pred, gold in pairs)
    contradicted_leaked = sum(pred.get("status") == "contradicted"
                               and bool(row.get("public", not row.get("abstained", False)))
                               for row, group in zip(rows, row_pairs) for pred, _ in group)

    citation_total = valid_citations = gold_links = predicted_links = linked_correct = 0
    complete_total = complete_hit = 0
    for row, pairs_for_row in zip(rows, row_pairs):
        citations = [item for item in row.get("citations", []) if isinstance(item, dict)]
        citation_total += len(citations)
        row_gold = set().union(*(_evidence_set(gold) for _, gold in pairs_for_row if gold is not None)) if pairs_for_row else set()
        valid_citations += sum(("chunk", item.get("chunk_id")) in row_gold or
                               ("coord", item.get("doc_id"), item.get("page")) in row_gold
                               for item in citations)
        for pred, gold in pairs_for_row:
            if gold is None or not bool(gold.get("answerable", True)):
                continue
            gold_set, pred_set = _evidence_set(gold), _predicted_evidence(row, pred)
            if pred.get("status") == "supported" and bool(gold_set & pred_set):
                grounded += 1
            gold_links += len(gold_set)
            predicted_links += len(pred_set)
            linked_correct += len(gold_set & pred_set)
            complete_total += 1
            complete_hit += bool(gold_set & pred_set and pred.get("status") == "supported")

    predicted_abstain = [bool(row.get("abstained")) for row in rows]
    gold_abstain = [not bool(row.get("answerable", True)) for row in rows]
    tp = sum(p and g for p, g in zip(predicted_abstain, gold_abstain))
    fp = sum(p and not g for p, g in zip(predicted_abstain, gold_abstain))
    fn = sum(not p and g for p, g in zip(predicted_abstain, gold_abstain))
    reason_pairs = [(row.get("abstention_reason", row.get("reason")), row.get("gold_abstention_reason"))
                    for row in rows if row.get("abstained") and row.get("gold_abstention_reason")]
    reasons = Counter(row.get("abstention_reason", row.get("reason")) for row in rows if row.get("abstained"))
    citation_precision = valid_citations / max(1, citation_total)
    link_precision = linked_correct / max(1, predicted_links)
    link_recall = linked_correct / max(1, gold_links)
    confidence_scores = []
    confidence_labels = []
    label_scores = {"low": 0.25, "medium": 0.60, "high": 0.90}
    for row in rows:
        score = row.get("confidence_score")
        if score is None:
            score = label_scores.get(row.get("confidence"))
        if score is not None:
            confidence_scores.append(float(score))
            confidence_labels.append(bool(row.get("answerable", True)) and not bool(row.get("abstained")))
    calibration = calibration_metrics(confidence_scores, confidence_labels) if confidence_scores else {
        "brier_score": 1.0, "ece": 1.0, "count": 0,
    }
    return {
        "records": len(rows),
        "claim_count": predicted_claim_count,
        "predicted_claim_count": predicted_claim_count,
        "matched_predicted_claim_count": matched_predicted_claim_count,
        "gold_claim_count": gold_count,
        "matched_gold_claim_count": matched_gold_claim_count,
        "grounded_claim_precision": round(grounded / max(1, predicted_claim_count), 6),
        "grounded_claim_recall": round(grounded / max(1, gold_count), 6),
        "unsupported_claim_leakage": round(leaked / max(1, predicted_claim_count), 6),
        "contradicted_claim_leakage": round(contradicted_leaked / max(1, predicted_claim_count), 6),
        "citation_precision": round(citation_precision, 6),
        "citation_recall": round(link_recall, 6),
        "citation_completeness": round(complete_hit / max(1, complete_total), 6),
        "claim_citation_precision": round(link_precision, 6),
        "claim_citation_recall": round(link_recall, 6),
        "claim_citation_f1": round(2 * link_precision * link_recall / max(1e-12, link_precision + link_recall), 6),
        "abstention_precision": round(tp / max(1, tp + fp), 6),
        "abstention_recall": round(tp / max(1, tp + fn), 6),
        "reason_accuracy": round(sum(p == g for p, g in reason_pairs) / max(1, len(reason_pairs)), 6),
        "brier_score": calibration["brier_score"],
        "ece": calibration["ece"],
        "calibration_count": calibration["count"],
        "schema_invalid_rate": round(sum(not row.get("schema_valid", True) for row in rows) / max(1, len(rows)), 6),
        "abstention_reason_counts": dict(reasons),
    }
