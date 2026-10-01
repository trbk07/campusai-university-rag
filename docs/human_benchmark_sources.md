# Human-natural question sources for Phase 7

This is a **source inventory, not a reviewed benchmark**. No entries have been
copied into `data/benchmark/phase6_human_natural.jsonl`, and no release gate
is satisfied by this inventory alone.

| Source | Why useful | Required check before benchmark use |
|---|---|---|
| [UET Faculty of IT student FAQ](https://www.fit.uet.vnu.edu.vn/sinh-vien/cac-cau-hoi-thuong-gap/) | The faculty says these are questions it receives from students. They include natural phrasing about curricula, prerequisites and course registration, including spelling variation. | For each question, verify that the relevant answer is actually supported by a **frozen indexed PDF chunk**. FAQ answers or current web policies are not gold evidence for the PDF corpus. Record source URL and retrieval date; check reuse rights. |
| [UET admissions FAQ archive](https://tuyensinh.uet.vnu.edu.vn/category/tu-van-tuyen-sinh/cau-hoi-thuong-gap/) | Realistic prospective-student wording and out-of-corpus/negative cases. | Admissions material changes over time. Do not mark an item answerable unless the frozen corpus supports it; otherwise review it as a negative or exclude it. |
| [TDTU student-regulations QA dataset](https://huggingface.co/datasets/hungminhss/tdtu-student-regulations-qa) | A separate Vietnamese university QA dataset with verification metadata; useful for query-style and negative-domain stress testing. | It is a different university and is licensed CC BY-NC 4.0. Do not import its answers or evidence IDs into the UET benchmark, and review license restrictions before any reuse. |
| [UIT-ViQuAD 2.0 paper](https://arxiv.org/abs/2203.11400) | Human-annotated Vietnamese QA and unanswerable examples for general-language stress tests. | Wikipedia passages are outside the UET corpus. This cannot substitute for UET-specific positive evidence. |

## Intake protocol

1. Acquire questions only where terms permit, preserving URL, retrieval date,
   and original wording. Do not derive answer labels from the live page alone.
2. Have an annotator map each proposed positive item to frozen
   `(doc_id, chunk_id)` evidence in the index, or mark it negative. Reject
   questions whose answer depends on newer policy than the indexed PDF.
3. Have a second, independent reviewer check wording, answerability, evidence,
   language, difficulty and challenge tags. The reviewer must not be the author.
4. Freeze at least 150 accepted records with 100 answerable, 20 negative,
   15 hard/multi-hop, 15 exact-code and 10 ambiguous/abstention records. Tags
   may overlap. Preserve independent reviewer attestation, frozen PDF page
   provenance and separate dev/test/holdout paraphrase groups.
5. Run `python -m evaluation.freeze_human_benchmark` and then the sequential
   gates in [`reranker_release_runbook.md`](reranker_release_runbook.md).
   Keep human and generated regression quality separate. Never fit on test/holdout.

Public FAQ provenance is evidence of source phrasing, **not** proof that a
particular row was independently reviewed. Until steps 2–4 are completed,
M1 remains blocked and later release gates cannot advance.
