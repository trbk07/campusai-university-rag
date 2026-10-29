// All dynamic HTML passes through esc(). SVG strings below are trusted constants.
export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
export const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths = {
  cap:'<path d="m2 9 10-5 10 5-10 5L2 9Z"/><path d="M6 11v6c4 3 8 3 12 0v-6M2 9v8"/><circle cx="2" cy="19" r="1"/>',
  file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"/><path d="M14 2v6h6M8 13h8M8 17h6"/>',
  chat:'<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2v-9.5A8.5 8.5 0 1 1 21 11.5Z"/><path d="M7 9h9M7 13h6"/>',
  collection:'<rect x="3" y="4" width="7" height="7" rx="1.5"/><rect x="14" y="4" width="7" height="7" rx="1.5"/><rect x="3" y="15" width="7" height="7" rx="1.5"/><rect x="14" y="15" width="7" height="7" rx="1.5"/>',
  help:'<circle cx="12" cy="12" r="9"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2-3 4M12 17h.01"/>',
  search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  monitor:'<rect x="3" y="3" width="18" height="13" rx="2"/><path d="M8 21h8M12 16v5"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  shield:'<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6l8-4Z"/><path d="m8 12 3 3 5-6"/>',
  layers:'<path d="m12 3 10 5-10 5L2 8l10-5ZM2 12l10 5 10-5M2 16l10 5 10-5"/>',
  sparkles:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3ZM20 2v4M18 4h4"/>',
  'arrow-right':'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  'chevron-down':'<path d="m6 9 6 6 6-6"/>',
  upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
  paperclip:'<path d="m21 11-9 9a6 6 0 0 1-8.5-8.5l10-10a4 4 0 0 1 5.5 5.5l-10 10a2 2 0 0 1-2.8-2.8l9-9"/>',
  send:'<path d="m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13"/>',
  panel:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M15 3v18M18 8h.01M18 12h.01"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
  'check-circle':'<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  source:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h6M8 15h4"/>',
  'thumb-up':'<path d="M7 10H3v11h4M7 10l5-8a3 3 0 0 1 2 3l-1 5h6a2 2 0 0 1 2 2l-2 8a2 2 0 0 1-2 1H7V10Z"/>',
  'thumb-down':'<path d="M7 14H3V3h4M7 14l5 8a3 3 0 0 0 2-3l-1-5h6a2 2 0 0 0 2-2l-2-8a2 2 0 0 0-2-1H7v11Z"/>',
  copy:'<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
  trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
  refresh:'<path d="M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 14 6M4 12a8 8 0 0 0 14 6"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  external:'<path d="M14 3h7v7M10 14 21 3M21 14v7H3V3h7"/>',
  eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  user:'<circle cx="12" cy="8" r="3"/><path d="M5 21v-3a7 7 0 0 1 14 0v3"/>'
};
export const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.file}</svg>`;
export function hydrate(root = document) { $$('[data-icon]', root).forEach(el => { el.innerHTML = icon(el.dataset.icon); }); }
export const pdfIcon = () => `<span class="pdf-icon" aria-hidden="true">${icon('file')}<small>PDF</small></span>`;
export const events = new EventTarget();
export const state = {documents:[], jobs:[], selected:new Set(), tab:'assistant', category:'all', search:'', year:'', program:'', status:'all', loading:true, error:'', busy:false, aiConfigured:false, queryStreaming:false, queryTimeoutMs:45000, replyLanguage:'vi', uploadAvailable:false, limits:{max_mb:50,max_pages:218}};
export const notify = name => events.dispatchEvent(new Event(name));
export const date = seconds => seconds ? new Date(seconds * 1000).toLocaleDateString('vi-VN', {timeZone:'Asia/Bangkok'}) : 'Chưa có ngày tải';
export const bytes = size => size == null ? '' : size > 1048576 ? `${(size / 1048576).toFixed(1)} MB` : `${Math.ceil(size / 1024)} KB`;
let toastTimer;
export function toast(text) { $('#toast').textContent = text; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 3500); }
export function showDialog(id) { const dialog = $(`#${id}`); if (!dialog.open) dialog.showModal(); }
export function closeDialog(dialog) { dialog.close(); if (dialog.id === 'preview-dialog') $('#preview-body').replaceChildren(); }
export function selectDocument(id, checked) { checked ? state.selected.add(id) : state.selected.delete(id); notify('selection'); }
export function route(tab) { location.hash = tab; }
export function empty(title, text, action = '') { return `<div class="empty-state"><div class="empty-icon">${icon('file')}</div><h2>${esc(title)}</h2><p>${esc(text)}</p>${action}</div>`; }
