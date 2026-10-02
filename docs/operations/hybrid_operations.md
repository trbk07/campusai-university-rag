# Phase 6 operations

## User-upload lifecycle

The server starts with an empty or previously persisted operator-selected
index directory. It does not preload the release fixture corpus. Uploads are
acknowledged by `IngestionJobManager`; each job validates, parses, chunks,
persists, and indexes the supplied file. A successful job returns its content
hash as `document_id`. Query callers must pass the selected `doc_ids`; this is
the tenant/session boundary and prevents retrieval from unrelated uploads.

Recommended environment:

```powershell
$env:CAMPUSAI_INDEX_DIR='data/index'
$env:CAMPUSAI_STORE_DIR='data/store'
$env:CAMPUSAI_DENSE_MODEL='BAAI/bge-m3'
$env:CAMPUSAI_DEVICE='cpu'
$env:CAMPUSAI_RETRIEVAL_CALIBRATION='evaluation/results/hybrid_retrieval_calibration.json'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.venv\Scripts\python.exe -m scripts.operations.serve
```

`OMP_NUM_THREADS=1` and `MKL_NUM_THREADS=1` prevent nested PyTorch/BLAS thread
oversubscription under concurrent CPU requests. On the benchmark host, warm
p95 was 247.839 ms; the 20-user run reached p95 856.038 ms and p99 926.443 ms
with zero errors/timeouts. One process-wide encoder instance used about 2.16
GB peak RSS. Capacity planning must therefore limit worker processes rather
than duplicating the model per request.

## Failure behavior

- Missing dense index: deterministic BM25 fallback with trace reason.
- Missing BM25 index: fail closed.
- Corrupt dense checksum: reject the index.
- Corpus/model/schema/dimension mismatch: reject the index.
- Invalid or unknown filter: structured `RetrievalContractError`.
- Empty, stopword-only, oversized, ambiguous, prompt-injection, impossible
  future-year, or unknown exact-code query: abstain.
- Multiple exact matches: contextual hybrid fallback, never arbitrary document
  selection.
- Restart: load the persisted index and verify manifest/checksum before use.

Index writes are atomic. Model objects are process-wide singletons; retriever
index/cache mutation is guarded, and traces are thread-local. Deleting an
uploaded document must use the existing store/index lifecycle helpers and
invalidate caches through the corpus version.

## Evidence and alerts

Monitor route, fallback, candidate/final counts, query parse, BM25, dense,
fusion and total latency. Alert on non-zero schema/provenance/filter leakage,
FPR above 5%, warm p95 above 500 ms, p99 above 1,000 ms, index checksum errors,
or unexpected model duplication. Never log uploaded content, secrets, raw
embeddings, or internal source hashes in the public response.
