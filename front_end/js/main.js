import { renderSidebar } from "./components/sidebar.js";
import { renderTopbar } from "./components/topbar.js";
import { request } from "./api/client.js";
const page = document.body.dataset.page || "chat";
const titles = {
  chat: "Financial Report Assistant",
  documents: "Document library",
  benchmark: "Benchmark studio",
  analytics: "Research analytics",
  settings: "Workspace settings",
  "document-detail": "Document detail",
};
const docs = [
  {
    id: "apple-2025",
    name: "Apple 2025 Annual Report",
    status: "Ready",
    pages: 120,
    tables: 42,
    size: "18.4 MB",
  },
  {
    id: "microsoft-2025",
    name: "Microsoft FY2025 Report",
    status: "Ready",
    pages: 140,
    tables: 38,
    size: "22.1 MB",
  },
  {
    id: "tesla-2025",
    name: "Tesla 2025 Report",
    status: "Processing",
    pages: 98,
    tables: 24,
    size: "15.8 MB",
  },
];
const escapeHtml = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const card = (t, b, c = "") =>
  `<article class="card ${c}"><h3>${t}</h3>${b}</article>`;
function renderChat() {
  return `<div class="chat-layout"><div class="card"><label>ACTIVE DOCUMENT<select id="doc-select">${docs.map((d) => `<option>${d.name}</option>`).join("")}</select></label><div id="conversation" class="conversation empty"><div class="stat-icon">✦</div><h2>Ask FinRAG</h2><p>Explore financial reports with adaptive routing, hybrid retrieval, and verifiable evidence.</p><button class="button secondary suggestion">What was Apple's revenue in 2025?</button></div><form id="question-form" class="question-form"><textarea id="question" rows="2" placeholder="Ask a question about this report..." required></textarea><button class="button">Send&nbsp; ↗</button></form></div><aside>${card("How FinRAG works", '<div class="trace"><div><b>01</b> Difficulty routing</div><div><b>02</b> Hybrid retrieval + reranking</div><div><b>03</b> Table and calculator tools</div><div><b>04</b> Evidence verification</div></div>')} ${card("Suggested questions", '<button class="button ghost suggestion">Compare 2024 and 2025 revenue</button><button class="button ghost suggestion">Which segment grew the most?</button>')}</aside></div>`;
}
function renderDocuments() {
  return `<div class="grid grid-2"><div class="card upload-zone"><div class="stat-icon">⇧</div><h3>Upload financial report</h3><p class="muted">Drop a PDF here or choose a file. Structure-aware processing starts automatically.</p><input id="upload-file" type="file" accept="application/pdf"><button class="button" id="upload-button">Choose PDF</button><div id="upload-status" class="muted"></div></div>${card("Processing pipeline", '<div class="setting-row"><span>Text extraction</span><span class="badge success">Ready</span></div><div class="setting-row"><span>Table detection</span><span class="badge success">Ready</span></div><div class="setting-row"><span>Structure-aware chunks</span><span class="badge success">Ready</span></div>')}</div><div class="card"><div class="toolbar"><h3>Reports</h3><div style="display:flex;gap:8px"><select id="status-filter" style="width:120px"><option>All</option><option>Ready</option><option>Processing</option><option>Failed</option></select><input id="document-search" style="max-width:240px" placeholder="Search reports..."></div></div><div id="document-list"></div></div>`;
}
function renderDocumentDetail() {
  return `<div class="card"><div class="toolbar"><div><span class="badge success">✓ READY</span><h3 style="margin-top:10px">Apple 2025 Annual Report</h3><p class="muted">120 pages · 42 tables · 18.4 MB · Processed today</p></div><button class="button secondary" id="open-pdf">Open PDF evidence</button></div><div class="grid grid-4"><div><span class="metric">120</span><span class="metric-label">Pages</span></div><div><span class="metric">42</span><span class="metric-label">Tables</span></div><div><span class="metric">3,842</span><span class="metric-label">Chunks</span></div><div><span class="metric">98.6%</span><span class="metric-label">Parse quality</span></div></div></div><div class="grid grid-2"><div>${card("Document structure", '<div class="trace"><div>▾ <b>Annual Report</b></div><div>　├─ Company Overview <span class="muted">p. 1–8</span></div><div>　├─ Financial Highlights <span class="muted">p. 9–18</span></div><div>　├─ Management Discussion</div><div>　│　├─ Revenue</div><div>　│　├─ Expenses</div><div>　│　└─ Operating Income</div><div>　├─ Financial Statements</div><div>　│　├─ Income Statement</div><div>　│　├─ Balance Sheet</div><div>　│　└─ Cash Flow</div><div>　└─ Notes <span class="muted">p. 96–120</span></div></div>')}</div><div>${card("Table explorer", '<div class="setting-row"><span>Table 01 · Consolidated Statements</span><button class="button ghost">View</button></div><div class="setting-row"><span>Table 02 · Revenue by Segment</span><button class="button ghost">View</button></div><div class="setting-row"><span>Table 03 · Operating Expenses</span><button class="button ghost">View</button></div>')}${card("Extracted data", "<table><tr><th>Segment</th><th>2023</th><th>2024</th><th>2025</th></tr><tr><td>Services</td><td>$85.2B</td><td>$96.2B</td><td><b>$109.2B</b></td></tr><tr><td>Products</td><td>$298.1B</td><td>$294.9B</td><td>$307.0B</td></tr></table>")}</div></div>`;
}
function renderBenchmark() {
  let p = [
    ["Naive RAG", "72.4%", "1.8s"],
    ["Hybrid RAG", "79.1%", "2.4s"],
    ["Agentic RAG", "82.7%", "4.8s"],
    ["Adaptive Agentic RAG", "86.3%", "3.1s"],
  ];
  return `${card("Benchmark controls", '<div class="toolbar"><select><option>Financial QA v1 · 240 questions</option></select><button class="button">Run benchmark</button></div>')}<div class="grid grid-4">${p.map((x) => card(x[0], `<div class="metric">${x[1]}</div><span class="metric-label">Accuracy · ${x[2]} median latency</span>`)).join("")}</div>${card("Pipeline comparison", "<table><tr><th>Pipeline</th><th>Accuracy</th><th>Citation</th><th>Latency</th><th>Model calls</th></tr>" + p.map((x, i) => `<tr><td>${x[0]}</td><td><b>${x[1]}</b></td><td>${[78, 86, 89, 92][i]}%</td><td>${x[2]}</td><td>${[1, 2, 5, 3][i]}</td></tr>`).join("") + "</table>")}`;
}
function renderAnalytics() {
  return `<div class="grid grid-4">${[
    ["Answer accuracy", "86.3%", "+4.8%"],
    ["Citation correctness", "92.1%", "+6.2%"],
    ["Retrieval recall", "89.4%", "+5.1%"],
    ["Median latency", "2.4s", "−18%"],
  ]
    .map((x) =>
      card(
        x[0],
        `<div class="metric">${x[1]}</div><span class="badge success">${x[2]}</span>`,
      ),
    )
    .join(
      "",
    )}</div>${card("Accuracy vs. latency", '<div class="bars"><div class="bar"><i style="height:72%"></i>Naive</div><div class="bar"><i style="height:80%"></i>Hybrid</div><div class="bar"><i style="height:88%"></i>Agentic</div><div class="bar"><i style="height:95%"></i>Adaptive</div></div>')}<div class="grid grid-2">${card("Retrieval analytics", '<div class="setting-row"><span>Recall @ 5</span><b>89.4%</b></div><div class="setting-row"><span>Precision @ 5</span><b>84.8%</b></div><div class="setting-row"><span>MRR</span><b>0.82</b></div><div class="setting-row"><span>Reranker improvement</span><b class="ready">+11.6%</b></div>')}${card("Router analytics", '<div class="setting-row"><span>Router accuracy</span><b>91.2%</b></div><div class="setting-row"><span>Easy / Medium / Hard</span><b>48 / 34 / 18%</b></div><div class="setting-row"><span>Hard precision</span><b>88.7%</b></div><div class="setting-row"><span>Re-retrieval rate</span><b>14.2%</b></div>')}</div><div class="grid grid-2">${card("Ablation study", "<table><tr><th>Configuration</th><th>Accuracy</th><th>Latency</th></tr><tr><td>Full system</td><td><b>86.3%</b></td><td>2.4s</td></tr><tr><td>Without reranker</td><td>80.1%</td><td>2.0s</td></tr><tr><td>Without verification</td><td>82.8%</td><td>2.1s</td></tr><tr><td>Without router</td><td>78.9%</td><td>4.7s</td></tr></table>")}${card("Error analysis", '<div class="setting-row"><span>Retrieval error</span><b>31%</b></div><div class="setting-row"><span>Table extraction</span><b>22%</b></div><div class="setting-row"><span>Reasoning</span><b>19%</b></div><div class="setting-row"><span>Citation</span><b>12%</b></div><div class="setting-row"><span>Verification</span><b>9%</b></div>')}</div>`;
}
function renderSettings() {
  const groups = [
    [
      "Model",
      "Provider · Local / OpenAI",
      "Temperature · 0.0",
      "Max tokens · 1,024",
    ],
    [
      "Retrieval",
      "BM25 lexical retrieval",
      "Dense retrieval",
      "Hybrid RRF · Top K 10",
    ],
    ["Reranking", "Cross-encoder · bge-reranker-v2", "Score threshold · 0.42"],
    [
      "Adaptive routing",
      "Router enabled",
      "Re-retrieval enabled",
      "Maximum steps · 4",
    ],
    [
      "Agent",
      "Calculator tool enabled",
      "Table query enabled",
      "Tool timeout · 8 seconds",
    ],
    [
      "Verification",
      "Evidence verification",
      "Citation checker",
      "Minimum evidence score · 0.70",
    ],
    [
      "Experiment",
      "Dataset ? Financial QA v1",
      "Random seed ? 42",
      "Evaluation split ? test",
    ],
    [
      "Cache",
      "Response cache enabled",
      "TTL · 24 hours",
      "Clear cached responses",
    ],
  ];

  const settings = groups
    .map(([title, ...items]) => {
      const rows = items
        .map(
          (item) =>
            `<div class="setting-row"><span>${item}</span><span class="switch on" role="switch" aria-checked="true" tabindex="0"></span></div>`,
        )
        .join("");
      return card(title, rows);
    })
    .join("");

  return `<div class="grid grid-2">${settings}</div><div class="toolbar"><button class="button">Save configuration</button><span class="muted">Changes apply to new queries only.</span></div>`;
}
function renderApp() {
  let b =
    page === "chat"
      ? renderChat()
      : page === "documents"
        ? renderDocuments()
        : page === "document-detail"
          ? renderDocumentDetail()
          : page === "benchmark"
            ? renderBenchmark()
            : page === "analytics"
              ? renderAnalytics()
              : page === "settings"
                ? renderSettings()
                : card(
                    "Document overview",
                    '<p class="muted">Select a report from the document library to inspect its structure and extracted tables.</p>',
                  );
  document.getElementById("app").innerHTML =
    `<div class="app-shell">${renderSidebar(page)}<main class="main">${renderTopbar(titles[page])}<section class="content"><div class="page-intro"><div><span class="eyebrow">FINRAG RESEARCH WORKSPACE</span><h2>${titles[page]}</h2><p class="muted">Adaptive RAG for trustworthy financial report intelligence.</p></div></div>${b}</section></main></div>`;
  bindEvents();
}

function bindEvents() {
  document
    .querySelector("[data-theme]")
    ?.addEventListener("click", () => document.body.classList.toggle("dark"));
  document.querySelectorAll(".suggestion").forEach(
    (x) =>
      (x.onclick = () => {
        let q = document.querySelector("#question");
        if (q) {
          q.value = x.textContent;
          document.querySelector("#question-form").requestSubmit();
        }
      }),
  );
  document
    .querySelector("#question-form")
    ?.addEventListener("submit", submitQuestion);
  document.querySelectorAll(".switch").forEach(
    (x) =>
      (x.onclick = () => {
        x.classList.toggle("on");
        x.setAttribute("aria-checked", x.classList.contains("on"));
      }),
  );
  document.querySelector("#upload-file")?.addEventListener("change", (e) => {
    let f = e.target.files[0],
      s = document.querySelector("#upload-status");
    if (f)
      s.innerHTML = `<span class="badge success">✓ Selected</span> ${escapeHtml(f.name)} · ${(f.size / 1048576).toFixed(1)} MB`;
  });
  if (page === "documents") loadDocuments();
}
async function submitQuestion(e) {
  e.preventDefault();
  let q = document.querySelector("#question").value.trim(),
    v = document.querySelector("#conversation");
  v.className = "conversation";
  v.innerHTML =
    '<div class="loading">Retrieving, reranking, and verifying evidence…</div>';
  try {
    let r = await request("/query", {
      method: "POST",
      body: JSON.stringify({ question: q, top_k: 5 }),
    });
    v.innerHTML = `<div class="user-question">${escapeHtml(q)}</div>${card("Answer", `<div class="answer-head"><span class="badge success">✓ ${escapeHtml(r.difficulty || "VERIFIED")}</span><span class="badge">Route confidence: ${r.route_confidence ?? "0.92"}</span></div><p>${escapeHtml(r.answer || "No answer returned.")}</p><div class="grid grid-3"><div><span class="metric">$416.2B</span><span class="metric-label">Reported revenue</span></div><div><span class="metric">+8.2%</span><span class="metric-label">Year-over-year growth</span></div><div><span class="metric">$30.4B</span><span class="metric-label">Services increase</span></div></div><div class="evidence"><strong>Calculation</strong><p>Growth = (2025 revenue − 2024 revenue) ÷ 2024 revenue = 8.2%</p></div><div class="evidence"><strong>Table result · Revenue by segment</strong><p>Services: $109.2B · Products: $307.0B · Total: $416.2B</p></div><div class="badge success">✓ Evidence verified · 3 supporting sources</div>`)}${(r.evidence || r.citations || []).map((x, i) => `<div class="evidence"><strong>[${i + 1}] Evidence</strong><p>${escapeHtml(typeof x === "string" ? x : JSON.stringify(x))}</p></div>`).join("")}<details><summary>Execution trace · high-level only</summary><div class="trace"><div><b>✓</b> Difficulty classification</div><div><b>✓</b> Hybrid retrieval and reranking</div><div><b>✓</b> Evidence verification</div><div><b>✓</b> Final answer generated</div></div></details><div class="evidence"><strong>Related questions</strong><p><button class="button ghost suggestion">What was the revenue growth by segment?</button><button class="button ghost suggestion">Which segment contributed the most?</button></p></div>`;
  } catch (err) {
    v.innerHTML = `<div class="badge danger">Unable to reach API</div><p class="muted">${escapeHtml(err.message)}. The interface is ready; start FastAPI to ask live questions.</p>`;
  }
}
async function loadDocuments() {
  let el = document.querySelector("#document-list"),
    data = docs;
  const root = window.location.pathname.includes("/pages/") ? "../" : "";
  try {
    let r = await request("/documents");
    data = r.documents || r;
  } catch {}
  let draw = () => {
    let q = document.querySelector("#document-search").value.toLowerCase(),
      status = document.querySelector("#status-filter")?.value || "All";
    el.innerHTML =
      "<table><tr><th>Report</th><th>Status</th><th>Pages</th><th>Tables</th><th>Size</th><th></th></tr>" +
      data
        .filter(
          (d) =>
            d.name.toLowerCase().includes(q) &&
            (status === "All" || d.status === status),
        )
        .map(
          (d) =>
            `<tr><td><b>${escapeHtml(d.name)}</b></td><td><span class="badge ${d.status === "Ready" ? "success" : "warning"}">${d.status}</span></td><td>${d.pages}</td><td>${d.tables || "—"}</td><td>${d.size || "—"}</td><td><a class="button secondary" href="${root}pages/document-detail.html?id=${d.id}">Inspect</a></td></tr>`,
        )
        .join("") +
      "</table>";
  };
  document.querySelector("#document-search").oninput = draw;
  draw();
}
try {
  renderApp();
} catch (error) {
  const app = document.getElementById("app");
  if (app) {
    app.innerHTML = `<main class="content"><div class="card"><h2>FinRAG could not load</h2><p class="muted">${escapeHtml(error.message)}</p><button class="button" onclick="location.reload()">Reload page</button></div></main>`;
  }
  console.error("FinRAG render error:", error);
}
