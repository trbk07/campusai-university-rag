# App performance evidence

Cycle: 2026-10-23. No new speed claim is made for the source-packaging repair.

| Workload | Before | After / observation | Limits |
|---|---|---|---|
| Two real PDFs, 34 + 13 pages, local hash-model profile | Sequential 4,980 ms | Parallel 4,515 ms (~9.3% lower wall time) | Earlier same-profile baseline before worker count increase; not the BGE workload. |
| Five generated one-page PDFs, total 4,749 bytes, BGE-M3 offline | No comparable old five-file BGE baseline recorded | All accepted in 0.113 s; ready in 9.619 s including cold model load | Prior cycle, tiny fixtures; does not predict five large/scanned PDFs. |
| 100 EN/VI local API questions, four query workers | No matched before baseline | 100/100 HTTP success, 4.853 s wall time, p95 0.324 s | Deterministic test provider: 72 checked citations, 28 fail-closed abstentions. Not live model accuracy or latency. |
| Clean-source app correctness | Import fails on published source | Exact staged Git export: 98/98 tests PASS in 11.49 s | Test duration is not user-request latency. Earlier minimal candidate: 10.62 s. |

Outstanding: measured peak process RSS, realistic large/scanned/table PDF batch,
slow/disconnected client behavior under load, and live provider latency/quality.
Provider quota remains independent of local query-worker capacity: four local
query slots do not imply four Gemini requests in flight or unlimited API usage.

Existing detailed runtime/profile notes: [Phase 12 handoff](docs/ui/phase12-ui.md).
