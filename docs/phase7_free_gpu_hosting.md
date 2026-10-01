# Phase 7 GPU deployment decision

The user requires zero GPU rental cost for the public website. Local development
and measurement use the existing RTX 4060 Laptop GPU (8 GB); the isolated CUDA
runtime is `.tmp/phase7-gpu-runtime`. The default CPU environment stays intact.

The selected free web target is Hugging Face Spaces **ZeroGPU `large`**. Its
current allocation is half an RTX Pro 6000 Blackwell with 48 GB VRAM. `xlarge`
offers 96 GB but consumes double quota and may queue longer; the reranker does
not need that memory. Eligible free personal accounts can host two ZeroGPU
Spaces after email verification and 30 days of account age. Guest GPU quota is
2 minutes/day and free signed-in quota is 5 minutes/day. These are shared,
limited allocations, not continuously reserved GPU capacity. Recheck the
[official ZeroGPU documentation](https://huggingface.co/docs/hub/spaces-zerogpu)
before deployment; this decision was checked on 2026-10-02.

Keep `large` fixed. Do not switch to paid dedicated hardware, paid plans, or
credits automatically. A failed GPU lease, exhausted quota or excessive queue
wait must preserve Phase 6 retrieval and its frozen citations. Exact-code,
easy-confidence and abstention routes continue to bypass reranking. Bound GPU
admission, retain the service cache, and request only the lease duration measured
for the frozen model/cap. Public response latency includes allocation/queue
wait, not just model execution.

ZeroGPU requires a Gradio entry point and `spaces.GPU` GPU lease boundary;
models are placed on CUDA at module startup. The current persistent local
worker is not a verified ZeroGPU deployment. Adapting it requires checking lease
lifetime, queued work after timeout, visitor context, and cancellation rather
than moving the existing server unchanged. The Space must use a supported
Python/PyTorch combination, then collect its own runtime-bound M3-M11 evidence.
The laptop measurements do not approve Blackwell staging or its shared queue.

No Space has been published and no paid hosting enabled. Publication later
requires a suitable Hugging Face account, the reviewed benchmark/release bundle,
and actual ZeroGPU staging measurements. If free quota or queue latency cannot
meet the fixed release budgets, keep that deployment in demo status and retain
Phase 6 fallback; do not relabel it as a 10/10 production release.
