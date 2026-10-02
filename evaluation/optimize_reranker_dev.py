"""Fit and compare evidence abstention and rank fusion on a dev split only.

Raw model scores, query scope and gold coordinates are retained. An infeasible
quality target is reported as infeasible; this tool never creates human review
or release PASS evidence. Test/holdout input and output overwrite are rejected.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import statistics
import time

from evaluation.compare_retrieval_quality import query_metrics
from evaluation.release_artifacts import sha256, source_identity, write_json
from evaluation.reranker_probe_inputs import FORMATS, probe_loader, scoring_text


def rank_fusion(items, scores, weight, cap):
    """Convex fusion of reciprocal ranks, avoiding incompatible logit scales."""
    if not 0 <= weight <= 1 or not 1 <= cap <= 40:
        raise ValueError("invalid fusion policy")
    head = items[:cap]
    if any(type(scores.get(item["chunk_id"])) not in (int,float)
           or not math.isfinite(scores[item["chunk_id"]]) for item in head):
        raise ValueError("fusion requires finite per-candidate model scores")
    if len({(item["doc_id"],item["chunk_id"]) for item in items}) != len(items):
        raise ValueError("duplicate candidate provenance")
    ce_order = sorted(head, key=lambda item: (-scores[item["chunk_id"]], item["rank"], item["chunk_id"]))
    ce_ranks = {item["chunk_id"]: rank for rank, item in enumerate(ce_order, 1)}
    ranked = sorted(head, key=lambda item: (
        -((1-weight)/(3+item["rank"]) + weight/(3+ce_ranks[item["chunk_id"]])),
        item["rank"], item["chunk_id"]))
    return ranked + items[cap:]


def summarize(rows, outputs):
    positive = [row for row in rows if row["answerable"]]
    negative = [row for row in rows if not row["answerable"]]
    if not positive or not negative:
        raise ValueError("dev requires positive and negative records")
    metrics = [query_metrics(row, outputs[row["qid"]]) for row in positive]
    return {"recall5": statistics.mean(m["recall5"] for m in metrics),
        "mrr": statistics.mean(m["mrr"] for m in metrics),
        "ndcg5": statistics.mean(m["ndcg5"] for m in metrics),
        "negative_fpr": sum(bool(outputs[row["qid"]]) for row in negative)/len(negative),
        "positive":len(positive),"negative":len(negative),
        "all_gold_coverage5": statistics.mean(
            {(g["doc_id"],g["chunk_id"]) for g in row["gold_evidence"]} <=
            {(r["doc_id"],r["chunk_id"]) for r in outputs[row["qid"]][:5]} for row in positive)}


def fit(rows, observations, evidence_signals=("top_logit",)):
    if not evidence_signals or set(evidence_signals) - {"top_logit", "top_margin", "peak_over_mean"}:
        raise ValueError("unsupported evidence signals")
    if any(row.get("split") != "dev" for row in rows):
        raise ValueError("policy fitting accepts only dev rows")
    if (len({row["qid"] for row in rows}) != len(rows)
            or len({o["qid"] for o in observations}) != len(observations)
            or {row["qid"] for row in rows} != {o["qid"] for o in observations}):
        raise ValueError("dev observations must match the unique dataset qids")
    baseline = {o["qid"]:o["baseline"] for o in observations}
    base = summarize(rows, baseline)
    trials = []
    for cap in (8,10,12,16,20,40):
        proposals = {weight: {o["qid"]:rank_fusion(o["pool"],o["scores"],weight,cap)[:5]
                     for o in observations} for weight in (0.,.1,.25,.5,.75,1.)}
        sorted_scores = {o["qid"]:sorted((o["scores"][item["chunk_id"]] for item in o["pool"][:cap]), reverse=True)
                         for o in observations}
        for signal in evidence_signals:
            values = {}
            for qid, scores in sorted_scores.items():
                values[qid] = (-math.inf if not scores else scores[0] if signal == "top_logit"
                               else scores[0] - (scores[1] if len(scores)>1 else scores[0]) if signal == "top_margin"
                               else scores[0] - statistics.mean(scores))
            thresholds = sorted({-1e6, *(math.nextafter(value, math.inf) for value in values.values() if math.isfinite(value))})
            for weight, proposed in proposals.items():
                for threshold in thresholds:
                    outputs = {qid:items if values[qid] >= threshold else [] for qid,items in proposed.items()}
                    quality = summarize(rows,outputs)
                    feasible = quality["negative_fpr"] <= .01 and quality["recall5"] >= .95
                    trials.append({"cap":cap,"rank_weight":weight,"evidence_signal":signal,"evidence_threshold":threshold,
                        "feasible":feasible,"metrics":quality})
    feasible = [trial for trial in trials if trial["feasible"]]
    # A failing candidate is diagnostic only. Preserve its actual recall/FPR.
    chosen = max(feasible or trials, key=lambda trial:(
        -trial["metrics"]["negative_fpr"], trial["metrics"]["recall5"], trial["metrics"]["mrr"],
        trial["metrics"]["ndcg5"], -trial["cap"]))
    return {"baseline":base,"selected":chosen,"feasible":bool(feasible),"trials":trials,
        "selection_rule":"FPR<=1% and recall>=95%; minimize FPR, maximize recall/MRR/nDCG, then minimize cap"}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev",type=Path,default=Path(".release/reranker/studies/ai-benchmark-v1/dev.jsonl"))
    parser.add_argument("--output",type=Path,default=Path(".release/reranker/studies/evidence-fusion-v1"))
    parser.add_argument("--model-dir",type=Path)
    parser.add_argument("--model-name",default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--index-dir",type=Path,default=Path(".tmp/phase6-index"))
    parser.add_argument("--calibration",type=Path,default=Path("evaluation/results/phase6_retrieval_calibration.json"))
    parser.add_argument("--dtype",choices=("float32","float16","bfloat16"),default="float16")
    parser.add_argument("--max-length",type=int,default=512)
    parser.add_argument("--input-format",choices=FORMATS,default="full_chunk")
    parser.add_argument("--raw-scores",type=Path,help="Replay a prior dev-only raw score artifact without model calls")
    parser.add_argument("--evidence-signals",nargs="+",choices=("top_logit","top_margin","peak_over_mean"),default=["top_logit"])
    args=parser.parse_args(argv)
    root=Path(__file__).resolve().parents[1]
    if not args.output.resolve().is_relative_to(root/".release/reranker/studies"):
        raise ValueError("optimization evidence must be isolated")
    rows=[json.loads(line) for line in args.dev.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or any(row.get("split") != "dev" for row in rows):
        raise ValueError("optimization accepts only dev rows")
    if args.raw_scores is None and args.model_dir is None:
        parser.error("--model-dir is required when collecting new scores")
    args.output.mkdir(parents=True,exist_ok=True)
    with (args.output/"attempt.json").open("x",encoding="utf-8") as stream:
        json.dump({"release_eligible":False,"dev_sha256":sha256(args.dev)},stream)
    if args.raw_scores:
        raw = json.loads(args.raw_scores.read_text(encoding="utf-8"))
        if (raw.get("release_eligible") is not False or raw.get("dev_sha256") != sha256(args.dev)
                or raw.get("index_sha256") != sha256(args.index_dir/"manifest.json")
                or raw.get("phase6_calibration_sha256") != sha256(args.calibration)):
            raise ValueError("raw dev scores do not match dataset, index and calibration")
        report = {**source_identity(root), "model_identity":raw["model_identity"],
            "raw_scores_sha256":sha256(args.raw_scores), "raw_source_sha256":raw["source_sha256"],
            "dev_sha256":sha256(args.dev), "index_sha256":raw["index_sha256"],
            "phase6_calibration_sha256":raw["phase6_calibration_sha256"],
            "status":"conditional","release_eligible":False,"test_used":False,"holdout_used":False,
            "calibration_split":"dev", **fit(rows,raw["observations"],args.evidence_signals)}
        report["input_format"] = raw.get("input_format", "full_chunk")
        write_json(args.output/"dev_optimization.json",report)
        print(json.dumps({k:report[k] for k in ("status","baseline","selected","feasible")}),flush=True)
        return 0
    os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1")
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.calibration import RetrievalPolicy
    from campusai.retrieval.cross_encoder_provider import ModelIdentity,OfflineCrossEncoderReranker,RerankCandidate,snapshot_sha256
    identity=ModelIdentity(args.model_name,args.model_dir.name,snapshot_sha256(args.model_dir),
        args.model_dir.name,device="cuda:0",dtype=args.dtype,max_length=args.max_length,batch_size=16)
    provider=OfflineCrossEncoderReranker(identity,args.model_dir,timeout_ms=60000,score_cache_size=0,
        model_loader=probe_loader(args.model_dir,identity,args.input_format))
    retriever=HybridRetriever(args.index_dir,query_cache_size=0,
        policies={"hybrid_rrf":RetrievalPolicy.from_report(args.calibration)})
    observations=[]
    bindings={**source_identity(root),"model_identity":identity.to_dict(),"input_format":args.input_format,"dev_sha256":sha256(args.dev),
        "index_sha256":sha256(args.index_dir/"manifest.json"),"phase6_calibration_sha256":sha256(args.calibration)}
    try:
        provider.warm_up()
        for row in rows:
            baseline=retriever.search(row["question"],row["doc_ids"],filters=row.get("filters"),mode="auto",top_k=5)
            pool=retriever.search(row["question"],row["doc_ids"],filters=row.get("filters"),mode="auto",top_k=40)
            candidates=[RerankCandidate(item.chunk_id,item.doc_id,item.chunk_id,item.page,item.content,
                item.rank,float(item.fusion_score or 0)) for item in pool]
            started=time.perf_counter()
            ranking=provider.score(row["question"],candidates)
            observations.append({"qid":row["qid"],"baseline":[item.to_dict() for item in baseline],
                "pool":[item.to_dict() for item in pool],"scores":{item.chunk_id:item.reranker_score for item in ranking},
                "scoring_input_sha256":{item.chunk_id:__import__("hashlib").sha256(
                    scoring_text(item.content[:8192],args.input_format,row["question"][:2048]).encode()).hexdigest() for item in pool},
                "latency_ms":(time.perf_counter()-started)*1000})
            if len(observations)%10==0:
                print(json.dumps({"completed":len(observations),"total":len(rows)}),flush=True)
        write_json(args.output/"raw_dev.json",{**bindings,"observations":observations,"release_eligible":False})
        report={**bindings,"status":"conditional","release_eligible":False,"test_used":False,"holdout_used":False,
            "calibration_split":"dev",**fit(rows,observations,args.evidence_signals)}
        write_json(args.output/"dev_optimization.json",report)
        print(json.dumps({k:report[k] for k in ("status","baseline","selected","feasible")}),flush=True)
    finally:
        provider.close()
        provider.drain()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
