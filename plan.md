# CampusAI â€” Evidence-Grounded University Knowledge Assistant

## 1. Quyáº¿t Ä‘á»‹nh sáº£n pháº©m

TÃªn dá»± Ã¡n chÃ­nh thá»©c: **CampusAI**.

TÃªn mÃ´ táº£: **Evidence-Grounded University Knowledge Assistant**.

Slug repository/package: `campusai-evidence-rag` / `campusai`.

CampusAI lÃ  trá»£ lÃ½ há»i Ä‘Ã¡p tri thá»©c Ä‘áº¡i há»c. NgÆ°á»i dÃ¹ng táº£i lÃªn cÃ¡c tÃ i liá»‡u cÃ³ nguá»“n rÃµ rÃ ng nhÆ° quy cháº¿ Ä‘Ã o táº¡o, chÆ°Æ¡ng trÃ¬nh Ä‘Ã o táº¡o, Ä‘á» cÆ°Æ¡ng há»c pháº§n, sá»• tay sinh viÃªn, thÃ´ng bÃ¡o há»c vá»¥ vÃ  báº£ng há»c phÃ­. Há»‡ thá»‘ng trÃ­ch xuáº¥t ná»™i dung, láº­p chá»‰ má»¥c, tráº£ lá»i báº±ng tiáº¿ng Viá»‡t hoáº·c tiáº¿ng Anh, luÃ´n dáº«n nguá»“n Ä‘áº¿n tÃ i liá»‡u/trang vÃ  tá»« chá»‘i khi khÃ´ng cÃ³ Ä‘á»§ báº±ng chá»©ng.

Pháº¡m vi cá»‘t lÃµi:

- há»c pháº§n, mÃ£ mÃ´n, tÃ­n chá»‰, há»c ká»³, Ä‘iá»u kiá»‡n tiÃªn quyáº¿t;
- quy cháº¿, thá»i háº¡n Ä‘Äƒng kÃ½, Ä‘iá»u kiá»‡n tá»‘t nghiá»‡p, thá»§ tá»¥c há»c vá»¥;
- so sÃ¡nh chÆ°Æ¡ng trÃ¬nh hoáº·c quy Ä‘á»‹nh giá»¯a cÃ¡c nÄƒm;
- truy váº¥n nhiá»u tÃ i liá»‡u vÃ  cÃ¢u há»i cáº§n ná»‘i nhiá»u máº£nh báº±ng chá»©ng;
- báº£ng biá»ƒu cÃ³ thá»ƒ kiá»ƒm tra Ä‘Æ°á»£c, khÃ´ng Ä‘á»ƒ LLM tá»± Ä‘oÃ¡n sá»‘ liá»‡u.

KhÃ´ng cÃ²n coi bÃ¡o cÃ¡o tÃ i chÃ­nh lÃ  domain sáº£n pháº©m. CÃ¡c fixture PDF vÃ  report
finance-only Ä‘Ã£ Ä‘Æ°á»£c xÃ³a; khi cáº§n Ä‘o láº¡i Task 2, benchmark pháº£i cháº¡y trÃªn corpus
Ä‘áº¡i há»c Ä‘Æ°á»£c cung cáº¥p vÃ  review láº¡i tá»« Ä‘áº§u.

## 2. Má»¥c tiÃªu vÃ  tiÃªu chÃ­ hoÃ n thÃ nh

### Má»¥c tiÃªu ngÆ°á»i dÃ¹ng

Má»™t sinh viÃªn cÃ³ thá»ƒ má»Ÿ website, táº£i 5â€“10 tÃ i liá»‡u cá»§a trÆ°á»ng, chá» há»‡ thá»‘ng xá»­ lÃ½ ná»n, há»i má»™t cÃ¢u tá»± nhiÃªn vÃ  nháº­n Ä‘Æ°á»£c:

1. cÃ¢u tráº£ lá»i ngáº¯n, rÃµ, Ä‘Ãºng pháº¡m vi tÃ i liá»‡u;
2. citation dáº¡ng `[TÃªn tÃ i liá»‡u, trang N]` cho tá»«ng káº¿t luáº­n quan trá»ng;
3. Ä‘oáº¡n trÃ­ch/preview Ä‘á»ƒ kiá»ƒm tra ngay;
4. nhÃ£n thá»i gian hoáº·c phiÃªn báº£n tÃ i liá»‡u;
5. cÃ¢u tráº£ lá»i â€œchÆ°a Ä‘á»§ báº±ng chá»©ngâ€ khi khÃ´ng tÃ¬m tháº¥y thÃ´ng tin Ä‘Ã¡ng tin cáº­y.

### Definition of Done

- CÃ³ website public cháº¡y Ä‘Æ°á»£c báº±ng háº¡ táº§ng free-tier.
- Upload PDF text-based, hiá»ƒn thá»‹ progress vÃ  tráº¡ng thÃ¡i job.
- Parse, chunk, metadata, index vÃ  cache thÃ nh cÃ´ng.
- TÃ¬m kiáº¿m BM25 + dense; query Ä‘Æ¡n giáº£n khÃ´ng pháº£i chá» reranker náº·ng.
- CÃ³ cháº¿ Ä‘á»™ rerank cho cÃ¢u há»i khÃ³.
- LLM chá»‰ Ä‘Æ°á»£c tráº£ lá»i tá»« context Ä‘Ã£ chá»n, cÃ³ citation vÃ  abstention.
- CÃ³ bá»™ benchmark university 100â€“300 cÃ¢u há»i, tÃ¡ch dev/test, khÃ´ng test trÃªn corpus Ä‘Ã£ tune.
- BÃ¡o cÃ¡o Recall@k, MRR/nDCG, citation precision, groundedness, abstention precision, p50/p95 latency vÃ  chi phÃ­/token.
- CÃ³ cÃ¢u há»i so sÃ¡nh nÄƒm 2025/2026 vÃ  multi-hop trong benchmark.
- CÃ³ dashboard tá»‘i thiá»ƒu Ä‘á»ƒ xem tÃ i liá»‡u, cÃ¢u há»i, nguá»“n vÃ  Ä‘iá»ƒm Ä‘Ã¡nh giÃ¡.
- Deploy public báº±ng cÃ¡c dá»‹ch vá»¥ free; cÃ³ giá»›i háº¡n abuse vÃ  khÃ´ng lÆ°u secret trong repo.

## 3. Kiáº¿n trÃºc má»¥c tiÃªu

```text
Browser
  â”‚ upload / progress / chat / citations
  â–¼
Web app/API
  â”œâ”€â”€ rate limit + file validation + tenant/user quota
  â”œâ”€â”€ document registry + job status
  â””â”€â”€ query router
        â”œâ”€â”€ easy: BM25 hoáº·c cache
        â”œâ”€â”€ normal: BM25 + dense + RRF
        â””â”€â”€ hard: hybrid â†’ cross-encoder rerank
  â”‚
  â”œâ”€â”€ object storage: PDF, parsed markdown, tables, manifests
  â”œâ”€â”€ metadata DB: users, documents, versions, jobs, feedback
  â””â”€â”€ background worker
        â”œâ”€â”€ validate PDF
        â”œâ”€â”€ PyMuPDF page extraction
        â”œâ”€â”€ academic metadata detection
        â”œâ”€â”€ structure-aware chunking + provenance
        â”œâ”€â”€ BM25 / dense index
        â””â”€â”€ ready / failed / review-required
  â”‚
  â–¼
Grounded answer service
  â”œâ”€â”€ evidence selection
  â”œâ”€â”€ citation validation
  â”œâ”€â”€ deterministic table/calculation path
  â”œâ”€â”€ LLM answer generation
  â””â”€â”€ abstention if evidence is insufficient
```

### SÆ¡ Ä‘á»“ há»‡ thá»‘ng CampusAI

SÆ¡ Ä‘á»“ dÆ°á»›i Ä‘Ã¢y mÃ´ táº£ luá»“ng chÃ­nh tá»« lÃºc ngÆ°á»i dÃ¹ng upload tÃ i liá»‡u Ä‘áº¿n khi nháº­n cÃ¢u tráº£
lá»i cÃ³ provenance. NhÃ¡nh `review_required` dá»«ng trÆ°á»›c indexing; chá»‰ tÃ i liá»‡u á»Ÿ tráº¡ng thÃ¡i
`ready` má»›i Ä‘Æ°á»£c phÃ©p truy váº¥n.

```mermaid
flowchart LR
    U[NgÆ°á»i dÃ¹ng / Browser]
    API[Web API<br/>Upload Â· Query Â· Poll job]
    SEC[Validation & Security<br/>Magic bytes Â· quota Â· rate limit<br/>path safety Â· size/page limits]
    JOB[Ingestion Job Manager<br/>Queue Â· progress Â· retry Â· cancel<br/>dedupe Â· bounded workers]

    subgraph ING[Phase 1 â€” Ingestion]
        PARSE[PyMuPDF parser<br/>page-level text extraction]
        META[Academic metadata detector<br/>value Â· confidence Â· evidence]
        TABLE[Table extractor<br/>raw values Â· headers Â· table ID]
        CHUNK[Phase 2 chunker<br/>heading Â· section Â· page range]
        PERSIST[(Document Registry<br/>SHA-256 Â· versions Â· manifests)]
        STORE[(Artifact Store<br/>PDF Â· parsed text Â· chunks Â· tables)]
        REVIEW[review_required<br/>ocr_required<br/>no indexing]
    end

    subgraph IDX[Indexing & Retrieval]
        BM25[BM25 index]
        DENSE[Dense index<br/>optional model / fallback]
        FUSION[Hybrid fusion<br/>RRF Â· filters Â· dedupe]
        RERANK[Optional reranker<br/>hard queries only]
    end

    subgraph ANSWER[Grounded answer service]
        EVIDENCE[Evidence selection<br/>context budget]
        VALIDATE[Citation validator<br/>chunk Â· document Â· page Â· range]
        TABLECALC[Deterministic table/calculation path]
        LLM[LLM JSON generation<br/>context-only Â· schema validation]
        ABSTAIN[Abstention<br/>insufficient evidence]
        RESP[Answer + citations<br/>source/page preview]
    end

    U --> API
    API --> SEC
    SEC -->|valid PDF| JOB
    SEC -->|invalid| ERR[Structured error<br/>error_code Â· action]
    JOB --> PARSE
    PARSE -->|text available| META
    PARSE -->|scan-only / parse risk| REVIEW
    META --> TABLE
    TABLE --> CHUNK
    CHUNK --> PERSIST
    CHUNK --> STORE
    PERSIST -->|ingestion complete| JOB
    STORE --> BM25
    STORE --> DENSE
    BM25 --> FUSION
    DENSE --> FUSION
    FUSION -->|normal query| EVIDENCE
    FUSION -->|hard query| RERANK --> EVIDENCE
    API -->|query only when ready| EVIDENCE
    EVIDENCE --> TABLECALC
    EVIDENCE --> LLM
    TABLECALC --> VALIDATE
    LLM --> VALIDATE
    VALIDATE -->|valid evidence| RESP
    VALIDATE -->|missing / invalid evidence| ABSTAIN
    ABSTAIN --> RESP
    RESP --> U

    classDef phase1 fill:#e8f3ff,stroke:#2878b5,color:#12344d;
    classDef phase2 fill:#eef9ee,stroke:#3b8f4c,color:#183d20;
    classDef safety fill:#fff4df,stroke:#c27a00,color:#4d3100;
    classDef answer fill:#f3eaff,stroke:#8355b5,color:#32184d;
    class SEC,JOB,REVIEW,ERR safety;
    class PARSE,META,TABLE,PERSIST,STORE phase1;
    class CHUNK phase2;
    class EVIDENCE,VALIDATE,TABLECALC,LLM,ABSTAIN,RESP answer;
```

#### CÃ¡c invariant quan trá»ng trong sÆ¡ Ä‘á»“

| Äiá»ƒm kiá»ƒm soÃ¡t | Invariant nghiá»‡m thu |
|---|---|
| Validation | File khÃ´ng há»£p lá»‡ bá»‹ cháº·n trÆ°á»›c khi parse; khÃ´ng tin filename Ä‘á»ƒ xÃ¡c Ä‘á»‹nh PDF. |
| Ingestion | Job cÃ³ progress/stage/error; retry idempotent; dedupe theo SHA-256. |
| Scan/OCR | Scan-only káº¿t thÃºc `review_required/ocr_required`, khÃ´ng sinh chunk/index. |
| Chunking | `len(chunk.content) <= _MAX_CHARS`; heading path, page range vÃ  table boundary Ä‘Æ°á»£c giá»¯. |
| Persistence | Registry/artifact cÃ³ source hash, parser/chunker/schema version vÃ  cÃ³ thá»ƒ delete Ä‘áº§y Ä‘á»§. |
| Retrieval | Chá»‰ tÃ i liá»‡u `ready` Ä‘Æ°á»£c truy váº¥n; hybrid/reranker khÃ´ng lÃ m máº¥t provenance. |
| Answer | Citation pháº£i trá» Ä‘áº¿n evidence tá»“n táº¡i vÃ  page há»£p lá»‡; náº¿u khÃ´ng thÃ¬ abstain. |

### CÃ¡c quyáº¿t Ä‘á»‹nh ká»¹ thuáº­t Ä‘Ã£ chá»‘t

1. **Parser máº·c Ä‘á»‹nh lÃ  PyMuPDF.** ÄÃ¢y lÃ  Ä‘Æ°á»ng nhanh cho PDF cÃ³ text, hiá»‡n Ä‘Ã£ cÃ³ cache SHA-256, progress theo trang vÃ  kiá»ƒm tra scan. Docling chá»‰ cháº¡y trong explicit review job cho layout/table khÃ³; khÃ´ng dÃ¹ng cho request thÃ´ng thÆ°á»ng.
2. **Retrieval máº·c Ä‘á»‹nh lÃ  `hybrid`.** `BM25 + dense + RRF` Ä‘á»§ nhanh cho web free. `hybrid_rerank` lÃ  cháº¿ Ä‘á»™ opt-in cho cÃ¢u há»i khÃ³, giá»›i háº¡n tá»‘i Ä‘a 8 candidate.
3. **Model pháº£i load má»™t láº§n má»—i process.** Runtime singleton vÃ  LRU query cache Ä‘Æ°á»£c giá»¯ láº¡i; khÃ´ng load encoder/reranker trong má»—i request.
4. **Reranker khÃ´ng náº±m trÃªn free web request path.** CPU reranker hiá»‡n cÃ³ peak memory khoáº£ng 4.5 GB vÃ  load khoáº£ng 56 giÃ¢y trÃªn mÃ¡y benchmark; chá»‰ dÃ¹ng worker cÃ³ RAM phÃ¹ há»£p hoáº·c báº­t theo feature flag.
5. **KhÃ´ng Ä‘Æ°a Knowledge Graph vÃ o MVP.** Chá»‰ triá»ƒn khai sau khi benchmark chá»©ng minh hybrid/multi-hop chÆ°a giáº£i quyáº¿t Ä‘Æ°á»£c quan há»‡ prerequisite hoáº·c version.
6. **KhÃ´ng thÃªm framework RAG náº·ng á»Ÿ giai Ä‘oáº¡n Ä‘áº§u.** CÃ¡c component hiá»‡n táº¡i minh báº¡ch, dá»… benchmark vÃ  Ä‘Ã£ cÃ³ test; cÃ³ thá»ƒ há»c pattern ingestion/index/store cá»§a LlamaIndex hoáº·c Haystack sau khi cÃ³ nhu cáº§u, nhÆ°ng khÃ´ng Ä‘á»•i framework chá»‰ vÃ¬ xu hÆ°á»›ng.
7. **FAISS lÃ  hÆ°á»›ng scale-up, khÃ´ng báº¯t buá»™c á»Ÿ MVP.** Corpus nhá» dÃ¹ng index hiá»‡n táº¡i Ä‘á»ƒ giáº£m dependency vÃ  cold start; khi vector count tÄƒng, benchmark FAISS vá»›i cosine báº±ng normalized inner product trÆ°á»›c khi chuyá»ƒn.

## 4. Code hiá»‡n táº¡i: giá»¯ láº¡i, sá»­a vÃ  xÃ¢y má»›i

### Giá»¯ láº¡i vÃ  tÃ¡i sá»­ dá»¥ng trá»±c tiáº¿p

| ThÃ nh pháº§n | GiÃ¡ trá»‹ vá»›i CampusAI |
|---|---|
| `src/campusai/ingestion/validate.py` | giá»›i háº¡n file/trang, nháº­n diá»‡n PDF scan, lá»—i rÃµ rÃ ng |
| `docling_parser.py` / PyMuPDF path | parse page-level nhanh, giá»¯ sá»‘ trang vÃ  progress |
| `table_extractor.py` | báº£ng cÃ³ schema, raw preservation, cáº£nh bÃ¡o khÃ´ng phÃ¡ dá»¯ liá»‡u |
| `chunker.py` | chunk theo heading/page/table, káº¿ thá»«a metadata vÃ  provenance |
| `documents/registry.py` | Ä‘Äƒng kÃ½ tÃ i liá»‡u, cache theo hash, trÃ¡nh ingest láº·p |
| `ingestion/jobs.py` | background job, retry, dedupe, bounded executor, progress |
| `retrieval/bm25.py`, `dense_index.py`, `fusion.py`, `hybrid.py` | ná»n táº£ng retrieval nhanh, RRF, filter theo document |
| `retrieval/model_runtime.py` | singleton encoder/reranker, trÃ¡nh cold load láº·p |
| `llm/client.py`, `cache.py`, `rate_limiter.py`, `factory.py` | provider-neutral client, cache, retry/backoff, giá»›i háº¡n request |
| `evaluation/`, `scripts/validate_benchmark.py` | khung Ä‘Ã¡nh giÃ¡ vÃ  kiá»ƒm tra benchmark |
| Task 2 benchmark/tests | engine Ä‘Ã¡nh giÃ¡ parser/retrieval cÃ³ thá»ƒ cháº¡y láº¡i trÃªn corpus Ä‘áº¡i há»c |

### Äá»‘i chiáº¿u riÃªng vá»›i Task 1 cÅ©

Task 1 cÅ© khÃ´ng bá»‹ bá» Ä‘i vÃ  khÃ´ng cáº§n viáº¿t láº¡i tá»« Ä‘áº§u. NÃ³ trá»Ÿ thÃ nh lá»›p gá»i
LLM dÃ¹ng chung cho CampusAI:

- `client.py`: giá»¯ nguyÃªn transport Gemini/OpenAI-compatible, `complete`,
  `generate`, `generate_json`, phÃ¢n loáº¡i lá»—i vÃ  retry;
- `cache.py`: giá»¯ SQLite cache, response metadata vÃ  single-flight á»Ÿ client;
- `rate_limiter.py`: giá»¯ giá»›i háº¡n request vÃ  backoff;
- `factory.py`: giá»¯ cáº¥u hÃ¬nh provider, environment-only secret vÃ  fallback YAML;
- `tests/test_llm*.py`, `tests/integration/test_gemini.py`: giá»¯ lÃ m acceptance
  contract, chá»‰ Ä‘á»•i import namespace `finrag` â†’ `campusai`;
- `docs/t1_acceptance.md`: giá»¯ lÃ m bÃ¡o cÃ¡o acceptance, cáº­p nháº­t tÃªn sáº£n pháº©m;
- `rag/grounding.py` má»›i dÃ¹ng trá»±c tiáº¿p `generate_json` cá»§a Task 1 Ä‘á»ƒ tráº£ vá»
  answer/citations/abstention; LLM khÃ´ng Ä‘Æ°á»£c bypass citation validator.

KhÃ´ng Ä‘Æ°a API key, cache response hoáº·c provider-specific payload vÃ o layer
retrieval. Náº¿u sau nÃ y Ä‘á»•i Gemini sang provider free khÃ¡c, chá»‰ factory/client
Ä‘Æ°á»£c thay; ingestion, retrieval vÃ  citation contract khÃ´ng Ä‘á»•i.

### ÄÃ£ sá»­a Ä‘á»ƒ phÃ¹ há»£p domain má»›i

- Äá»•i package tá»« `finrag` thÃ nh `campusai`; Ä‘á»•i project/lock metadata thÃ nh `campusai-evidence-rag`.
- Äá»•i metadata detector tá»« tÃ i chÃ­nh-only thÃ nh academic: `domain`, `document_type`, `academic_years`, `years`, `semesters`, `language`, `currency` vÃ  `units` dÃ¹ng cho há»c phÃ­/tÃ­n chá»‰.
- XÃ³a cÃ¡c alias tÃ i chÃ­nh-only nhÆ° `fiscal_years` vÃ  `consolidation`; benchmark finance cÅ© Ä‘Ã£ Ä‘Æ°á»£c dá»n khá»i repository.
- Äá»•i table schema Ä‘á»ƒ mang metadata academic, khÃ´ng cÃ²n field tÃ i chÃ­nh-only.
- Äá»•i numeric normalizer thÃ nh parser sá»‘ dÃ¹ng chung cho tÃ­n chá»‰, há»c phÃ­, pháº§n trÄƒm vÃ  báº£ng; khÃ´ng tá»± Ä‘oÃ¡n Ä‘Æ¡n vá»‹.
- Äá»•i warm-up query sang prerequisite/semester.
- Äá»•i `data/benchmark/dev.jsonl` thÃ nh seed benchmark university gá»“m fact, table, calculation, comparison vÃ  multi-hop.
- Äá»•i `configs/default.yaml` cÃ³ app domain, quota web vÃ  tÃªn CampusAI.

### ChÆ°a cáº§n thay Ä‘á»•i

- Contract `Document`, `Chunk`, `Table`: provenance hiá»‡n táº¡i Ä‘Ãºng vá»›i citation.
- SHA-256 cache, page number, `content_type`, heading path.
- Fallback dense deterministic cho mÃ´i trÆ°á»ng khÃ´ng cÃ³ model.
- LLM transport, schema validation, retry vÃ  cache vÃ¬ Ä‘Ã¢y lÃ  háº¡ táº§ng dÃ¹ng chung.
- giá»›i háº¡n benchmark Task 2 50 MB/218 trang; Ä‘Ã¢y lÃ  giá»›i háº¡n Ä‘o nÄƒng lá»±c, khÃ´ng pháº£i quota public web.

### Pháº£i xÃ¢y thÃªm

1. `academic_metadata` chuáº©n hÃ³a institution/program/course/academic-year/version/effective-date; trÆ°á»ng nÃ o khÃ´ng cÃ³ báº±ng chá»©ng thÃ¬ Ä‘á»ƒ `null`.
2. Answer pipeline cÃ³ prompt grounding, context budget, citation validator vÃ  abstention policy.
3. Temporal resolver: chá»n báº£n hiá»‡n hÃ nh theo `effective_date`, tráº£ lá»i so sÃ¡nh khi user há»i â€œkhÃ¡c gÃ¬ giá»¯a nÄƒm X/Yâ€.
4. Multi-document retrieval vÃ  evidence set Ä‘á»ƒ khÃ´ng trá»™n nháº§m hai chÆ°Æ¡ng trÃ¬nh.
5. Deterministic table/calculation executor cho tÃ­n chá»‰, tá»· lá»‡, há»c phÃ­; LLM chá»‰ diá»…n giáº£i káº¿t quáº£.
6. Web UI/API, storage adapter, authentication nháº¹, quota, health check vÃ  job polling.
7. Evaluation dashboard, feedback â€œcitation Ä‘Ãºng/saiâ€, trace latency theo tá»«ng stage.

## 5. Lá»™ trÃ¬nh triá»ƒn khai theo phase

### Phase 0 â€” Äá»•i tÃªn, contract vÃ  baseline

Tráº¡ng thÃ¡i: **Ä‘ang thá»±c hiá»‡n**.

- hoÃ n táº¥t tÃªn CampusAI, package `campusai`, README vÃ  plan nÃ y;
- cháº¡y import scan khÃ´ng cÃ²n `finrag` trong code production;
- giá»¯ Task 2 artifacts Ä‘á»ƒ regression;
- táº¡o `ARCHITECTURE.md`, `.env.example`, policy dá»¯ liá»‡u.

Exit criteria: test suite pass; import public lÃ  `campusai.*`; benchmark validator pass.

### Phase 1 â€” Ingestion Ä‘áº¡i há»c (10/10 gate)

#### Chiáº¿n lÆ°á»£c Ä‘Ã£ chá»n

Phase 1 dÃ¹ng pipeline deterministic-first: PyMuPDF cho PDF text-based lÃ  Ä‘Æ°á»ng máº·c Ä‘á»‹nh,
Docling/OCR chá»‰ lÃ  nhÃ¡nh review opt-in cho tÃ i liá»‡u khÃ³. KhÃ´ng gá»i LLM Ä‘á»ƒ parse metadata,
khÃ´ng index tÃ i liá»‡u chÆ°a Ä‘áº¡t validation, vÃ  khÃ´ng coi fixture sinh tá»± Ä‘á»™ng lÃ  corpus tháº­t.
Má»—i tÃ i liá»‡u Ä‘Æ°á»£c xá»­ lÃ½ qua má»™t job idempotent, cÃ³ registry, version, provenance vÃ  tráº¡ng
thÃ¡i rÃµ rÃ ng. ÄÃ¢y lÃ  lá»±a chá»n tá»‘i Æ°u cho free-tier vÃ¬ giáº£m cold start, chi phÃ­ vÃ  bá» máº·t lá»—i,
Ä‘á»“ng thá»i váº«n má»Ÿ Ä‘Æ°á»ng cho OCR/layout parser á»Ÿ worker riÃªng.

#### Contract Ä‘áº§u vÃ o vÃ  corpus nghiá»‡m thu

- [ ] CÃ³ tá»‘i thiá»ƒu **5 PDF Ä‘áº¡i há»c tháº­t**, Æ°u tiÃªn UET/VNU; corpus pháº£i Ä‘a dáº¡ng loáº¡i/layout
  vÃ  khÃ´ng dÃ¹ng synthetic fixture Ä‘á»ƒ thay tháº¿ coverage tháº­t.
- [ ] Corpus bao phá»§ regulation, curriculum, syllabus, handbook, course catalog, tÃ i liá»‡u
  nhiá»u trang, tÃ i liá»‡u cÃ³ báº£ng, tiáº¿ng Viá»‡t cÃ³ dáº¥u, tiáº¿ng Anh/song ngá»¯ vÃ  Ã­t nháº¥t hai
  phiÃªn báº£n/nÄƒm khÃ¡c nhau.
- [ ] CÃ³ `supplied_real_corpus`, `generated_test_fixtures` vÃ  `holdout_corpus` tÃ¡ch biá»‡t.
- [ ] Má»—i PDF cÃ³ manifest gá»“m tÃªn, nguá»“n, nÄƒm, sá»‘ trang, loáº¡i tÃ i liá»‡u, ngÃ´n ngá»¯,
  SHA-256 vÃ  tráº¡ng thÃ¡i quyá»n sá»­ dá»¥ng; corpus vÃ  manifest Ä‘Æ°á»£c version/hash trong report.
- [ ] Holdout khÃ´ng Ä‘Æ°á»£c dÃ¹ng Ä‘á»ƒ tune parser/chunker; acceptance pháº£i cháº¡y Ä‘Æ°á»£c tá»« workspace
  sáº¡ch vÃ  khÃ´ng Ä‘á»c dá»¯ liá»‡u ngoÃ i repository mÃ  khÃ´ng khai bÃ¡o.

#### Pipeline vÃ  lifecycle báº¯t buá»™c

Tráº¡ng thÃ¡i canonical:

```text
queued â†’ validating â†’ parsing â†’ detecting_metadata â†’ extracting_tables
       â†’ chunking â†’ persisting â†’ indexing â†’ succeeded
       â†˜ review_required / failed / cancelled
```

- [ ] Má»—i stage cÃ³ `started_at`, `finished_at`, progress, duration vÃ  error cÃ³ cáº¥u trÃºc:
  `error_code`, `message`, `stage`, `retryable`, `action`.
- [ ] TÃ¡ch rÃµ `ingestion_complete` vÃ  `index_ready`; scan-only khÃ´ng Ä‘Æ°á»£c gáº¯n
  `succeeded` hoáº·c Ä‘Æ°a vÃ o index.
- [ ] Retry chá»‰ dÃ nh cho lá»—i retryable, cÃ³ backoff/idempotency key vÃ  khÃ´ng táº¡o báº£n ghi,
  file, chunk hay index trÃ¹ng.
- [ ] CÃ³ cancel an toÃ n, cleanup khi fail/cancel, bounded worker theo CPU/RAM, vÃ  phá»¥c há»“i
  registry sau process restart.
- [ ] Concurrent upload cÃ¹ng SHA-256 Ä‘Æ°á»£c dedupe; hai file khÃ¡c nhau cÃ¹ng filename váº«n
  Ä‘Æ°á»£c lÆ°u Ä‘á»™c láº­p.

#### Validation vÃ  an toÃ n file

- [ ] Kiá»ƒm tra PDF magic bytes/signature, khÃ´ng tin filename/suffix; giá»›i háº¡n file size,
  page count, tá»•ng text/table size vÃ  thá»i gian parse.
- [ ] Upload root Ä‘Æ°á»£c cÃ´ láº­p; filename Ä‘Æ°á»£c normalize; cháº·n path traversal, symlink vÃ 
  Ä‘Æ°á»ng dáº«n ngoÃ i root.
- [ ] Tá»« chá»‘i hoáº·c chuyá»ƒn review Ä‘á»‘i vá»›i PDF rá»—ng, há»ng, encrypted, scan-only vÃ 
  decompression bomb; cÃ³ memory guard vÃ  timeout.
- [ ] Temporary files luÃ´n Ä‘Æ°á»£c dá»n sau success/fail/cancel; log khÃ´ng chá»©a toÃ n bá»™ ná»™i
  dung tÃ i liá»‡u nháº¡y cáº£m.
- [ ] CÃ³ test cho file giáº£, file há»ng, encrypted, file quÃ¡ lá»›n, zip/decompression abuse,
  symlink/path traversal vÃ  timeout.

#### Metadata há»c thuáº­t cÃ³ báº±ng chá»©ng

Detector pháº£i tráº£ vá» schema á»•n Ä‘á»‹nh cho `institution`, `faculty/school`, `program`,
`course`, `course_code`, `document_type`, `academic_year`, `semester`, `version`,
`effective_date`, `issue_date`, `language`. Má»—i field cÃ³ thá»ƒ cÃ³:

```json
{
  "value": "Ká»¹ thuáº­t CÆ¡ Ä‘iá»‡n tá»­",
  "confidence": 0.92,
  "evidence": "ChÆ°Æ¡ng trÃ¬nh Ä‘Ã o táº¡o ngÃ nh Ká»¹ thuáº­t CÆ¡ Ä‘iá»‡n tá»­",
  "source_page": 1
}
```

- [ ] KhÃ´ng suy diá»…n field khi thiáº¿u báº±ng chá»©ng: tráº£ `null`, confidence tháº¥p vÃ  warning.
- [ ] Regex/context phÃ¢n biá»‡t tÃªn chÆ°Æ¡ng trÃ¬nh vá»›i sá»‘ tÃ­n chá»‰; `155 tÃ­n chá»‰` khÃ´ng Ä‘Æ°á»£c
  nháº­n lÃ  `program`.
- [ ] Æ¯u tiÃªn bÃ¬a, quyáº¿t Ä‘á»‹nh ban hÃ nh, header/footer cÃ³ kiá»ƒm soÃ¡t; há»— trá»£ tiáº¿ng Viá»‡t cÃ³
  dáº¥u/khÃ´ng dáº¥u vÃ  tiáº¿ng Anh.
- [ ] CÃ³ unit test positive/negative cho tá»«ng field vÃ  integration test trÃªn toÃ n corpus;
  khÃ´ng cÃ³ metadata nghiÃªm trá»ng sai trÃªn holdout.

#### Scan/OCR vÃ  persistence

- [ ] Scan-only tráº£ `review_required` vá»›i error code `ocr_required`, khÃ´ng gá»i LLM vÃ 
  khÃ´ng index text rá»—ng.
- [ ] OCR lÃ  background job opt-in, cÃ³ page/time/cost limit vÃ  test cho PDF scan má»™t trang,
  nhiá»u trang vÃ  PDF trá»™n text/image; Phase 1 khÃ´ng phá»¥ thuá»™c OCR production Ä‘á»ƒ pass.
- [ ] Registry dedupe theo SHA-256 nhÆ°ng váº«n lÆ°u source metadata, ingestion config,
  parser/chunker/schema version; pipeline version khÃ¡c khÃ´ng ghi Ä‘Ã¨ artifact cÅ©.
- [ ] Delete document xÃ³a PDF, parsed text, chunks, tables, index, cache vÃ  metadata;
  cÃ³ TTL/cache cleanup vÃ  test xÃ¡c nháº­n xÃ³a tháº­t.

#### Definition of Done Phase 1

- [ ] Corpus tháº­t tá»‘i thiá»ƒu Ä‘áº¡t coverage: Ã­t nháº¥t 5 PDF, tá»‘i thiá»ƒu 3 loáº¡i tÃ i liá»‡u,
  cÃ³ tÃ i liá»‡u nhiá»u trang, cÃ³ báº£ng, cÃ³ tiáº¿ng Viá»‡t/Anh náº¿u scope há»— trá»£, vÃ  cÃ³ Ã­t nháº¥t
  má»™t PDF scan hoáº·c layout lá»—i; report phÃ¢n biá»‡t real corpus/fixtures/holdout.
- [ ] Má»i chunk há»£p lá»‡ cÃ³ `doc_id`, source, page/page range, `content_type`, source hash,
  parser/chunker version vÃ  citation; scan khÃ´ng lÃ m worker treo.
- [ ] Job progress/retry/dedupe/cancel/cleanup/restart pass integration/concurrency tests.
- [ ] Validation, metadata evidence, registry, delete/TTL vÃ  security scan khÃ´ng cÃ²n P0/P1.
- [ ] Acceptance report Ä‘Æ°á»£c regenerate tá»« code hiá»‡n táº¡i; khÃ´ng Ä‘Æ°á»£c sá»­a tay Ä‘á»ƒ biáº¿n fail
  thÃ nh pass.
- [ ] Sá»­a `scripts/validate_ingestion.py` Ä‘á»ƒ acceptance dÃ¹ng coverage gate thá»±c táº¿; fixture
  chá»‰ Ä‘Æ°á»£c bÃ¡o riÃªng cho regression, khÃ´ng thay tháº¿ corpus tháº­t. Report pháº£i cÃ³ holdout
  vÃ  pháº£i fail closed khi regression test tÆ°Æ¡ng á»©ng fail.

### Phase 2 â€” Chunking vÃ  cáº¥u trÃºc (10/10 gate)

#### Chiáº¿n lÆ°á»£c Ä‘Ã£ chá»n

Phase 2 dÃ¹ng structure-aware chunking vá»›i section lÃ m Ä‘Æ¡n vá»‹ ngá»¯ nghÄ©a, page provenance
lÃ m Ä‘Æ¡n vá»‹ citation, vÃ  table lÃ  content type Ä‘á»™c láº­p. Heading Ä‘Æ°á»£c nháº­n diá»‡n báº±ng rule
deterministic cÃ³ normalization Unicode; khÃ´ng dÃ¹ng LLM Ä‘á»ƒ Ä‘oÃ¡n section. Má»i chunk pháº£i
Ä‘áº¡t invariant trÆ°á»›c khi persist: kÃ­ch thÆ°á»›c tuyá»‡t Ä‘á»‘i, section boundary Ä‘Ãºng, provenance
Ä‘á»§ vÃ  citation má»Ÿ Ä‘Æ°á»£c Ä‘Ãºng trang.

#### P0: golden fixtures vÃ  section correctness

- [ ] Golden `Äiá»u kiá»‡n tá»‘t nghiá»‡p` vÃ  `Há»c pháº§n tiÃªn quyáº¿t` pass trÃªn cÃ¡c biáº¿n thá»ƒ: viáº¿t
  hoa, Ä‘Ã¡nh sá»‘, dáº¥u cÃ¢u, heading bá»‹ tÃ¡ch dÃ²ng vÃ  heading kÃ©o qua trang.
- [ ] Golden test xÃ¡c nháº­n Ä‘Ãºng heading, section, page, page range, citation vÃ  ná»™i dung;
  khÃ´ng Äƒn sang section káº¿ bÃªn. Báº¯t buá»™c pass:
  `test_graduation_golden_fixture_keeps_section_and_citation_page`.
- [ ] Heading tiáº¿ng Viá»‡t cÃ³ dáº¥u Ä‘Æ°á»£c giá»¯ nguyÃªn báº£n gá»‘c; normalized form dÃ¹ng cho search
  (`ÄIá»€U KIá»†N` â†’ `dieu kien`) nhÆ°ng khÃ´ng lÃ m máº¥t numbering.
- [ ] Má»¥c lá»¥c, header/footer, tÃªn báº£ng, cÃ¢u viáº¿t hoa dÃ i vÃ  mÃ£ há»c pháº§n pháº£i Ä‘Æ°á»£c loáº¡i
  khá»i heading báº±ng context/page-frequency/numbering checks.

#### Heading vÃ  section inheritance

- [ ] Há»— trá»£ Markdown, `1/1.1/1.1.1`, `Äiá»u/Khoáº£n/Má»¥c/ChÆ°Æ¡ng`, `Article/Section/Chapter`,
  heading cÃ³ `: . -`, heading qua dÃ²ng vÃ  qua trang.
- [ ] Heading record cÃ³ `text`, `normalized`, `level`, `source_page`, `confidence`.
- [ ] `heading_path` káº¿ thá»«a Ä‘Ãºng document â†’ page â†’ section â†’ chunk; heading cáº¥p tháº¥p
  khÃ´ng lÃ m máº¥t cáº¥p cao, heading má»›i chá»‰ thay level tÆ°Æ¡ng á»©ng.
- [ ] Section tiáº¿p tá»¥c Ä‘Ãºng qua page break; khÃ´ng gÃ¡n text trÆ°á»›c heading vÃ o section sau;
  page range vÃ  nested headings pháº£i chÃ­nh xÃ¡c.
- [ ] CÃ³ test section liá»n ká», nested headings, heading cuá»‘i trang, báº£ng xen giá»¯a section
  vÃ  tÃ i liá»‡u layout há»—n há»£p.

#### Chunk-size invariant vÃ  overlap

- [ ] TÃ­nh budget sau khi biáº¿t context header: `body_budget = MAX_CHARS - header_len -
  safety_margin`; Ã¡p dá»¥ng cho text vÃ  table.
- [ ] Final guard cháº¡y sau khi ghÃ©p header/content/overlap; náº¿u vÆ°á»£t thÃ¬ split láº¡i cho Ä‘áº¿n
  khi `len(final_chunk.content) <= _MAX_CHARS`.
- [ ] Unicode Ä‘Æ°á»£c Ä‘o á»•n Ä‘á»‹nh; overlap khÃ´ng Ä‘Æ°á»£c lÃ m chunk vÆ°á»£t giá»›i háº¡n; input há»£p lá»‡
  luÃ´n cÃ³ `diagnostics["chunks_over_limit"] == []`.
- [ ] Chá»‰ ghi overflow khi má»™t Ä‘Æ¡n vá»‹ khÃ´ng thá»ƒ chia nhá» hÆ¡n, kÃ¨m warning vÃ  reason rÃµ rÃ ng;
  khÃ´ng dÃ¹ng `allowed_margin` Ä‘á»ƒ che lá»—i splitter.

#### Table chunk contract

- [ ] Má»—i table lÃ  chunk Ä‘á»™c láº­p, giá»¯ raw values, header Ä‘áº§y Ä‘á»§, `table_id` á»•n Ä‘á»‹nh,
  section path, source, page range vÃ  `content_type="table"`.
- [ ] Table nhiá»u trang Ä‘Æ°á»£c ná»‘i Ä‘Ãºng, láº·p header khi cáº§n, khÃ´ng trá»™n vá»›i section káº¿ tiáº¿p;
  khÃ´ng tá»± diá»…n giáº£i/normalize lÃ m máº¥t dá»¯ liá»‡u.
- [ ] Schema tá»‘i thiá»ƒu: `headers`, `rows`, `units`, `page`, `page_range`, `table_id`,
  `section`, `source`; test cá»™t khÃ´ng Ä‘á»u, Ã´ trá»‘ng, merged cells, thiáº¿u header vÃ  split
  nhiá»u trang. Báº¯t buá»™c pass:
  `test_prerequisite_golden_fixture_preserves_table_header_and_section_boundary`.

#### Provenance, citation vÃ  metric

- [ ] Má»i chunk cÃ³ `doc_id`, source name, page, page range, content type, chunk ID,
  heading path, table ID náº¿u cÃ³, parser/chunker version vÃ  source hash.
- [ ] Citation validator kiá»ƒm tra chunk/document tá»“n táº¡i, page/page range há»£p lá»‡, table ID
  tá»“n táº¡i vÃ  khÃ´ng trá» vÃ o chunk Ä‘Ã£ xÃ³a; test end-to-end:
  `query â†’ retrieved chunk â†’ citation â†’ source document/page`.
- [ ] BÃ¡o cÃ¡o corpus tháº­t cÃ³ chunk count/document, min/mean/p50/p95/max length, overflow,
  overlap, duplicate rate, thiáº¿u heading/citation, sai page range, section boundary failure
  vÃ  table máº¥t header.

#### Definition of Done Phase 2

- [ ] Hai golden fixture pass; chunk overflow báº±ng 0 trÃªn corpus há»£p lá»‡.
- [ ] KhÃ´ng máº¥t heading, numbering, section path, table header/id hoáº·c page range; khÃ´ng
  trá»™n section liá»n nhau.
- [ ] Citation validator pass 100%; má»i chunk cÃ³ provenance Ä‘áº§y Ä‘á»§.
- [ ] Metric report trÃªn corpus tháº­t vÃ  holdout cÃ³ version/hash; layout thá»±c táº¿, báº£ng nhiá»u
  trang, font lá»—i, page rá»—ng vÃ  heading tÃ¡ch dÃ²ng Ä‘á»u cÃ³ test.
- [ ] Acceptance JSON, test runtime, tÃ i liá»‡u vÃ  code khÃ´ng cÃ²n mismatch.

### Phase 1/2 acceptance gate chung

Chá»‰ Ä‘Ã³ng Phase 1 vÃ  Phase 2 khi táº¥t cáº£ lá»‡nh sau cÃ¹ng pass trong workspace sáº¡ch:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\validate_ingestion.py --input-dir data\corpus\university --holdout data\corpus\university\uet_admission_2025.pdf --output evaluation\ingestion_acceptance.json
.\.venv\Scripts\python.exe scripts\secret_scan.py
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
.\.venv\Scripts\python.exe scripts\benchmark_t2.py --input-dir data\corpus\university --output evaluation\t2_results.json --holdout data\corpus\university\uet_admission_2025.pdf --run-docling --docling-max-pages 30 --run-models --device cpu --batch-size 2 --repeats 1 --model-text-count 8 --memory-budget-mb 8192
.\.venv\Scripts\python.exe scripts\create_t2_table_review.py evaluation\t2_results.json --output evaluation\t2_table_review.json --complete
.\.venv\Scripts\python.exe scripts\validate_t2.py evaluation\t2_results.json --acceptance --review evaluation\t2_table_review.json
```

Acceptance report pháº£i Ä‘Æ°á»£c táº¡o láº¡i tá»« runtime hiá»‡n táº¡i vÃ  pháº£i fail closed: náº¿u regression
test tÆ°Æ¡ng á»©ng fail, report khÃ´ng Ä‘Æ°á»£c ghi nháº­n `true`. Release note pháº£i ghi commit/version,
Python/OS/package versions, parser/chunker version, corpus hash, holdout hash vÃ  thá»i gian
cháº¡y. Báº¥t ká»³ P0/P1 security, reliability, provenance hoáº·c reproducibility nÃ o cÃ²n má»Ÿ Ä‘á»u
giá»¯ phase á»Ÿ tráº¡ng thÃ¡i chÆ°a Ä‘áº¡t.

### Phase 3 â€” Embedding vÃ  vector search

- dÃ¹ng fallback hash cho test/dev khÃ´ng táº£i model;
- production benchmark má»™t embedding model multilingual nháº¹;
- persist index theo corpus/version, khÃ´ng build láº¡i má»—i query;
- thÃªm FAISS chá»‰ khi benchmark corpus vÆ°á»£t ngÆ°á»¡ng hiá»‡n táº¡i.

Exit criteria: Recall@5 vÃ  p95 query Ä‘Æ°á»£c ghi theo tá»«ng corpus; restart process khÃ´ng máº¥t index.

### Phase 4 â€” Basic RAG

- láº¥y top-k context, dá»±ng prompt tiáº¿ng Viá»‡t/Anh;
- tráº£ lá»i ngáº¯n vÃ  nÃªu rÃµ document/page;
- cache cÃ¢u há»i giá»‘ng nhau theo corpus version;
- context budget khÃ´ng vÆ°á»£t giá»›i háº¡n model/provider.

Exit criteria: cÃ¢u há»i fact cÃ³ answer/evidence; cÃ¢u ngoÃ i corpus khÃ´ng Ä‘Æ°á»£c bá»‹a.

Phase 4 acceptance: completed with bilingual prompts, provenance-preserving
context/token budgets, versioned query-answer cache, deterministic abstention
tests and offline report in `evaluation/results/basic_rag_report.json`.

### Phase 5 â€” Citation, grounding vÃ  abstention

- output schema báº¯t buá»™c `answer`, `citations`, `confidence`, `abstained`;
- citation pháº£i trá» Ä‘áº¿n chunk tá»“n táº¡i vÃ  page há»£p lá»‡;
- claim khÃ´ng cÃ³ evidence bá»‹ loáº¡i hoáº·c chuyá»ƒn thÃ nh abstention;
- phÃ¢n biá»‡t â€œkhÃ´ng tÃ¬m tháº¥yâ€ vá»›i â€œtÃ i liá»‡u khÃ´ng Ä‘á» cáº­pâ€.

Exit criteria: citation precision vÃ  abstention precision Ä‘Æ°á»£c Ä‘o tá»± Ä‘á»™ng trÃªn test set.

### Phase 6 â€” BM25 + hybrid + RRF

- query routing: exact code/course trÆ°á»›c, hybrid sau;
- filter theo document/program/year khi ngÆ°á»i dÃ¹ng chá»n;
- normalize score, RRF, dedupe chunk vÃ  giá»›i háº¡n candidate;
- Ä‘o latency riÃªng BM25, dense, fusion.

Exit criteria: hybrid tháº¯ng tá»«ng retriever Ä‘Æ¡n trÃªn Recall@k mÃ  p95 váº«n phÃ¹ há»£p free CPU.

### Phase 7 â€” Reranker

- chá»‰ rerank top 8â€“20 candidate trong worker hoáº·c route hard;
- warm má»™t láº§n lÃºc startup; khÃ´ng load trong callback ngÆ°á»i dÃ¹ng;
- cÃ³ circuit breaker/fallback vá» hybrid khi thiáº¿u RAM/timeout;
- ghi `reranker_used` vÃ  latency vÃ o trace.

Exit criteria: reranker cáº£i thiá»‡n nDCG/citation precision Ä‘á»§ lá»›n Ä‘á»ƒ biá»‡n minh chi phÃ­.

### Phase 8 â€” Evaluation vÃ  benchmark

Tá»‘i thiá»ƒu 100â€“300 cÃ¢u há»i do ngÆ°á»i táº¡o vÃ  review, phÃ¢n phá»‘i:

- 30% fact/definition;
- 20% table/filter/calculation;
- 20% prerequisite/multi-hop;
- 15% temporal/comparison;
- 15% unanswerable/ambiguous/adversarial.

Äo Recall@3/5/10, MRR hoáº·c nDCG, answer exact/semantic, citation precision/recall, groundedness, abstention precision/recall, p50/p95 end-to-end, peak RAM vÃ  cache hit. CÃ³ ablation: BM25-only, dense-only, hybrid, hybrid+rerank, cÃ³/khÃ´ng metadata filter.

Exit criteria: cÃ³ report versioned; má»i tá»‘i Æ°u sau Ä‘Ã³ pháº£i khÃ´ng lÃ m xáº¥u answer/citation metrics.

### Phase 9 â€” Temporal RAG

- version document theo academic year/effective date;
- query â€œhiá»‡n hÃ nhâ€, â€œnÄƒm 2025â€, â€œkhÃ¡c gÃ¬â€ pháº£i chá»n Ä‘Ãºng version;
- citation hiá»ƒn thá»‹ ngÃ y hiá»‡u lá»±c vÃ  tráº¡ng thÃ¡i superseded;
- khÃ´ng merge hai phiÃªn báº£n náº¿u user khÃ´ng yÃªu cáº§u comparison.

### Phase 10 â€” Multi-document vÃ  multi-hop

- evidence set cÃ³ `doc_id` vÃ  role cho tá»«ng hop;
- truy váº¥n course â†’ prerequisite â†’ rule â†’ answer;
- tÃ¡ch retrieval cá»§a tá»«ng document rá»“i má»›i fusion khi cáº§n;
- Ä‘Ã¡nh giÃ¡ contamination giá»¯a cÃ¡c chÆ°Æ¡ng trÃ¬nh.

### Phase 11 â€” Knowledge Graph (deferred)

Chá»‰ lÃ m khi Phase 8 cho tháº¥y lá»—i cÃ²n láº¡i chá»§ yáº¿u lÃ  quan há»‡ entity, khÃ´ng pháº£i retrieval/citation. Schema dá»± kiáº¿n: `Course`, `Program`, `Prerequisite`, `Semester`, `Regulation`, `EffectiveDate`. KhÃ´ng xÃ¢y graph trÆ°á»›c benchmark.

### Phase 12 â€” Web app

- dashboard tÃ i liá»‡u: upload, loáº¡i tÃ i liá»‡u, version, tráº¡ng thÃ¡i, lá»—i;
- progress job vÃ  nÃºt retry/review;
- chat vá»›i source cards, page preview, copy citation;
- filter program/year/semester;
- feedback citation Ä‘Ãºng/sai;
- giá»›i háº¡n file, user, concurrency vÃ  cÃ¢u há»i/phÃºt.

### Phase 13 â€” Deploy free

MVP public nÃªn tÃ¡ch:

- **Streamlit Community Cloud** cho UI/demo nháº¹;
- storage/database free-tier cho metadata vÃ  PDF nhá»;
- worker CPU riÃªng hoáº·c Hugging Face Space náº¿u cáº§n process dÃ i;
- LLM provider free quota vá»›i cache báº¯t buá»™c;
- khÃ´ng táº£i BGE-m3/reranker náº·ng trong Streamlit request path.

Náº¿u chá»‰ dÃ¹ng má»™t service Ä‘á»ƒ demo, cháº¥p nháº­n giá»›i háº¡n: tÃ i liá»‡u nhá», má»™t worker, queue ngáº¯n, khÃ´ng Ä‘áº£m báº£o SLA. TÃ i liá»‡u lá»›n vÃ  OCR khÃ´ng nÃªn cháº¡y Ä‘á»“ng bá»™ trong web request.

### Phase 14 â€” Production polish

- structured logs, request/job id, stage timings;
- health/readiness check vÃ  graceful shutdown;
- secret tá»« platform environment, khÃ´ng commit API key;
- xÃ³a file theo TTL, privacy notice, export/delete user data;
- smoke test sau deploy, rollback image, backup manifest;
- README deploy má»™t lá»‡nh vÃ  public demo URL.

## 6. Háº¡ táº§ng free Ä‘Æ°á»£c chá»n

| Nhu cáº§u | Lá»±a chá»n MVP | Giá»›i háº¡n cáº§n cháº¥p nháº­n |
|---|---|---|
| UI | Streamlit Community Cloud | tÃ i nguyÃªn khoáº£ng 2 core/2.7 GB RAM/50 GB; phÃ¹ há»£p demo nháº¹ |
| Worker/model náº·ng | Hugging Face Spaces CPU hoáº·c Space phÃ¹ há»£p | cold start vÃ  quota; GPU free khÃ´ng máº·c Ä‘á»‹nh Ä‘áº£m báº£o |
| File | local ephemeral cho demo hoáº·c Cloudflare R2 | free tier cÃ³ quota; cáº§n TTL vÃ  giá»›i háº¡n upload |
| Metadata | Supabase Postgres | free project cÃ³ quota; khÃ´ng lÆ°u embedding khá»•ng lá»“ vÃ´ háº¡n |
| LLM | free-tier provider, máº·c Ä‘á»‹nh Gemini-compatible adapter | RPM/TPM/RPD thay Ä‘á»•i; pháº£i cache vÃ  rate-limit |
| Vector | file index trong artifact/storage | rebuild theo corpus version; FAISS khi scale |

CÃ¡c giá»›i háº¡n trÃªn pháº£i Ä‘Æ°á»£c kiá»ƒm tra láº¡i lÃºc deploy vÃ¬ free-tier thay Ä‘á»•i theo thá»i gian. KhÃ´ng há»©a â€œmiá»…n phÃ­ vÃ´ háº¡nâ€ hay SLA production.

## 7. Thá»© tá»± viá»‡c pháº£i lÃ m ngay

1. HoÃ n táº¥t import/namespace scan vÃ  cháº¡y toÃ n bá»™ test sau rename.
2. ThÃªm test academic metadata vÃ  test table schema má»›i.
3. ThÃªm `answer/grounding/citation` module, chÆ°a cáº§n UI.
4. Táº¡o corpus university nhá» cÃ³ báº£n 2025/2026 vÃ  20â€“30 cÃ¢u há»i vÃ ng.
5. Káº¿t ná»‘i answer pipeline vá»›i `HybridRetriever` á»Ÿ mode fast.
6. Äo baseline answer/citation/latency; sau Ä‘Ã³ má»›i báº­t reranker.
7. Táº¡o web app tá»‘i thiá»ƒu upload â†’ job â†’ chat â†’ citation.
8. Deploy demo free; giá»›i háº¡n quota trÆ°á»›c khi chia sáº» public.
9. Má»Ÿ rá»™ng benchmark lÃªn 100â€“300 cÃ¢u há»i vÃ  táº¡o evaluation dashboard.

## 8. Nguá»“n tham kháº£o ká»¹ thuáº­t

- [Microsoft MarkItDown](https://github.com/microsoft/markitdown): tham kháº£o mÃ´ hÃ¬nh converter pipeline vÃ  optional dependencies; khÃ´ng dÃ¹ng thay parser layout chÃ­nh.
- [FAISS](https://github.com/facebookresearch/faiss): tham kháº£o dense similarity search vÃ  lá»±a chá»n index khi corpus lá»›n.
- [LlamaIndex ingestion](https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/): tham kháº£o pipeline loader â†’ transformations â†’ index/store vÃ  metadata lineage.
- [Haystack ranker](https://docs.haystack.deepset.ai/docs/ranker): tham kháº£o vá»‹ trÃ­ reranker sau retriever vÃ  trade-off latency.
- [Jmhzbmcn2/med_rag](https://github.com/Jmhzbmcn2/med_rag): tham kháº£o API chat/health,
  source cards (`title`, `section`, `text`, `score`), giá»›i háº¡n input, fallback khi
  reranker lá»—i, context header cho chunk vÃ  metric retrieval theo loáº¡i tÃ i liá»‡u.
- [Hugging Face Spaces](https://huggingface.co/docs/hub/spaces-overview): tham kháº£o hardware/deployment options.
- [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app): tham kháº£o giá»›i háº¡n tÃ i nguyÃªn khi chá»n route free.

CÃ¡c repo trÃªn lÃ  nguá»“n há»c pattern. CampusAI giá»¯ code path nhá», cÃ³ benchmark vÃ  provenance riÃªng thay vÃ¬ sao chÃ©p nguyÃªn framework.
## 9. Phase 1/2 regenerated acceptance evidence

- Full suite: 71 passed, 1 skipped (live Gemini integration requires an external secret).
- Phase 1/2 acceptance: all 16 exit criteria are true in `evaluation/ingestion_acceptance.json`.
- Corpus: 8 real UET/VNU PDFs with manifest SHA-256, a declared holdout, Vietnamese/English, scan/image, and mixed-layout coverage.
- Provenance validator: fail-closed checks for chunk/document/page/page-range/table/source hash; delete and lifecycle checks pass.
- T2 report: schema-2 extended report, Docling comparison, model benchmark and completed table review all validate with `scripts/validate_t2.py --acceptance`.
- OCR policy: scan-only inputs use the bounded RapidOCR ONNX worker when explicitly enabled; default ingestion remains fail-closed with `review_required/ocr_required`.
