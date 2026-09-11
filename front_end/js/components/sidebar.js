export function renderSidebar(active = "chat") {
  const root = window.location.pathname.includes("/pages/") ? "../" : "";
  const items = [
    ["chat", "⌂", "Chat & QA", `${root}index.html`],
    ["documents", "▤", "Documents", `${root}pages/documents.html`],
    ["benchmark", "◒", "Benchmark", `${root}pages/benchmark.html`],
    ["analytics", "⌁", "Analytics", `${root}pages/analytics.html`],
    ["settings", "⚙", "Settings", `${root}pages/settings.html`],
  ];
  return `<aside class="sidebar"><div class="brand"><span class="brand-mark">◈</span><span>FinRAG<small>Adaptive RAG for<br>Financial Reports</small></span></div><div class="nav-label">WORKSPACE</div><nav>${items.map(([id, icon, label, url]) => `<a class="${active === id ? "active" : ""}" href="${url}"><span class="nav-icon">${icon}</span>${label}</a>`).join("")}</nav><div class="routing"><strong>⚡ Adaptive Routing</strong><p>Automatically chooses the right reasoning strategy.</p><div class="route-row"><span>🟢 Easy</span><span>RAG</span></div><div class="route-row"><span>🟡 Medium</span><span>RAG + Tools</span></div><div class="route-row"><span>🟣 Hard</span><span>Agentic</span></div></div><div class="document-status"><small>CURRENT DOCUMENT</small><strong>Annual_Report_2024.pdf</strong><span>68 pages · 42 tables</span><em class="ready">● Processed</em></div></aside>`;
}
