import {$, $$, esc, icon, pdfIcon, state, events, notify, date, bytes, toast, showDialog, closeDialog, selectDocument, route, empty} from '../scripts/shared.js';
import {request, post, upload, errorText} from '../scripts/api.js';

export const groups = [
  {id:'all', label:'Tất cả tài liệu', icon:'collection'},
  {id:'courses', label:'Học phần & chương trình', icon:'file', types:['curriculum','syllabus','course_catalog']},
  {id:'regulations', label:'Quy chế & quy định', icon:'shield', types:['regulation']},
  {id:'finance', label:'Học phí & tài chính', icon:'file', types:['tuition','financial']},
  {id:'guide', label:'Hướng dẫn sinh viên', icon:'source', types:['handbook','guide']},
  {id:'other', label:'Khác', icon:'layers', types:['academic_notice','other']},
  {id:'unclassified', label:'Chưa phân loại', icon:'file', types:[]},
];
export const groupFor = doc => groups.find(group => group.types?.includes(doc.metadata.document_type)) || groups.at(-1);
export const readySelected = () => state.documents.filter(doc => doc.ready && state.selected.has(doc.doc_id));
const groupCount = group => group.id === 'all' ? state.documents.length : state.documents.filter(doc => groupFor(doc).id === group.id).length;
const uploadButton = '<button class="button primary upload-trigger">'+icon('upload')+'Tải tài liệu PDF đầu tiên</button>';
const MAX_UPLOAD_FILES = 5;
let files = [], uploading = false, deleteId = null, pollingTimer = null, pollingStarted = 0, refreshing = false;

export function badge(doc) {
  if (doc.deleting) return `<span class="status-badge status-pending">${icon('info')}${doc.delete_failed ? 'Xóa chưa thành công' : 'Đang xóa...'}</span>`;
  const ready = doc.ready, review = doc.status === 'review_required';
  return `<span class="status-badge ${ready ? 'status-ready' : review ? 'status-review' : 'status-pending'}">${icon(ready ? 'check-circle' : 'info')}${ready ? 'Sẵn sàng' : review ? 'Cần kiểm tra' : 'Chưa sẵn sàng'}</span>`;
}
function filtered() {
  const needle = state.search.toLocaleLowerCase('vi');
  return state.documents.filter(doc => (state.category === 'all' || groupFor(doc).id === state.category)
    && (!needle || `${doc.name} ${Object.values(doc.metadata).join(' ')}`.toLocaleLowerCase('vi').includes(needle))
    && (!state.year || String(doc.metadata.academic_year) === state.year)
    && (!state.program || String(doc.metadata.program) === state.program)
    && (state.status === 'all' || (state.status === 'ready' ? doc.ready : !doc.ready)));
}
function renderSidebar() {
  $('#categories').innerHTML = groups.map(group => `<button class="category-button ${state.category === group.id ? 'active' : ''}" data-category="${group.id}" ${state.loading ? 'disabled' : ''} ${state.category === group.id ? 'aria-current="true"' : ''}>${icon(group.icon)}<span>${group.label}</span><span class="count">${state.loading ? '…' : groupCount(group)}</span></button>`).join('');
  $('#recent-documents').setAttribute('aria-busy',String(state.loading));
  $('#recent-documents').innerHTML = state.loading
    ? Array.from({length:4},() => '<div class="recent-item recent-placeholder" aria-hidden="true"><span class="pdf-icon"></span><span class="recent-text"><span></span><span></span></span></div>').join('')
    : state.documents.slice(0,4).map(doc => `<button class="recent-item" data-detail="${esc(doc.doc_id)}">${pdfIcon()}<span class="recent-text"><strong>${esc(doc.name)}</strong><small>${date(doc.uploaded_at)}${state.selected.has(doc.doc_id) ? ' · Đã chọn' : ''}</small></span></button>`).join('') || '<p class="sidebar-empty">Tài liệu bạn tải lên sẽ xuất hiện ở đây.</p>';
  $$('.upload-trigger').forEach(button => { button.disabled = !state.uploadAvailable; });
}
function options(key) { return [...new Set(state.documents.map(doc => doc.metadata[key]).filter(value => value != null))].sort().map(value => `<option value="${esc(value)}" ${String(value) === state[key === 'academic_year' ? 'year' : key] ? 'selected' : ''}>${esc(value)}</option>`).join(''); }
function renderControls() {
  $('#document-controls').innerHTML = `<div class="filter-bar"><label class="sr-only" for="document-search">Tìm trong tài liệu</label><input id="document-search" type="search" placeholder="Tìm tên tài liệu..." value="${esc(state.search)}"><label class="sr-only" for="year-filter">Năm học</label><select id="year-filter"><option value="">Tất cả năm học</option>${options('academic_year')}</select><label class="sr-only" for="program-filter">Chương trình</label><select id="program-filter"><option value="">Tất cả chương trình</option>${options('program')}</select><label class="sr-only" for="status-filter">Trạng thái</label><select id="status-filter"><option value="all">Mọi trạng thái</option><option value="ready" ${state.status === 'ready' ? 'selected' : ''}>Sẵn sàng</option><option value="pending" ${state.status === 'pending' ? 'selected' : ''}>Chưa sẵn sàng</option></select><button class="text-button" id="clear-filters">Xóa bộ lọc</button><button class="button secondary" id="ask-selected" ${readySelected().length ? '' : 'disabled'}>${icon('chat')}Hỏi với ${readySelected().length} tài liệu</button></div>`;
}
function renderList() {
  const target = $('#document-list');
  if (state.loading) { target.innerHTML = '<p class="loading-line"><span class="spinner" aria-hidden="true"></span>Đang tải tài liệu...</p>'; return; }
  if (state.error) { target.innerHTML = empty('Chưa tải được thư viện', state.error, '<button class="button secondary" data-refresh>Thử lại</button>'); return; }
  if (!state.documents.length) { target.innerHTML = empty('Bạn chưa có tài liệu nào.', 'Tải PDF đầu tiên. CampusAI sẽ chuẩn bị nội dung để bạn hỏi đáp và xem nguồn.', state.uploadAvailable ? uploadButton : '<p>Chức năng tải lên chưa khả dụng trong phiên này.</p>'); return; }
  const docs = filtered();
  target.innerHTML = `<p class="list-summary">${docs.length} tài liệu${state.category !== 'all' ? ` trong ${groups.find(g => g.id === state.category).label}` : ''} · ${readySelected().length} đã chọn để hỏi AI</p>` + (docs.length ? docs.map(doc => `<article class="document-card"><input type="checkbox" data-select="${esc(doc.doc_id)}" aria-label="Chọn ${esc(doc.name)}" ${state.selected.has(doc.doc_id) ? 'checked' : ''} ${doc.ready ? '' : 'disabled'}>${pdfIcon()}<div class="document-info"><h3>${esc(doc.name)}</h3><p>${esc(groupFor(doc).label)}${doc.metadata.academic_year ? ' · '+esc(doc.metadata.academic_year) : ''} · ${doc.page_count} trang${doc.size_bytes ? ' · '+bytes(doc.size_bytes) : ''}</p><p>${date(doc.uploaded_at)}</p></div><div class="document-actions">${badge(doc)}<button class="icon-button" data-detail="${doc.doc_id}" aria-label="Chi tiết ${esc(doc.name)}" title="Chi tiết tài liệu">${icon('info')}</button><button class="icon-button" data-preview="${doc.doc_id}" aria-label="Xem PDF ${esc(doc.name)}" title="Xem PDF gốc" ${doc.file_available ? '' : 'disabled'}>${icon('eye')}</button><button class="icon-button" data-delete="${doc.doc_id}" aria-label="Xóa ${esc(doc.name)}" title="Xóa tài liệu" ${doc.deleting && !doc.delete_failed ? 'disabled' : ''}>${icon('trash')}</button></div></article>`).join('') : empty('Không tìm thấy tài liệu phù hợp', 'Thử đổi từ khóa hoặc xóa bộ lọc.'));
}
function renderCollections() {
  const actual = groups.slice(1).filter(group => groupCount(group));
  $('#collection-list').innerHTML = actual.length ? actual.map((group,i) => `<button class="collection-card" data-category="${group.id}"><span class="feature-icon ${['blue','green','violet'][i%3]}">${icon(group.icon)}</span><h2>${group.label}</h2><p>${groupCount(group)} tài liệu · ${state.documents.filter(doc => groupFor(doc).id === group.id && doc.ready).length} sẵn sàng</p><span class="collection-bottom">Khám phá tài liệu${icon('arrow-right')}</span></button>`).join('') : empty(state.error ? 'Chưa tải được bộ sưu tập' : 'Tri thức bắt đầu từ tài liệu của bạn', state.error || 'Tài liệu được nhóm theo metadata thực. Nguồn chưa có loại xác định sẽ nằm trong “Chưa phân loại”.', state.error ? '<button class="button secondary" data-refresh>Thử lại</button>' : uploadButton);
}
function renderScope() {
  const focusedId = document.activeElement.closest('#scope-dialog')?.querySelector(':focus')?.dataset.select;
  $('#scope-documents').innerHTML = state.documents.length ? state.documents.map(doc => `<label class="scope-row"><input type="checkbox" data-select="${doc.doc_id}" ${state.selected.has(doc.doc_id) ? 'checked' : ''} ${doc.ready ? '' : 'disabled'}><span>${esc(doc.name)}<small>${doc.page_count} trang${doc.metadata.academic_year ? ' · '+esc(doc.metadata.academic_year) : ''}</small></span>${badge(doc)}</label>`).join('') : '<p class="muted">Chưa có tài liệu sẵn sàng. Hãy tải PDF và chờ xử lý hoàn tất.</p>';
  const chosen = readySelected();
  $('#scope-label').textContent = chosen.length === 1 ? chosen[0].name : chosen.length ? `${chosen.length} tài liệu đã chọn` : 'Chọn tài liệu để hỏi đáp';
  if (focusedId) $(`[data-select="${focusedId}"]`, $('#scope-documents'))?.focus();
}
const stageLabels = {receiving:'Đang nhận và lưu PDF',interrupted:'Tác vụ bị gián đoạn. Thử xử lý lại hoặc tải lại PDF gốc.',queued:'Đang chờ xử lý',validating:'Đang kiểm tra PDF',parsing:'Đang đọc nội dung',ocr:'Đang nhận diện chữ',detecting_metadata:'Đang nhận diện thông tin',extracting_tables:'Đang trích xuất bảng',chunking:'Đang tổ chức nội dung',persisting:'Đang lưu tài liệu',indexing:'Đang chuẩn bị tài liệu để hỏi đáp...',done:'Đã xử lý tài liệu',review_required:'Tài liệu cần được kiểm tra thêm',failed:'Xử lý chưa thành công. Hãy kiểm tra PDF.',cancelled:'Đã hủy xử lý'};
function renderJobs() {
  const jobs = state.jobs.filter(job => (job.state !== 'succeeded' || job.deleting) && !state.documents.some(doc => doc.doc_id === job.document_id && job.state === 'review_required'));
  const cards = jobs.map(job => `<article class="job-card"><strong>${esc(job.name)}</strong><p>${job.deleting ? job.delete_failed ? 'Xóa chưa thành công. Bạn có thể thử xóa lại.' : 'Đang dừng xử lý để xóa PDF...' : stageLabels[job.stage] || 'Đang xử lý tài liệu...'}</p><progress value="${Number(job.progress) || 0}" max="1" aria-label="Tiến độ xử lý ${esc(job.name)}"></progress>${!job.deleting && ['staging','queued','running'].includes(job.state) ? `<button class="text-button" data-job-cancel="${esc(job.job_id)}">Yêu cầu hủy</button>` : ''}${!job.deleting && job.state === 'failed' && job.retryable ? `<button class="text-button" data-job-retry="${esc(job.job_id)}">Thử xử lý lại</button>` : ''}<button class="text-button" data-delete="${esc(job.document_id)}" ${job.deleting && !job.delete_failed ? 'disabled' : ''}>${icon('trash')} ${job.delete_failed ? 'Thử xóa lại' : 'Xóa PDF'}</button></article>`).join('');
  $('#sidebar-jobs').innerHTML = cards; $('#document-jobs').innerHTML = cards;
}
function renderAll() { renderSidebar(); renderControls(); renderList(); renderScope(); renderCollections(); renderJobs(); notify('documents'); }
function schedulePoll() {
  clearTimeout(pollingTimer);
  const active = state.jobs.some(job => ['staging','queued','running'].includes(job.state) || (job.deleting && !job.delete_failed))
    || state.documents.some(doc => doc.deleting && !doc.delete_failed);
  if (!active) { pollingStarted = 0; return; }
  if (!pollingStarted) pollingStarted = Date.now();
  if (document.hidden) return;
  if (Date.now() - pollingStarted > 600000) { $('#document-jobs').insertAdjacentHTML('beforeend','<p class="inline-status">Đã dừng tự cập nhật sau 10 phút. <button class="text-button" data-refresh>Cập nhật trạng thái</button></p>'); return; }
  // Keep upload completion responsive while parsing/indexing is usually short;
  // reduce polling pressure for documents that need longer OCR or indexing.
  const pollDelay = Date.now() - pollingStarted < 60000 ? 1000 : 2000;
  pollingTimer = setTimeout(refreshDocuments, pollDelay);
}
export async function refreshDocuments() {
  if (refreshing) return;
  refreshing = true;
  try {
    const value = await request('/api/documents');
    state.documents = value.documents; state.jobs = value.jobs; state.limits = value.limits; state.uploadAvailable = value.upload_available; state.aiConfigured = value.runtime?.ai_configured === true; state.error = '';
    const valid = new Set(state.documents.filter(doc => doc.ready).map(doc => doc.doc_id));
    state.selected.forEach(id => { if (!valid.has(id)) state.selected.delete(id); });
    $('#upload-limits').textContent = `Tối đa ${MAX_UPLOAD_FILES} PDF mỗi lượt · ${state.limits.max_mb} MB / ${state.limits.max_pages} trang mỗi file`;
  } catch (error) { state.error = errorText(error); }
  finally { refreshing = false; state.loading = false; renderAll(); schedulePoll(); }
}
function reviewNotice(doc) {
  if (doc.review_reason === 'ocr_unavailable') return 'OCR chưa hoàn tất. Kiểm tra bộ nhận diện chữ trên máy hoặc chia PDF thành phần nhỏ hơn rồi thử lại.';
  if (doc.unread_pages?.length) return `Cần OCR để đọc đủ nội dung tại trang ${doc.unread_pages.slice(0,12).join(', ')}${doc.unread_pages.length > 12 ? '…' : ''}. Tài liệu chưa sẵn sàng để hỏi đáp; bạn vẫn có thể xem PDF gốc.`;
  return 'Tài liệu chưa sẵn sàng để hỏi đáp. PDF scan cần OCR/kiểm tra thêm; tài liệu đã đọc cần có chỉ mục hoàn chỉnh.';
}
function ocrControl(doc) {
  return doc.ocr_available ? `<p class="muted">Nhận diện chữ trên máy này, tối đa 50 trang scan và 2 phút mỗi lượt. Có thể mất lâu hơn đọc PDF text.</p><button class="button primary" data-ocr="${esc(doc.doc_id)}">Đọc trang scan bằng OCR</button><p id="ocr-status" role="status" aria-live="polite"></p>` : '';
}
async function startOCR(button) {
  if (button.disabled) return;
  button.disabled = true;
  $('#ocr-status').textContent = 'Đang bắt đầu nhận diện chữ...';
  try {
    await post(`/api/documents/${encodeURIComponent(button.dataset.ocr)}/ocr`, {});
    closeDialog($('#detail-dialog')); route('documents'); pollingStarted = 0;
    await refreshDocuments(); toast('Đã bắt đầu OCR cục bộ. Bạn có thể tiếp tục dùng thư viện trong lúc chờ.');
  } catch (error) { $('#ocr-status').textContent = errorText(error); }
  finally { if (button.isConnected) button.disabled = false; }
}
async function detail(id) {
  showDialog('detail-dialog'); $('#detail-content').textContent = 'Đang tải thông tin...';
  try {
    const {document:doc} = await request(`/api/documents/${encodeURIComponent(id)}`);
    const metadata = Object.entries(doc.metadata).map(([key,value]) => `<dt>${esc({document_type:'Loại tài liệu',academic_year:'Năm học',program:'Chương trình',university:'Đơn vị',version:'Phiên bản',semester:'Học kỳ'}[key] || key)}</dt><dd>${esc(value)}</dd>`).join('');
    $('#detail-content').innerHTML = `<div class="document-card">${pdfIcon()}<div class="document-info"><h3>${esc(doc.name)}</h3>${badge(doc)}</div></div><dl class="detail-grid"><dt>Số trang</dt><dd>${doc.page_count}</dd><dt>Dung lượng</dt><dd>${bytes(doc.size_bytes) || 'Chưa có thông tin'}</dd><dt>Ngày tải lên</dt><dd>${date(doc.uploaded_at)}</dd>${metadata}</dl>${!doc.ready ? `<div class="notice">${esc(reviewNotice(doc))}</div>` : ''}${ocrControl(doc)}<button class="button secondary" data-preview="${doc.doc_id}" ${doc.file_available ? '' : 'disabled'}>${icon('eye')}Xem PDF gốc</button>`;
  } catch (error) { $('#detail-content').textContent = errorText(error); }
}
export async function preview(id, page = 1, citation = null) {
  showDialog('preview-dialog'); $('#preview-body').textContent = 'Đang mở tài liệu nguồn...'; $('#preview-external').removeAttribute('href');
  try {
    const {document:doc} = await request(`/api/documents/${encodeURIComponent(id)}`);
    if (!doc.file_available) { const error = new Error(); error.code = 'source_unavailable'; throw error; }
    let physicalPage = Math.max(1, Math.min(doc.page_count, Number(page) || 1));
    let located = null;
    if (citation?.quote) {
      const interval = citation.page_range?.length === 2 && citation.page_range[0] > 0 ? citation.page_range : [physicalPage,physicalPage];
      located = await post(`/api/documents/${encodeURIComponent(id)}/locate`, {quote:citation.quote,page_range:interval});
      physicalPage = located.page;
    }
    const url = `/api/documents/${encodeURIComponent(id)}/file#page=${physicalPage}`;
    $('#preview-title').textContent = doc.name; $('#preview-page').textContent = `Trang ${physicalPage} / ${doc.page_count} · ${located ? located.matched ? 'Đã tìm thấy đoạn trích trên trang này' : 'Mở trang đầu của nguồn; chưa xác định được vị trí đoạn trích' : 'Số trang vật lý trong PDF'}`;
    $('#preview-external').href = url;
    const frame = document.createElement('iframe'); frame.title = `PDF ${doc.name}, trang ${physicalPage}`; frame.src = url;
    $('#preview-body').replaceChildren(frame);
  } catch (error) { $('#preview-body').textContent = errorText(error); }
}
function renderUploadSelection() {
  $('#upload-selection').innerHTML = files.map((entry, index) => `<div class="document-card upload-file-card">${pdfIcon()}<div class="document-info"><h3>${esc(entry.file.name)}</h3><p>${bytes(entry.file.size)} · <span data-upload-status="${index}">${esc(entry.status || 'Sẵn sàng tải lên')}</span></p><progress data-upload-progress="${index}" value="${entry.progress || 0}" max="100" aria-label="Tiến độ tải lên ${esc(entry.file.name)}"></progress></div>${uploading ? '' : `<button class="icon-button" data-upload-remove="${index}" aria-label="Bỏ ${esc(entry.file.name)} khỏi lượt tải">${icon('close')}</button>`}</div>`).join('');
  $('#upload-submit').disabled = !files.length || !state.uploadAvailable || uploading;
  $('#upload-submit').innerHTML = `${icon('upload')}${uploading ? 'Đang gửi PDF...' : files.length ? `Tải lên ${files.length} PDF song song` : 'Tải lên và xử lý'}`;
}
function updateUploadProgress(index) {
  const entry = files[index];
  if (!entry) return;
  const progress = $(`[data-upload-progress="${index}"]`, $('#upload-selection'));
  const status = $(`[data-upload-status="${index}"]`, $('#upload-selection'));
  if (progress) progress.value = entry.progress || 0;
  if (status) status.textContent = entry.status || '';
  const total = files.reduce((sum, item) => sum + item.file.size, 0);
  const transferred = files.reduce((sum, item) => sum + item.file.size * (item.progress || 0) / 100, 0);
  const settled = files.filter(item => ['accepted', 'failed'].includes(item.state)).length;
  $('#upload-status').textContent = `Đang gửi ${settled}/${files.length} PDF · ${total ? Math.round(transferred / total * 100) : 0}%`;
}
function chooseFiles(values) {
  if (uploading) return;
  const selected = Array.from(values || []);
  files = [];
  $('#upload-status').textContent = ''; $('#upload-status').classList.remove('error-text');
  if (selected.length > MAX_UPLOAD_FILES) {
    $('#upload-status').textContent = `Mỗi lượt chỉ tải được tối đa ${MAX_UPLOAD_FILES} PDF. Hãy chia file thành các lượt nhỏ hơn.`;
    $('#upload-status').classList.add('error-text'); renderUploadSelection(); return;
  }
  const invalid = selected.filter(item => !item.name.toLowerCase().endsWith('.pdf') || item.size > state.limits.max_mb*1048576 || !item.size);
  files = selected.filter(item => !invalid.includes(item)).map(file => ({file, progress:0, state:'ready', status:'Sẵn sàng tải lên'}));
  if (invalid.length) {
    $('#upload-status').textContent = `${invalid.length} file bị bỏ qua. Chỉ chọn PDF không rỗng, tối đa ${state.limits.max_mb} MB mỗi file.`;
    $('#upload-status').classList.add('error-text');
  }
  renderUploadSelection();
}
async function submitUpload() {
  const batch = files.filter(entry => entry.state === 'ready' || entry.state === 'failed');
  if (!batch.length || uploading || !state.uploadAvailable) return;
  uploading = true; $('#file-input').disabled = true;
  $('#upload-status').classList.remove('error-text');
  batch.forEach(entry => { entry.state = 'sending'; entry.progress = 0; entry.status = 'Đang tải lên...'; });
  renderUploadSelection();
  await Promise.all(batch.map(async entry => {
    const index = files.indexOf(entry);
    try {
      const result = await upload(entry.file, progress => { entry.progress = progress; entry.status = progress < 100 ? `Đang tải lên ${progress}%` : 'Đã truyền file, đang kiểm tra'; updateUploadProgress(index); });
      entry.state = 'accepted'; entry.progress = 100; entry.status = result.duplicate ? 'Đã có trong thư viện' : 'Đã nhận, đang xử lý nền';
    } catch (error) {
      entry.state = 'failed'; entry.status = errorText(error);
    }
    updateUploadProgress(index);
  }));
  const accepted = batch.filter(entry => entry.state === 'accepted').length;
  const failed = batch.length - accepted;
  uploading = false;
  $('#file-input').disabled = false;
  if (accepted) {
    files = files.filter(entry => entry.state !== 'accepted');
    route('documents'); pollingStarted = 0; await refreshDocuments();
  }
  if (failed) {
    $('#upload-status').textContent = accepted ? `Đã nhận ${accepted} PDF; ${failed} file lỗi vẫn được giữ để thử lại.` : `${failed} file chưa tải được. Kiểm tra lỗi bên cạnh rồi thử lại.`;
    if (!accepted) $('#upload-status').classList.add('error-text');
    renderUploadSelection();
    if (accepted) toast(`Đã nhận ${accepted} PDF; ${failed} file cần thử lại.`);
  } else {
    files = []; $('#file-input').value = ''; renderUploadSelection(); closeDialog($('#upload-dialog'));
    toast(accepted === 1 ? 'Đã tải lên. PDF đang được chuẩn bị.' : `Đã nhận ${accepted} PDF. Đang xử lý nền.`);
  }
}
export function initDocuments() {
  renderAll();
  renderUploadSelection();
  events.addEventListener('selection', () => { renderScope(); renderSidebar(); renderList(); const ask = $('#ask-selected'); if (ask) { ask.disabled = !readySelected().length; ask.innerHTML = `${icon('chat')}Hỏi với ${readySelected().length} tài liệu`; } });
  events.addEventListener('search', () => { renderControls(); renderList(); renderSidebar(); });
  events.addEventListener('navigation', () => { renderControls(); renderList(); });
  document.addEventListener('visibilitychange', () => { clearTimeout(pollingTimer); if (!document.hidden) { pollingStarted = 0; refreshDocuments(); } });
  window.addEventListener('pagehide', () => clearTimeout(pollingTimer));
  document.addEventListener('change', event => {
    if (event.target.matches('[data-select]')) selectDocument(event.target.dataset.select, event.target.checked);
    if (['year-filter','program-filter','status-filter'].includes(event.target.id)) { state[{'year-filter':'year','program-filter':'program','status-filter':'status'}[event.target.id]] = event.target.value; renderList(); }
  });
  document.addEventListener('input', event => { if (event.target.id === 'document-search') { state.search = event.target.value; renderList(); } });
  document.addEventListener('click', async event => {
    const ocr = event.target.closest('[data-ocr]'); if (ocr) { await startOCR(ocr); return; }
    const category = event.target.closest('[data-category]'); if (category) { state.category = category.dataset.category; state.search = ''; state.year = ''; state.program = ''; state.status = 'all'; renderControls(); renderList(); renderSidebar(); route('documents'); }
    const details = event.target.closest('[data-detail]'); if (details) detail(details.dataset.detail);
    const source = event.target.closest('[data-preview]'); if (source) preview(source.dataset.preview);
    const deletion = event.target.closest('[data-delete]'); if (deletion && !deletion.disabled) { deleteId = deletion.dataset.delete; $('#delete-name').textContent = state.documents.find(doc => doc.doc_id === deleteId)?.name || state.jobs.find(job => job.document_id === deleteId)?.name || ''; $('#delete-status').textContent = ''; showDialog('delete-dialog'); }
    if (event.target.closest('[data-refresh]')) { pollingStarted = 0; refreshDocuments(); }
    if (event.target.closest('#ask-selected')) route('assistant');
    if (event.target.closest('#clear-filters')) { state.category = 'all'; state.search = ''; state.year = ''; state.program = ''; state.status = 'all'; renderControls(); renderList(); renderSidebar(); }
    const removeUpload = event.target.closest('[data-upload-remove]');
    if (removeUpload) { files.splice(Number(removeUpload.dataset.uploadRemove), 1); renderUploadSelection(); }
    const jobAction = event.target.closest('[data-job-cancel],[data-job-retry]');
    if (jobAction) {
      jobAction.disabled = true;
      try { const retry = jobAction.hasAttribute('data-job-retry'); await post(`/api/jobs/${encodeURIComponent(retry ? jobAction.dataset.jobRetry : jobAction.dataset.jobCancel)}/${retry ? 'retry' : 'cancel'}`, {}); await refreshDocuments(); toast(retry ? 'Đã yêu cầu thử lại.' : 'Đã yêu cầu hủy. Tác vụ đang chạy sẽ dừng tại điểm kiểm tra tiếp theo.'); }
      catch (error) { jobAction.parentElement.querySelector('p').textContent = errorText(error); jobAction.disabled = false; }
    }
  });
  $('#file-input').addEventListener('change', event => { chooseFiles(event.target.files); event.target.value = ''; });
  $('#dropzone').addEventListener('dragover', event => { event.preventDefault(); $('#dropzone').classList.add('dragover'); });
  $('#dropzone').addEventListener('dragleave', () => $('#dropzone').classList.remove('dragover'));
  $('#dropzone').addEventListener('drop', event => { event.preventDefault(); $('#dropzone').classList.remove('dragover'); chooseFiles(event.dataTransfer.files); });
  $('#upload-submit').addEventListener('click', submitUpload);
  $('#scope-open').addEventListener('click', () => { renderScope(); showDialog('scope-dialog'); });
  $('#clear-scope').addEventListener('click', () => { state.selected.clear(); notify('selection'); });
  $('#delete-confirm').addEventListener('click', async () => {
    if (!deleteId || $('#delete-confirm').disabled) return;
    $('#delete-confirm').disabled = true;
    try { const result = await request(`/api/documents/${encodeURIComponent(deleteId)}`, {method:'DELETE'}); state.selected.delete(deleteId); notify('deleted'); closeDialog($('#delete-dialog')); pollingStarted = 0; await refreshDocuments(); toast(result.deleting ? 'Đã nhận yêu cầu xóa. PDF sẽ được xóa khi tác vụ dừng an toàn.' : 'Đã xóa tài liệu và dữ liệu liên quan.'); }
    catch (error) { $('#delete-status').textContent = errorText(error); }
    finally { $('#delete-confirm').disabled = false; }
  });
}
