# FinRAG — UI Development Plan

## 1. UI Goal

Build a professional, clean, trustworthy, and research-oriented web interface for FinRAG — an Adaptive RAG system for semi-structured financial and business reports.

The UI should demonstrate:

- Financial document ingestion
- Structure-aware document processing
- Text/table separation
- Structure-aware chunks and metadata
- Question answering over financial reports
- Adaptive routing between Easy / Medium / Hard questions
- Hybrid retrieval
- Reranking
- Table-based reasoning
- Calculator-based reasoning
- Agentic multi-step reasoning
- Evidence and citation verification
- Re-retrieval when evidence is insufficient
- Benchmark comparison
- Retrieval, routing, reliability, and efficiency analytics

The UI is a research/demo interface rather than a generic chatbot.

---

# 2. Design Principles

## 2.1 Visual Direction

Style:

- Professional
- Minimal
- Clean
- Technical
- Research-oriented
- Enterprise AI
- Financial analytics
- Trustworthy

Avoid:

- Excessive neon colors
- Excessive gradients
- Glassmorphism
- 3D elements
- Animated backgrounds
- Gaming-style UI
- Landing-page aesthetics
- Generic ChatGPT clone appearance

The interface should feel closer to:

> Enterprise AI analytics platform + research prototype

rather than:

> Consumer chatbot.

---

# 3. Technology Stack

## Frontend

Use:

- HTML5
- CSS3
- Vanilla JavaScript

Do NOT use:

- React
- Vue
- Angular
- TypeScript
- Tailwind CSS
- shadcn/ui

Reason:

The UI is relatively small and does not require a frontend framework. Vanilla JavaScript keeps the architecture simple, transparent, and easy to maintain for a solo student project.

## Backend Integration

The UI communicates with:

- Python
- FastAPI
- REST API

Architecture:

```text
HTML
  ↓
CSS
  ↓
Vanilla JavaScript
  ↓ REST API
FastAPI
  ↓
FinRAG Backend
```

Java is not required for the UI architecture.

---

# 4. UI Folder Structure

```text
front_end/
├── index.html
│
├── pages/
│   ├── chat.html
│   ├── documents.html
│   ├── document-detail.html
│   ├── benchmark.html
│   ├── analytics.html
│   └── settings.html
│
├── css/
│   ├── main.css
│   │
│   ├── base/
│   │   ├── variables.css
│   │   ├── reset.css
│   │   └── typography.css
│   │
│   ├── layout/
│   │   ├── shell.css
│   │   ├── sidebar.css
│   │   ├── topbar.css
│   │   └── responsive.css
│   │
│   ├── components/
│   │   ├── buttons.css
│   │   ├── cards.css
│   │   ├── badges.css
│   │   ├── inputs.css
│   │   ├── tables.css
│   │   ├── modals.css
│   │   └── alerts.css
│   │
│   └── pages/
│       ├── chat.css
│       ├── documents.css
│       ├── document-detail.css
│       ├── benchmark.css
│       ├── analytics.css
│       └── settings.css
│
├── js/
│   ├── main.js
│   │
│   ├── components/
│   │   ├── sidebar.js
│   │   ├── topbar.js
│   │   ├── modal.js
│   │   ├── dropdown.js
│   │   ├── toast.js
│   │   └── loading.js
│   │
│   ├── pages/
│   │   ├── chat.js
│   │   ├── documents.js
│   │   ├── document-detail.js
│   │   ├── benchmark.js
│   │   ├── analytics.js
│   │   └── settings.js
│   │
│   ├── api/
│   │   ├── client.js
│   │   ├── chat.js
│   │   ├── documents.js
│   │   ├── benchmark.js
│   │   └── analytics.js
│   │
│   └── utils/
│       ├── dom.js
│       ├── format.js
│       └── storage.js
│
├── assets/
│   ├── logo/
│   ├── icons/
│   └── images/
│
└── README.md
```

---

# 5. Design System

## 5.1 Colors

### Primary

```text
Navy:
#0F1B33

Dark Navy:
#0B1428

Primary Blue:
#2563EB

Primary Hover:
#1D4ED8

Light Blue:
#EFF6FF
```

### Background

```text
Page:
#F8FAFC

Surface:
#FFFFFF

Border:
#E2E8F0
```

### Text

```text
Primary:
#0F172A

Secondary:
#64748B

Muted:
#94A3B8
```

### Difficulty

Easy:

```text
#22C55E
Background: #ECFDF5
Text: #15803D
```

Medium:

```text
#F59E0B
Background: #FFFBEB
Text: #B45309
```

Hard:

```text
#EF4444
Background: #FEF2F2
Text: #B91C1C
```

### Verification

Verified:

```text
#10B981
```

---

# 6. Typography

Use:

```text
Inter
```

Hierarchy:

```text
Page title:
24–28px / 600

Section title:
16–18px / 600

Card title:
14–16px / 600

Body:
14px

Secondary:
13px

Metadata:
12px
```

---

# 7. Global Application Layout

## 7.1 App Shell

Desktop-first layout:

```text
┌──────────────────────────────────────────────────────────────┐
│                         TOPBAR                               │
├───────────────┬──────────────────────────────────────────────┤
│               │                                              │
│   SIDEBAR     │                  MAIN CONTENT                │
│               │                                              │
│               │                                              │
│               │                                              │
│               │                                              │
└───────────────┴──────────────────────────────────────────────┘
```

Sidebar:

```text
Width: 240px
```

Topbar:

```text
Height: 64px
```

Cards:

```text
Radius: 10–12px
```

---

# 8. Global Navigation

Sidebar navigation:

```text
FinRAG
────────────────

Chat & QA

Documents

Benchmark

Analytics

Settings
```

Additional sidebar information:

## Adaptive Routing

```text
Adaptive Routing
ON

Easy
Medium
Hard
```

## Current Document

```text
Current Document

Apple 2025 Annual Report
● Ready
```

The sidebar should communicate that adaptive routing is a core feature of FinRAG.

---

# 9. Global Reusable Components

JavaScript components:

```text
js/components/
├── sidebar.js
├── topbar.js
├── modal.js
├── dropdown.js
├── toast.js
└── loading.js
```

Responsibilities:

### sidebar.js

- Render sidebar
- Navigation
- Active page
- Routing status
- Current document status

### topbar.js

- Page title
- Document selector
- Theme control
- User/profile area

### modal.js

- Confirmation dialogs
- Document information
- Error dialogs
- PDF evidence viewer container

### dropdown.js

- Document selector
- Filters
- Settings controls

### toast.js

- Success
- Warning
- Error
- Information

### loading.js

- Loading spinner
- Skeleton loading
- Processing state

---

# 10. Page 1 — Chat & QA

Files:

```text
pages/chat.html
css/pages/chat.css
js/pages/chat.js
```

This is the primary page of FinRAG.

## Main layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Document: [Apple 2025 Annual Report ▼]                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                         CHAT AREA                            │
│                                                              │
│ User Question                                                │
│                                                              │
│ FinRAG Answer                                                │
│ Route Badge                                                  │
│ Key Numbers                                                  │
│ Calculation / Table Result                                   │
│ Verification                                                 │
│ Evidence                                                     │
│ Action Trace                                                 │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ Ask a question...                                  [Send]    │
└──────────────────────────────────────────────────────────────┘
```

---

# 11. Chat Empty State

When no question has been submitted:

```text
┌──────────────────────────────────────────────┐
│                                              │
│              Ask FinRAG                     │
│                                              │
│  Ask questions about financial reports.     │
│                                              │
│  Examples:                                   │
│  • What was Apple's revenue in 2025?        │
│  • Compare revenue between 2024 and 2025.   │
│  • Which segment grew the most?             │
│                                              │
└──────────────────────────────────────────────┘
```

---

# 12. Document Selector

At the top of Chat & QA:

```text
Document:
[ Apple 2025 Annual Report ▼ ]
```

Features:

- Select document
- Search document
- Show processing status
- Show document metadata

---

# 13. Question Input

Main input:

```text
┌──────────────────────────────────────────────┐
│ Ask a question about this document...       │
│                                      [Send]  │
└──────────────────────────────────────────────┘
```

Support:

- Enter to submit
- Shift + Enter for newline
- Disabled state
- Loading state
- Error state

---

# 14. User Question

Display the user's question as a compact message.

Example:

```text
What was the revenue growth from 2024 to 2025?
```

---

# 15. Route Badge

Display FinRAG's routing decision:

```text
● EASY
```

or:

```text
● MEDIUM
```

or:

```text
● HARD
```

Optional metadata:

```text
Route confidence: 0.91
```

Do NOT expose:

- Chain-of-thought
- Hidden reasoning
- Internal prompts

Only show high-level execution information.

---

# 16. Answer Card

Main answer:

```text
┌──────────────────────────────────────────────┐
│ Answer                              VERIFIED │
│                                              │
│ Revenue increased by 8.2% from 2024 to      │
│ 2025.                                        │
│                                              │
└──────────────────────────────────────────────┘
```

Support:

- Text answer
- Highlighted numbers
- Inline citations
- Verification status
- Evidence references

---

# 17. Key Numbers

For quantitative questions:

```text
┌───────────────┬───────────────┬──────────────┐
│ 2024 Revenue  │ 2025 Revenue  │ Growth       │
│ $XX.XB        │ $XX.XB        │ +8.2%        │
└───────────────┴───────────────┴──────────────┘
```

Use when numbers are central to the answer.

---

# 18. Calculation Card

For calculator-based reasoning:

```text
Calculation

(2025 Revenue - 2024 Revenue)
--------------------------------
        2024 Revenue

Result: 8.2%
```

Show:

- Input values
- Formula
- Result

Do not expose internal model reasoning.

---

# 19. Table Result

For structured questions:

```text
┌──────────────┬─────────┬─────────┐
│ Segment      │ 2024    │ 2025    │
├──────────────┼─────────┼─────────┤
│ iPhone       │ ...     │ ...     │
│ Mac          │ ...     │ ...     │
│ Services     │ ...     │ ...     │
└──────────────┴─────────┴─────────┘
```

Features:

- Sorting
- Horizontal scrolling
- Numeric alignment
- Highlight relevant rows
- Show source table/page

---

# 20. Verification Status

Display clearly:

```text
✓ Verified
```

or:

```text
⚠ Insufficient Evidence
```

or:

```text
✕ Citation Check Failed
```

The UI should make evidence reliability visible.

---

# 21. Evidence Panel

Display supporting evidence:

```text
Evidence

[1] Apple 2025 Annual Report
    Page 28
    Revenue increased to ...

[2] Apple 2025 Annual Report
    Page 31
    Services revenue ...
```

Each evidence item should allow:

- Open PDF
- Navigate to page
- Highlight source text
- View metadata

---

# 22. Action Trace

Show only high-level system actions.

Example:

```text
Execution

✓ Question classified → MEDIUM
✓ Hybrid retrieval
✓ Reranking
✓ Table query
✓ Calculation
✓ Evidence verification
✓ Final answer
```

For a Hard question:

```text
Execution

✓ Question classified → HARD
✓ Query planning
✓ Retrieval
✓ Table query
✓ Re-retrieval
✓ Evidence verification
✓ Final answer
```

Do NOT display hidden chain-of-thought.

---

# 23. Related Questions

At the bottom:

```text
Related questions

→ What was the revenue growth by segment?
→ Which segment contributed the most?
→ Compare 2024 and 2025 operating income.
```

---

# 24. PDF Evidence Viewer

The Chat page can open a PDF evidence viewer.

Conceptual structure:

```text
┌──────────────────────────────────────────────┐
│ PDF Viewer          Page 28     [-] [+]      │
├──────────────────────────────────────────────┤
│                                              │
│              PDF PAGE                        │
│                                              │
│        highlighted evidence                  │
│                                              │
├──────────────────────────────────────────────┤
│ Search PDF...                  Page 28 / 120  │
└──────────────────────────────────────────────┘
```

Features:

- Page navigation
- Zoom
- Search
- Highlight relevant evidence
- Show page number
- Open source from citation

Implementation can use a PDF rendering library loaded on the frontend, while the UI itself remains HTML/CSS/Vanilla JS.

---

# 25. Page 2 — Documents

Files:

```text
pages/documents.html
css/pages/documents.css
js/pages/documents.js
```

Purpose:

Manage financial/business PDFs.

---

# 26. Document Upload

UI:

```text
┌───────────────────────────────────────────┐
│ Upload financial report                   │
│                                           │
│       Drag & Drop PDF                     │
│       or                                  │
│       [Choose File]                       │
│                                           │
└───────────────────────────────────────────┘
```

Display:

- Filename
- File size
- Upload progress
- Processing status
- Error status

---

# 27. Document List

Display:

```text
Documents

Search documents...

┌──────────────────────────────────────────────────────┐
│ Document                    Status       Pages       │
├──────────────────────────────────────────────────────┤
│ Apple 2025 Annual Report    ● Ready      120        │
│ Microsoft 2025 Report       ● Ready      140        │
│ Tesla 2025 Report           ◐ Processing  98         │
└──────────────────────────────────────────────────────┘
```

Filters:

- All
- Ready
- Processing
- Failed

---

# 28. Document Detail

Files:

```text
pages/document-detail.html
css/pages/document-detail.css
js/pages/document-detail.js
```

Sections:

```text
Document Overview

Processing Status

Document Structure

Tables

Extracted Data
```

---

# 29. Document Structure

Display hierarchical structure:

```text
Annual Report
│
├── Company Overview
├── Financial Highlights
├── Management Discussion
│   ├── Revenue
│   ├── Expenses
│   └── Operating Income
├── Financial Statements
│   ├── Income Statement
│   ├── Balance Sheet
│   └── Cash Flow
└── Notes
```

Purpose:

Demonstrate structure-aware PDF parsing.

---

# 30. Table Explorer

Show extracted tables:

```text
Tables

Table 01 — Consolidated Statements
Table 02 — Revenue by Segment
Table 03 — Operating Expenses
...
```

Clicking a table opens the structured table viewer.

---

# 31. DataFrame Viewer

Display:

```text
┌────────────┬──────────┬──────────┬──────────┐
│ Segment    │ 2023     │ 2024     │ 2025     │
├────────────┼──────────┼──────────┼──────────┤
│ Services   │ ...      │ ...      │ ...      │
│ Products   │ ...      │ ...      │ ...      │
└────────────┴──────────┴──────────┴──────────┘
```

Purpose:

Demonstrate that extracted tables are converted into structured data suitable for table-query reasoning.

---

# 32. Page 3 — Benchmark

Files:

```text
pages/benchmark.html
css/pages/benchmark.css
js/pages/benchmark.js
```

Purpose:

Compare FinRAG pipelines quantitatively.

---

# 33. Benchmark Header

Display:

```text
Benchmark

Dataset:
[ Financial QA v1 ▼ ]

Question Type:
[ All ▼ ]

Run:
[ Run Benchmark ]
```

---

# 34. Pipeline Cards

Four main pipelines:

```text
Naive RAG

Hybrid RAG

Agentic RAG

Adaptive Agentic RAG
```

Each card shows:

```text
Answer Accuracy
Citation Accuracy
Retrieval Performance
Latency
Model Usage
```

---

# 35. Comparison Table

```text
┌──────────────────────┬──────────┬──────────┬─────────┐
│ Pipeline             │ Accuracy │ Latency  │ Usage   │
├──────────────────────┼──────────┼──────────┼─────────┤
│ Naive RAG            │ ...      │ ...      │ ...     │
│ Hybrid RAG           │ ...      │ ...      │ ...     │
│ Agentic RAG          │ ...      │ ...      │ ...     │
│ Adaptive Agentic RAG │ ...      │ ...      │ ...     │
└──────────────────────┴──────────┴──────────┴─────────┘
```

---

# 36. Question Explorer

Allow selecting individual benchmark questions.

Display:

```text
Question

Expected Answer

Pipeline Outputs

Ground Truth

Evidence

Metrics
```

Useful for qualitative error analysis.

---

# 37. Page 4 — Analytics

Files:

```text
pages/analytics.html
css/pages/analytics.css
js/pages/analytics.js
```

Purpose:

Visualize research results.

---

# 38. Overview Metrics

Top-level cards:

```text
Answer Accuracy
Citation Accuracy
Retrieval Recall
Average Latency
Average Model Usage
Router Accuracy
```

---

# 39. Accuracy vs Latency

Visualization:

```text
Accuracy
   │
   │             ● Adaptive
   │       ● Agentic
   │
   │   ● Hybrid
   │
   │ ● Naive
   └──────────────────────── Latency
```

Purpose:

Demonstrate the central contribution:

> Maintain high answer quality while reducing unnecessary agentic execution.

---

# 40. Retrieval Analytics

Display:

- Recall@K
- Precision@K
- MRR
- Hit Rate
- BM25 performance
- Dense retrieval performance
- Hybrid retrieval performance
- Reranking improvement

---

# 41. Router Analytics

Display:

```text
Predicted     Actual

Easy          Easy
Easy          Medium
Medium        Medium
Hard          Hard
...
```

Include:

- Router accuracy
- Per-class precision
- Per-class recall
- Confusion matrix
- Routing distribution

---

# 42. Ablation

Display comparisons such as:

```text
Full System

- Without Reranker

- Without Table Query

- Without Verification

- Without Adaptive Router

- Without Re-retrieval
```

Show impact on:

- Answer accuracy
- Citation correctness
- Latency
- Model usage

---

# 43. Error Analysis

Question categories:

```text
Retrieval Error
Table Extraction Error
Routing Error
Reasoning Error
Citation Error
Verification Error
Other
```

Allow filtering by:

- Pipeline
- Question type
- Difficulty
- Error category

---

# 44. Page 5 — Settings

Files:

```text
pages/settings.html
css/pages/settings.css
js/pages/settings.js
```

Settings sections:

```text
Model

Retrieval

Reranking

Adaptive Routing

Agent

Verification

Experiment

Cache
```

---

# 45. Model Settings

Display:

```text
LLM Provider
Model
Temperature
Max Tokens
```

---

# 46. Retrieval Settings

Display:

```text
BM25: ON

Dense Retrieval: ON

Hybrid RRF: ON

Reranker: ON

Top K: 10

Rerank K: 5
```

---

# 47. Agent Settings

Display:

```text
Agentic Reasoning: ON

Maximum Steps: 4

Re-retrieval: ON

Calculator Tool: ON

Table Query Tool: ON
```

---

# 48. Verification Settings

Display:

```text
Evidence Verification: ON

Citation Checker: ON

Minimum Evidence Score: ...
```

---

# 49. Experiment Settings

Display:

```text
Experiment ID

Dataset

Random Seed

Run Configuration

Cache LLM Responses
```

Purpose:

Support reproducible experiments.

---

# 50. API Integration

JavaScript API layer:

```text
js/api/
├── client.js
├── chat.js
├── documents.js
├── benchmark.js
└── analytics.js
```

## client.js

Responsible for:

- Base API URL
- HTTP requests
- Headers
- Error handling
- Response parsing

Example architecture:

```text
chat.js
    ↓
client.js
    ↓
FastAPI
```

The page-specific JavaScript should NOT directly contain repeated `fetch()` logic.

---

# 51. API Responsibilities

## Chat API

UI needs endpoints for:

```text
POST /api/chat
GET  /api/documents
GET  /api/documents/{id}
```

Chat response should contain enough structured information for the UI to render:

```text
answer
difficulty
route_confidence
key_numbers
calculation
table_result
evidence
citations
verification
action_trace
related_questions
latency
```

Do not return hidden chain-of-thought.

---

## Documents API

Support:

```text
POST /api/documents/upload

GET /api/documents

GET /api/documents/{id}

GET /api/documents/{id}/structure

GET /api/documents/{id}/tables

GET /api/documents/{id}/pdf
```

---

## Benchmark API

Support:

```text
GET  /api/benchmark/summary

GET  /api/benchmark/questions

GET  /api/benchmark/questions/{id}

POST /api/benchmark/run
```

---

## Analytics API

Support:

```text
GET /api/analytics/overview

GET /api/analytics/retrieval

GET /api/analytics/router

GET /api/analytics/ablation

GET /api/analytics/errors
```

---

# 52. JavaScript Page Responsibilities

## chat.js

Responsible for:

- Submit question
- Render user message
- Render answer
- Render route badge
- Render key numbers
- Render calculation
- Render table result
- Render verification
- Render evidence
- Render action trace
- Open PDF evidence
- Render related questions

---

## documents.js

Responsible for:

- Upload document
- Display document list
- Search/filter documents
- Show processing status
- Navigate to document detail

---

## document-detail.js

Responsible for:

- Load document metadata
- Load processing status
- Render document structure
- Render extracted tables
- Open table viewer
- Open PDF

---

## benchmark.js

Responsible for:

- Load benchmark data
- Apply filters
- Render pipeline cards
- Render comparison table
- Render question explorer
- Trigger benchmark run

---

## analytics.js

Responsible for:

- Load metrics
- Render overview cards
- Render charts
- Render retrieval analytics
- Render router analytics
- Render ablation results
- Render error analysis

Charts should be implemented with a lightweight charting library only if necessary. The application architecture remains Vanilla JavaScript.

---

## settings.js

Responsible for:

- Load configuration
- Render settings
- Update configuration
- Save experiment settings
- Manage cache settings

---

# 53. Utility Layer

```text
js/utils/
├── dom.js
├── format.js
└── storage.js
```

## dom.js

Reusable DOM helpers:

- Create elements
- Query elements
- Add/remove classes
- Event helpers

## format.js

Formatting:

- Numbers
- Currency
- Percentages
- Dates
- Latency
- File sizes

## storage.js

Local browser storage for non-sensitive UI preferences:

- Selected document
- Theme
- UI preferences
- Last selected benchmark

Do not store sensitive credentials.

---

# 54. CSS Architecture

CSS loading order:

```text
main.css
    ↓
base/
    ↓
layout/
    ↓
components/
    ↓
pages/
```

## main.css

Acts as the central stylesheet entry point.

Example:

```css
@import url("./base/variables.css");
@import url("./base/reset.css");
@import url("./base/typography.css");

@import url("./layout/shell.css");
@import url("./layout/sidebar.css");
@import url("./layout/topbar.css");
@import url("./layout/responsive.css");

@import url("./components/buttons.css");
@import url("./components/cards.css");
@import url("./components/badges.css");
@import url("./components/inputs.css");
@import url("./components/tables.css");
@import url("./components/modals.css");
@import url("./components/alerts.css");

@import url("./pages/chat.css");
@import url("./pages/documents.css");
@import url("./pages/document-detail.css");
@import url("./pages/benchmark.css");
@import url("./pages/analytics.css");
@import url("./pages/settings.css");
```

---

# 55. UI States

Every major component should support:

## Loading

```text
Loading...
```

or skeleton loading.

## Empty

```text
No documents found.
```

## Success

```text
✓ Completed
```

## Error

```text
Something went wrong.
Try again.
```

## Processing

```text
◐ Processing document...
```

## Disabled

Buttons and controls should visually communicate disabled state.

## Insufficient Evidence

```text
⚠ Insufficient evidence

FinRAG could not find enough reliable evidence
to support this answer.
```

---

# 56. Accessibility

Minimum requirements:

- Semantic HTML
- Keyboard navigation
- Visible focus states
- Accessible button labels
- Proper form labels
- Sufficient text contrast
- Table headers
- `aria` attributes where appropriate
- Avoid information conveyed only through color

Difficulty should not rely only on color.

Example:

```text
● EASY
● MEDIUM
● HARD
```

rather than using only green/yellow/red.

---

# 57. Responsive Design

Primary target:

```text
Desktop
```

Secondary:

```text
Tablet
Small laptop
```

Mobile is not a primary target because FinRAG is an analytics/research interface.

Responsive behavior:

- Sidebar collapses
- Tables become horizontally scrollable
- PDF viewer becomes full-screen
- Analytics cards stack vertically
- Chat content remains readable
- Topbar controls wrap or collapse

---

# 58. UI ↔ FinRAG Feature Mapping

| FinRAG Backend Feature | UI |
|---|---|
| PDF parser | Document Processing |
| Structure-aware parser | Document Structure |
| Text/table separation | Document Detail |
| Structure-aware chunks | Document Structure / Metadata |
| BM25 | Action Trace / Retrieval Analytics |
| Dense retrieval | Action Trace / Retrieval Analytics |
| Hybrid RRF | Action Trace / Retrieval Analytics |
| Cross-encoder reranker | Action Trace / Retrieval Analytics |
| Difficulty router | Route Badge |
| Easy route | Answer Card |
| Medium route | Calculation / Table Result |
| Hard route | Action Trace |
| Calculator | Calculation Card |
| Table Query | Table Result |
| Agent loop | Action Trace |
| Re-retrieval | Action Trace |
| Evidence store | Evidence Panel |
| Citation checker | Verification |
| Benchmark | Benchmark Page |
| Router metrics | Router Analytics |
| Retrieval metrics | Retrieval Analytics |
| Ablation | Ablation Section |
| Error taxonomy | Error Analysis |
| Experiment logs | Analytics / Settings |
| LLM response cache | Settings |

---

# 59. Implementation Priority

## P0 — Core Demo

Must be implemented first:

```text
UI-001  App Shell
UI-002  Sidebar
UI-003  Topbar
UI-004  Chat Empty State
UI-005  Document Selector
UI-006  Question Input
UI-007  User Question
UI-008  Route Badge
UI-009  Answer Card
UI-010  Key Numbers
UI-011  Calculation Card
UI-012  Table Result
UI-013  Verification Status
UI-014  Evidence Panel
UI-015  Action Trace
UI-016  Related Questions
UI-017  PDF Evidence Viewer
```

P0 goal:

> A user can select a financial PDF, ask a question, receive an answer, inspect its difficulty route, evidence, citation, and execution trace.

---

# 60. P1 — Research Interface

After P0:

```text
UI-018  Document Upload
UI-019  Document List
UI-020  Document Detail
UI-021  Document Structure
UI-022  Table Explorer
UI-023  DataFrame Viewer

UI-024  Benchmark Header
UI-025  Pipeline Cards
UI-026  Benchmark Comparison
UI-027  Question Explorer

UI-028  Analytics Overview
UI-029  Accuracy vs Latency
UI-030  Retrieval Analytics
UI-031  Router Analytics
UI-032  Ablation
UI-033  Error Analysis
```

---

# 61. P2 — Configuration

```text
UI-034  Settings
UI-035  Model Settings
UI-036  Retrieval Settings
UI-037  Agent Settings
UI-038  Verification Settings
UI-039  Experiment Settings
UI-040  Cache Settings
```

---

# 62. P3 — Polish

Optional improvements:

- Better animations
- Keyboard shortcuts
- More detailed PDF interactions
- Advanced table interactions
- Export benchmark results
- Export analytics
- Dark mode
- More responsive layouts

Do not implement P3 before P0/P1 are stable.

---

# 63. Definition of Done

## P0

The UI is considered complete when:

- User can select a document
- User can submit a question
- UI displays the answer
- UI displays Easy / Medium / Hard
- UI displays key numbers when applicable
- UI displays calculation when applicable
- UI displays table results when applicable
- UI displays evidence
- UI displays citations
- UI displays verification status
- UI displays high-level action trace
- User can open the relevant PDF page
- Loading/error/empty states work

## P1

The research UI is considered complete when:

- User can upload PDFs
- User can inspect document structure
- User can inspect extracted tables
- User can inspect structured table data
- User can compare four pipelines
- User can inspect benchmark questions
- User can view retrieval metrics
- User can view router metrics
- User can view ablation results
- User can inspect error categories

## P2

Configuration is complete when:

- Model configuration is visible
- Retrieval configuration is visible
- Agent configuration is visible
- Verification configuration is visible
- Experiment configuration is visible
- Cache configuration is visible

---

# 64. Final UI Architecture

```text
                         FinRAG UI
                            │
             ┌──────────────┴──────────────┐
             │                             │
          HTML5                          CSS3
             │                             │
             └──────────────┬──────────────┘
                            │
                     Vanilla JavaScript
                            │
             ┌──────────────┼──────────────┐
             │              │              │
           Pages       Components         API
             │              │              │
      ┌──────┼──────┐       │        ┌────┼─────┐
      │      │      │       │        │    │     │
    Chat   Docs  Benchmark  │      Chat Docs Benchmark
      │      │      │       │        │    │     │
      └──────┴──────┴───────┴────────┴────┴─────┘
                            │
                         FastAPI
                            │
                       FinRAG Core
```

The UI should prioritize **clarity of the FinRAG research contribution** over visual complexity.

The most important user-facing story is:

```text
Question
   ↓
Difficulty Routing
   ↓
Appropriate Retrieval / Tool / Agent Pipeline
   ↓
Evidence
   ↓
Verification
   ↓
Answer
```

The Benchmark and Analytics pages then provide quantitative evidence that the adaptive approach improves the accuracy–reliability–efficiency trade-off.
