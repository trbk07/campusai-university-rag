# Adaptive RAG for Semi-structured Financial Reports — DSAI CV Project Plan

## 0. Project Positioning

### 0.1 Mục tiêu

Xây dựng một hệ thống **Adaptive Retrieval & Reasoning** cho các báo cáo tài chính/doanh nghiệp dạng PDF có cả **văn bản, bảng và cấu trúc phân cấp**. Hệ thống không chỉ trả lời câu hỏi bằng RAG mà còn học một chiến lược định tuyến nhẹ để lựa chọn mức độ xử lý phù hợp với độ khó của câu hỏi.

Project được thiết kế theo hướng **AI/DS research-oriented engineering**: mỗi thành phần quan trọng đều có baseline, metric, ablation và error analysis. Mục tiêu của project không phải chứng minh “có thể build một chatbot RAG”, mà chứng minh bằng thực nghiệm rằng **adaptive reasoning có thể giữ chất lượng gần với full-agentic reasoning trong khi giảm latency và số lần gọi model/tool**.

### 0.2 Bài toán

LLM/RAG thông thường gặp ba vấn đề khi làm việc với báo cáo tài chính:

1. **Retrieval mismatch:** thông tin có thể nằm trong text hoặc table; chỉ dùng dense retrieval hoặc chỉ dùng keyword search dễ bỏ sót evidence.
2. **Numerical/table reasoning:** flatten bảng thành text khiến việc lọc, nhóm, so sánh và tính toán dễ sai.
3. **Over-reasoning / under-reasoning:** câu hỏi đơn giản không cần agentic reasoning, trong khi câu hỏi comparison/multi-hop lại cần nhiều bước. Luôn dùng pipeline phức tạp gây tăng latency và model usage; luôn dùng RAG đơn giản lại làm giảm chất lượng ở câu khó.

### 0.3 Research Questions

**RQ1 — Retrieval:** Hybrid retrieval + reranking có cải thiện khả năng tìm đúng evidence so với BM25 hoặc dense retrieval đơn lẻ không?

**RQ2 — Structured reasoning:** Việc giữ bảng dưới dạng DataFrame và dùng constrained table-query tool có cải thiện độ chính xác trên câu hỏi cần lọc/nhóm/so sánh số liệu không?

**RQ3 — Agentic reasoning:** Agentic multi-step reasoning có cải thiện answer accuracy trên câu hỏi comparison/multi-hop so với RAG thông thường không?

**RQ4 — Main contribution:** Adaptive routing có giữ answer accuracy/citation correctness gần với full-agentic pipeline nhưng giảm average latency và model/tool usage không?

**RQ5 — Reliability:** Evidence verification + citation checking có làm giảm unsupported claims/hallucination và citation errors không?

### 0.4 Main Contribution

**Adaptive Retrieval & Reasoning:** một lightweight router phân loại câu hỏi thành Easy / Medium / Hard và chọn pipeline tương ứng:

- **Easy:** Retrieve → Answer
- **Medium:** Retrieve → Table Query/Calculator → Answer
- **Hard:** Plan → Multi-step Retrieval/Tools → Reason → Verify → Answer

Contribution chỉ được coi là thành công nếu benchmark chứng minh được trade-off **accuracy/reliability vs. latency/model usage**, không chỉ dựa trên demo.

### 0.5 Target domain

**Financial & Business Reports** là domain chính để giữ phạm vi tập trung. Có thể dùng:

- Annual reports
- Financial statements/reports
- Business/ESG reports có bảng số liệu

Không mở rộng đồng thời sang tài liệu kỹ thuật trong phiên bản chính; điều này giúp benchmark, error analysis và câu chuyện CV nhất quán hơn.

### 0.6 Output cuối

- Web QA demo cho financial/business PDFs
- Evidence + page citation cho từng câu trả lời
- Benchmark có 5 loại câu hỏi
- So sánh Naive RAG / Hybrid RAG / Agentic RAG / Adaptive Agentic RAG
- Retrieval evaluation
- Answer/citation/reliability evaluation
- Ablation study
- Router evaluation
- Error taxonomy
- Phân tích accuracy–latency–model usage
- README + architecture diagram + video demo + report

---

# 1. Scope & Design Principles

## 1.1 MUST HAVE

1. Structure-aware PDF parsing
2. Text/table separation
3. Structure-aware chunking + page/section metadata
4. BM25 + dense retrieval
5. Hybrid retrieval bằng RRF
6. Cross-encoder reranking
7. Lightweight difficulty router
8. Agent loop cho Hard questions
9. Calculator tool
10. Constrained table-query tool
11. Evidence store + citation checker
12. Re-retrieval khi evidence chưa đủ
13. Bốn pipeline baseline/comparison
14. Benchmark + reproducible evaluation
15. Ablation study
16. Error analysis
17. Quantitative evidence cho adaptive routing

## 1.2 SHOULD HAVE

- External benchmark: FinQA và/hoặc TAT-QA
- Deploy demo
- Pareto/accuracy-vs-latency visualization
- Caching và experiment logs
- Router confusion matrix

## 1.3 KHÔNG CẦN

Không thêm chỉ để làm CV “ngầu”:

- Multi-agent / agent swarm
- LangGraph/AutoGen/CrewAI nếu không cần thiết
- Fine-tuning LLM
- Knowledge graph
- Voice interface
- Vision-language model
- Fine-tune embedding/reranker
- Nhiều domain không liên quan

Framework chỉ là implementation detail; **baseline, experiment và kết quả** mới là phần quan trọng.

---

# 2. System Architecture

```text
                    Financial / Business PDF
                              │
                              ▼
                 Structure-aware Ingestion
                    ┌─────────┴─────────┐
                    ▼                   ▼
                  Text                Tables
                    │                   │
          section-aware chunks     DataFrame + Schema
                    │                   │
                    └─────────┬─────────┘
                              ▼
                  Hybrid Retrieval Index
                  ┌───────────┴───────────┐
                  ▼                       ▼
                BM25                   Dense
                  └───────────┬───────────┘
                              ▼
                            RRF
                              ▼
                          Reranker
                              │
Query ───────────────► Lightweight Router
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
            EASY           MEDIUM            HARD
              │               │                │
          Retrieve        Retrieve         Plan
              │               │                │
            Answer       Table/Calc      Multi-step Retrieve
                              │                │
                              ▼             Reason
                           Answer              │
                              │             Verify
                              └──────┬─────────┘
                                     ▼
                           Evidence Verification
                                     │
                           ┌─────────┴─────────┐
                           ▼                   ▼
                       Supported          Insufficient
                           │                   │
                           ▼              Re-retrieve
                    Answer + Citation          │
                                              └──► Verify
```

---

# 3. Tech Stack

| Component | Choice | Purpose |
|---|---|---|
| Language | Python | ML/RAG ecosystem |
| PDF parsing | PyMuPDF + pdfplumber/Camelot hoặc Docling | Text/heading/table extraction |
| Chunking | Custom structure-aware chunker | Preserve section/table semantics |
| Dense embedding | `bge-m3` | Multilingual semantic retrieval |
| Sparse retrieval | BM25 | Exact terms, numbers, company names |
| Hybrid fusion | RRF | Combine BM25 + dense without fragile score tuning |
| Vector store | Chroma hoặc Qdrant | Persist dense index |
| Reranker | `bge-reranker-v2-m3` | Re-rank top candidates |
| Router | Embedding features + Logistic Regression | Lightweight difficulty classifier |
| Agent | Custom ReAct-style loop | Full control for experiments |
| LLM | One primary provider/model family for controlled evaluation; stronger model only for Hard path if necessary | Generation/reasoning |
| Calculator | `numexpr`/`asteval` | Safe numerical computation |
| Table tool | Pandas + restricted expression validation | Structured table reasoning |
| Verification | LLM judge + deterministic citation checks | Reliability evaluation |
| Benchmark | Custom + FinQA/TAT-QA subset | Internal + external validation |
| API | FastAPI | Serving |
| UI | Streamlit | Demo |
| Deployment | HF Spaces / Render / Streamlit Cloud | Public demo if feasible |
| Tracking | JSON/CSV + pandas | Reproducible experiments |

### Model-control principle

Không thay đổi model giữa các pipeline trong cùng một experiment nếu không phải biến đang được nghiên cứu. Nếu dùng model reasoning mạnh hơn cho Hard path, phải giữ model/config cố định giữa **Agentic** và **Adaptive** để kết quả phản ánh routing thay vì model quality.

Judge model nên khác model sinh câu trả lời khi có thể để giảm self-evaluation bias.

---

# 4. Data & Benchmark Design

## 4.1 Document set

Chọn khoảng **8–15 financial/business reports** có chất lượng PDF đủ tốt và có nhiều bảng. Giữ một số tài liệu hoàn toàn ngoài benchmark tuning để kiểm tra generalization.

Mỗi document lưu:

```json
{
  "doc_id": "annual_report_2024",
  "page": 12,
  "section": "Revenue Breakdown",
  "content_type": "table",
  "text": "..."
}
```

## 4.2 Question taxonomy

Benchmark chính gồm 5 loại:

1. **Fact** — lấy một thông tin trực tiếp
2. **Table** — lọc/group/aggregate từ bảng
3. **Calculation** — tính toán từ evidence
4. **Comparison** — so sánh hai hoặc nhiều giá trị/period
5. **Multi-hop** — cần evidence từ nhiều section/table/document

## 4.3 Difficulty labels

Difficulty phải được định nghĩa theo **số bước reasoning cần thiết**, không theo độ dài câu:

- **Easy:** một evidence unit đủ trả lời; không cần tool.
- **Medium:** cần một structured query và/hoặc phép tính.
- **Hard:** cần từ hai evidence units trở lên, comparison xuyên section/document, hoặc nhiều bước retrieval/reasoning.

Gán nhãn thủ công trước khi train/evaluate router.

## 4.4 Dataset split

Tối thiểu:

```text
Router labeled set:
70% train / 30% validation

QA benchmark:
Tập evaluation cố định, không dùng để tune prompt/router thresholds.

External benchmark:
FinQA/TAT-QA subset chỉ dùng như external validation.
```

Không dùng cùng một câu để vừa tune router vừa báo cáo final answer accuracy.

## 4.5 Benchmark size

Mục tiêu cuối:

- ≥30 câu/type cho benchmark chính nếu đủ thời gian
- Ưu tiên **Comparison + Multi-hop + Table** vì đây là nơi project có contribution rõ nhất
- External FinQA/TAT-QA: 20–50 câu phù hợp scope

Nếu thiếu thời gian, giảm số câu nhưng **không bỏ các loại câu khó**.

---

# 5. Evaluation Protocol

## 5.1 Retrieval metrics

- Recall@3
- Recall@5
- Recall@10
- MRR

So sánh:

```text
BM25
Dense
Hybrid (RRF)
Hybrid + Reranker
```

## 5.2 Answer metrics

- Answer Accuracy
- Numerical Accuracy cho câu có đáp án số
- Citation Correctness
- Evidence Support / Faithfulness
- Hallucination / Unsupported Claim Rate

## 5.3 Efficiency metrics

- Average latency
- p50 latency
- p95 latency nếu đủ sample
- Number of LLM calls
- Number of tool calls
- Token usage nếu provider cho phép

Với free API, **request count/token usage** được dùng làm proxy cho cost.

## 5.4 Router metrics

- Accuracy
- Macro-F1
- Confusion matrix
- Hard→Easy error rate
- Easy→Hard over-routing rate

Hai lỗi cần phân tích riêng:

```text
Hard → Easy = nguy hiểm cho accuracy
Easy → Hard = tốn latency/model usage
```

## 5.5 Main success criterion

Adaptive Agentic RAG chỉ được kết luận tốt nếu đồng thời đạt:

```text
Accuracy / Citation Quality ≈ Full Agentic
                         AND
Average latency < Full Agentic
                         AND
LLM/tool usage < Full Agentic
```

Không đặt trước một con số improvement. **Chỉ báo cáo kết quả thực nghiệm thật.**

---

# 6. Experimental Baselines

## Baseline A — Naive RAG

```text
Dense Retrieval → LLM → Answer
```

Không tool, không agent, không verification nâng cao.

## Baseline B — Hybrid RAG

```text
BM25 + Dense → RRF → Reranker → LLM → Answer
```

Dùng để đo contribution của retrieval.

## Baseline C — Full Agentic RAG

```text
Every query
    ↓
Strong/Full agentic pipeline
    ↓
Retrieve → Tool/Plan → Reason → Verify
```

Dùng làm upper/reference system cho câu hỏi khó.

## Proposed — Adaptive Agentic RAG

```text
Question
   ↓
Router
 ┌─┼─────────────┐
Easy Medium      Hard
 ↓     ↓           ↓
RAG   RAG+Tool   Full Agentic
 └─────┴───────────┘
          ↓
       Verify
```

### Fair comparison

Bốn pipeline phải chạy trên:

- cùng document index
- cùng benchmark
- cùng answer protocol
- cùng evaluation metrics
- cùng model/config khi model không phải biến nghiên cứu

---

# 7. Detailed Roadmap — 12 Weeks

## Task 1 — Document Processing (Week 1)

### Steps

1. Chọn 8–15 financial/business PDFs.
2. Test parser trên text, headings, bảng đơn giản và bảng merged-cell.
3. Implement `pdf_parser.py`.
4. Tách text/heading/table.
5. Gắn `doc_id/page/section/content_type` ngay khi parse.
6. Implement structure-aware chunking.
7. Chuyển bảng thành DataFrame + schema.
8. Manual quality check 20–30 chunks và 5–10 tables.

### DoD

- PDF parse ổn định.
- Không flatten bảng thành text duy nhất.
- Chunk có page/section metadata.
- Table có DataFrame + schema.

### Experiment

Ghi lại các failure cases của parser để dùng cho error analysis cuối project.

---

## Task 2 — Retrieval Baseline & Hybrid Retrieval (Weeks 2–3)

### Week 2

1. Build BM25 index.
2. Build dense index.
3. Tạo 30–50 query retrieval ground truth.
4. Implement Recall@K/MRR.
5. So sánh BM25 vs Dense.

### Week 3

6. Implement RRF hybrid retrieval.
7. Add cross-encoder reranker.
8. So sánh:

```text
BM25
Dense
Hybrid
Hybrid + Reranker
```

9. Chọn cấu hình retrieval cố định cho các task sau.

### DoD

Có bảng + biểu đồ retrieval metrics và nhận xét rõ **khi nào BM25/Dense/Hybrid có lợi thế**.

---

## Task 3 — Difficulty Router (Week 4)

### Steps

1. Define Easy/Medium/Hard.
2. Label 60–100 representative questions nếu đủ dữ liệu.
3. Baseline heuristic router.
4. Generate embeddings cho questions.
5. Train Logistic Regression classifier.
6. 70/30 train-validation split.
7. Report Accuracy, Macro-F1, confusion matrix.
8. Tune threshold bằng validation set.
9. Đặc biệt phân tích Hard→Easy và Easy→Hard.

### DoD

Router có metric độc lập và có thể giải thích được vì sao một query được route vào từng nhánh.

---

## Task 4 — Agentic Reasoning (Week 5)

### Steps

1. Implement tool interface.
2. Implement minimal ReAct-style loop.
3. Easy path: Retrieve → Answer.
4. Hard path: Planner → sub-queries → retrieve → aggregate evidence.
5. Log every step.
6. Test trên Comparison/Multi-hop questions.

### DoD

Agent có log dạng:

```text
Question
→ Router
→ Sub-question 1
→ Evidence
→ Sub-question 2
→ Evidence
→ Final reasoning
```

Không cần multi-agent.

---

## Task 5 — Structured Table Reasoning (Week 6)

### 5.1 Calculator

1. Implement calculator.
2. Tool schema rõ ràng.
3. Log input/output.
4. Test numerical questions.

### 5.2 Table Query Tool — Signature Feature

Input:

```text
Question + Table Schema
```

Output:

```text
Validated pandas expression
→ result
```

Cho phép một whitelist nhỏ:

- filtering
- `.loc`
- `.groupby`
- `.sum()`
- `.mean()`
- `.max()`
- `.min()`

Không cho phép arbitrary Python/`exec`.

### 5.3 Error handling

Nếu expression sai:

```text
Tool error
→ agent retry (max 1–2)
→ verify result
```

### DoD

Có benchmark riêng cho Table/Calculation/Comparison và chứng minh table tool hoạt động trên các câu mà text-only RAG dễ sai.

---

## Task 6 — Evidence Verification (Week 7)

### Steps

1. Evidence store.
2. Answer verifier.
3. Citation checker.
4. Check numerical output against tool output.
5. Check citation → đúng page/chunk.
6. Nếu evidence thiếu → query rewrite → re-retrieve.
7. Retry tối đa 2 lần.
8. Test trên câu có missing/insufficient evidence.

### DoD

Hệ thống có thể:

```text
Unsupported answer
       ↓
Verifier detects
       ↓
Re-retrieve
       ↓
Verify again
```

hoặc trả lời rõ rằng tài liệu không đủ thông tin.

---

## Task 7 — Integrate Adaptive Pipeline (Week 8)

Implement:

```text
adaptive_agentic_rag.py
```

Ba branch:

```text
Easy
Retrieve → Answer → Verify

Medium
Retrieve → Table/Calculator → Answer → Verify

Hard
Plan → Multi-step Retrieval/Tools → Reason → Verify
```

### Critical experiment

So sánh:

```text
Full Agentic on every query
vs.
Adaptive Agentic
```

Cùng benchmark, cùng model/config.

Log:

- accuracy
- citation correctness
- hallucination rate
- latency
- LLM calls
- tool calls

### DoD

Có evidence định lượng cho RQ4.

---

# 8. Benchmark & Ablation (Weeks 9–10)

## Week 9 — Main benchmark

Chạy 4 pipeline:

```text
Naive RAG
Hybrid RAG
Agentic RAG
Adaptive Agentic RAG
```

Trên cùng benchmark.

Report:

| Pipeline | Accuracy | Citation | Hallucination | Avg Latency | LLM Calls |
|---|---:|---:|---:|---:|---:|
| Naive | | | | | |
| Hybrid | | | | | |
| Agentic | | | | | |
| Adaptive | | | | | |

Không điền số trước khi chạy experiment.

## Week 10 — Ablation

### Retrieval

- no-hybrid
- no-reranker

### Reasoning

- no-router
- no-planner

### Tools

- no-calculator
- no-table-tool
- no-tools

### Reliability

- no-verification
- no-re-retrieval

### Mục tiêu

Không chỉ nói “component này tốt”; phải đo **component đó đóng góp bao nhiêu**.

---

# 9. Error Analysis (Week 11)

Chọn 20–30 failed cases hoặc toàn bộ nếu dataset nhỏ.

Phân loại lỗi:

1. Parser failure
2. Retrieval miss
3. Reranker failure
4. Router misclassification
5. Planner failure
6. Table extraction error
7. Table query expression error
8. Calculator error
9. Evidence verification failure
10. Hallucination despite retrieved evidence
11. Citation mismatch

Với mỗi category lưu:

```text
Question
Expected evidence
System behavior
Failure cause
Potential fix
```

### Output

`failure_taxonomy.csv` + 5–10 representative examples trong README/report.

Đây là phần bắt buộc để project thể hiện khả năng **debug AI system**, không chỉ build demo.

---

# 10. Analysis & Visualization (Week 11)

Tạo tối thiểu:

### Figure 1 — Retrieval comparison

```text
Recall@5 / MRR
BM25 vs Dense vs Hybrid vs Reranker
```

### Figure 2 — Pipeline comparison

```text
Accuracy vs Latency
Naive / Hybrid / Agentic / Adaptive
```

### Figure 3 — Router confusion matrix

```text
Easy / Medium / Hard
```

### Figure 4 — Error distribution

```text
Retrieval / Router / Table / Tool / Hallucination / Citation
```

Không cần biểu đồ nếu bảng số liệu đã đủ rõ; ưu tiên biểu đồ thực sự hỗ trợ argument.

---

# 11. External Validation (Week 10–11, nếu đủ thời gian)

Dùng một subset nhỏ của **FinQA và/hoặc TAT-QA**.

Mục đích không phải cạnh tranh SOTA mà để trả lời:

> “Phương pháp có hoạt động ngoài benchmark tự xây không?”

Chỉ sử dụng các câu phù hợp với domain/table reasoning.

Report riêng external benchmark, không trộn với benchmark nội bộ.

---

# 12. Deployment & Wrap-up (Week 12)

## Demo

```text
Upload PDF
   ↓
Ask question
   ↓
Show answer
   ↓
Show cited page/evidence
   ↓
Show optional reasoning trace/tool summary
```

Không expose chain-of-thought nội bộ; chỉ hiển thị **action trace** an toàn như:

```text
Router: Hard
Retrieved: pages 12, 18
Used: Table Query + Calculator
Verification: Passed
```

## README bắt buộc

1. Problem
2. Why standard RAG is insufficient
3. Proposed architecture
4. Main contribution
5. Dataset
6. Evaluation protocol
7. Main results
8. Ablation
9. Error analysis
10. Limitations
11. Demo
12. Reproduction instructions

## Video

1–2 phút:

- Upload report
- Ask Easy question
- Ask Table/Calculation question
- Ask Multi-hop question
- Show evidence/citation
- Show action trace

---

# 13. Reproducibility & Engineering Quality

## Required

```text
configs/
  retrieval.yaml
  router.yaml
  agent.yaml
  eval.yaml

src/
evaluation/
tests/
```

Mỗi experiment phải log:

```json
{
  "pipeline": "adaptive",
  "model": "...",
  "question_id": "q023",
  "route": "medium",
  "llm_calls": 1,
  "tool_calls": 1,
  "latency_ms": 1234,
  "answer": "...",
  "citations": ["doc01:p12"],
  "evaluation": {}
}
```

### Tests

- parser tests
- retrieval tests
- router tests
- table tool tests
- citation tests
- end-to-end test

### Caching

Cache LLM/tool outputs để không gọi lại API khi debug hoặc chạy ablation. Điều này đặc biệt quan trọng khi dùng free tier.

---

# 14. Suggested Repository Structure

```text
adaptive-rag-financial/
├── README.md
├── pyproject.toml
├── .env.example
│
├── configs/
│   ├── retrieval.yaml
│   ├── router.yaml
│   ├── agent.yaml
│   └── eval.yaml
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── chunks/
│   ├── tables/
│   └── benchmark/
│       ├── fact.jsonl
│       ├── table.jsonl
│       ├── calculation.jsonl
│       ├── comparison.jsonl
│       ├── multihop.jsonl
│       └── external/
│
├── src/
│   └── adaptive_rag/
│       ├── ingestion/
│       │   ├── pdf_parser.py
│       │   ├── table_extractor.py
│       │   ├── chunker.py
│       │   └── metadata.py
│       │
│       ├── retrieval/
│       │   ├── bm25.py
│       │   ├── dense.py
│       │   ├── hybrid.py
│       │   ├── reranker.py
│       │   └── index.py
│       │
│       ├── router/
│       │   ├── features.py
│       │   ├── classifier.py
│       │   └── thresholds.py
│       │
│       ├── agent/
│       │   ├── planner.py
│       │   ├── agent_loop.py
│       │   └── prompts/
│       │
│       ├── tools/
│       │   ├── calculator.py
│       │   ├── table_query.py
│       │   └── retrieval_tool.py
│       │
│       ├── verification/
│       │   ├── evidence_store.py
│       │   ├── answer_verifier.py
│       │   └── citation_checker.py
│       │
│       └── pipelines/
│           ├── naive_rag.py
│           ├── hybrid_rag.py
│           ├── agentic_rag.py
│           └── adaptive_rag.py
│
├── evaluation/
│   ├── retrieval_metrics.py
│   ├── answer_metrics.py
│   ├── citation_metrics.py
│   ├── efficiency_metrics.py
│   ├── router_metrics.py
│   ├── run_benchmark.py
│   ├── run_ablation.py
│   └── error_analysis.py
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_retrieval_eval.ipynb
│   ├── 03_router_eval.ipynb
│   └── 04_ablation_analysis.ipynb
│
├── api/
│   └── main.py
├── ui/
│   └── app.py
├── tests/
└── docs/
    ├── architecture.md
    ├── experiments.md
    └── report.md
```

---

# 15. Final Deliverables Checklist

## Core system

- [ ] Financial/business PDF ingestion
- [ ] Structure-aware chunking
- [ ] Table → DataFrame + schema
- [ ] BM25 retrieval
- [ ] Dense retrieval
- [ ] Hybrid RRF retrieval
- [ ] Reranker
- [ ] Lightweight difficulty router
- [ ] Agentic multi-step reasoning
- [ ] Calculator tool
- [ ] Constrained Table Query Tool
- [ ] Evidence verification
- [ ] Citation checker
- [ ] Re-retrieval

## Research / evaluation

- [ ] RQ1 retrieval experiment
- [ ] RQ2 table reasoning experiment
- [ ] RQ3 agentic reasoning experiment
- [ ] RQ4 adaptive vs full-agentic experiment
- [ ] RQ5 verification experiment
- [ ] Router Accuracy/F1/confusion matrix
- [ ] 4-pipeline comparison
- [ ] Ablation study
- [ ] Error taxonomy
- [ ] Accuracy/latency analysis
- [ ] External benchmark if feasible

## Engineering / presentation

- [ ] Automated tests
- [ ] Experiment logs
- [ ] LLM response caching
- [ ] Public demo
- [ ] README
- [ ] Architecture diagram
- [ ] 1–2 minute demo video
- [ ] Final report/technical note

---

# 16. CV Positioning

## Project title

**Adaptive RAG for Semi-structured Financial Reports**

Tên này phù hợp hơn “Agentic RAG for Semi-structured Documents” vì thể hiện ngay:

- domain
- core problem
- main contribution

## CV bullets sau khi project hoàn thành

Chỉ sử dụng số liệu **đã thực nghiệm thật**.

> **Adaptive RAG for Semi-structured Financial Reports**
>
> • Developed an adaptive RAG system for financial reports, combining structure-aware document parsing, hybrid BM25+dense retrieval, reranking, and difficulty-aware routing for multi-step reasoning.
>
> • Designed a constrained table-query pipeline that preserves PDF tables as structured DataFrames, enabling reliable filtering, aggregation, comparison, and numerical reasoning.
>
> • Implemented evidence verification and citation checking with iterative re-retrieval to reduce unsupported answers and improve citation reliability.
>
> • Evaluated Naive, Hybrid, Agentic, and Adaptive RAG through retrieval metrics, answer accuracy, hallucination/citation analysis, latency, and ablation studies; report quantitative trade-offs between quality and inference cost.

### Khi có kết quả tốt

Ưu tiên thay bullet cuối bằng số liệu:

```text
Improved Recall@5 by X% over dense retrieval.
Maintained X% answer accuracy while reducing average latency by Y% vs. full-agentic RAG.
Reduced unsupported claims by X% with evidence verification.
```

Không ghi các con số này trước khi benchmark hoàn tất.

---

# 17. What Makes This a DSAI-Level Student Project?

Project được coi là hoàn chỉnh khi câu chuyện có đủ chuỗi:

```text
Real problem
    ↓
Hypothesis / Research Questions
    ↓
Baseline
    ↓
Proposed method
    ↓
Controlled experiments
    ↓
Ablation
    ↓
Error analysis
    ↓
Quantitative conclusion
```

Không đánh giá project dựa trên số lượng framework.

**Core identity:**

> A research-oriented AI system that studies whether adaptive retrieval and reasoning can make RAG over semi-structured financial documents more accurate and reliable without paying the full latency/model-usage cost of agentic reasoning on every query.

Đây là định vị cần giữ xuyên suốt code, README, report và CV.
