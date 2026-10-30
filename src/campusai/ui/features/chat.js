import {$, esc, icon, pdfIcon, state, events, notify, toast} from '../scripts/shared.js';
import {post, postQuery, errorText} from '../scripts/api.js';
import {readySelected, preview} from './documents.js';
import {excerptFallback, excerptSources, excerptBody, excerptCopy} from './excerpts.js';

let messages = [], activeSources = null, epoch = 0;
const formatInline = value => esc(value).replace(/\*\*([^*\n]+)\*\*/g,'<strong>$1</strong>').replace(/`([^`\n]+)`/g,'<code>$1</code>');
// A deliberately small renderer: text, lists, headings, tables and emphasis.
// Escape first; raw HTML, links, images and scripts are never interpreted.
export function safeMarkdown(value) {
  const lines = String(value || '').split('\n');
  let output = '', list = '', table = [];
  const flushList = () => { if (list) { output += `</${list}>`; list = ''; } };
  const flushTable = () => {
    if (!table.length) return;
    const rows = table.filter(line => !/^\s*\|?[\s:|\-]+\|?\s*$/.test(line));
    output += '<div class="table-scroll"><table><tbody>' + rows.map((line,i) => '<tr>'+line.replace(/^\s*\||\|\s*$/g,'').split('|').map(cell => `<${i ? 'td' : 'th'}>${formatInline(cell.trim())}</${i ? 'td' : 'th'}>`).join('')+'</tr>').join('')+'</tbody></table></div>'; table = [];
  };
  for (const line of lines) {
    if (/^\s*\|.+\|\s*$/.test(line)) { flushList(); table.push(line); continue; }
    flushTable();
    const item = line.match(/^\s*(?:([-*])|\d+\.)\s+(.+)/);
    if (item) { const next = item[1] ? 'ul' : 'ol'; if (next !== list) { flushList(); output += `<${next}>`; list = next; } output += `<li>${formatInline(item[2])}</li>`; continue; }
    flushList();
    const heading = line.match(/^#{1,6}\s+(.+)/);
    if (heading) output += `<h3>${formatInline(heading[1])}</h3>`;
    else if (line.trim()) output += `<p>${formatInline(line)}</p>`;
  }
  flushList(); flushTable(); return output;
}
function marker(index, messageIndex) { return `<button class="citation-marker" data-citation="${index}" data-message="${messageIndex}" aria-label="Xem nguồn trích dẫn ${index+1}">${index+1}</button>`; }
function note(answer) {
  if (answer.documentInfo || answer.conversationKind) return '';
  if (!answer.abstained) return '';
  if (answer.abstention_reason === 'provider_abstention') return 'Dịch vụ AI chưa sẵn sàng hoặc đang quá tải. Vui lòng thử lại sau.';
  if (['ambiguous_question','ambiguous_scope','conflicting_evidence'].includes(answer.abstention_reason)) return 'Cần làm rõ phạm vi hoặc phiên bản tài liệu.';
  return 'Chưa đủ bằng chứng trong tài liệu đã chọn.';
}
function renderMessage(message, index) {
  if (message.role === 'user') return `<article class="message user-message"><span class="message-avatar" aria-hidden="true">${icon('user')}</span><div class="message-bubble">${esc(message.text)}</div></article>`;
  if (message.error) return `<article class="message assistant-message"><span class="message-avatar" aria-hidden="true">${icon('cap')}</span><div class="message-bubble"><p>${esc(message.error)}</p><button class="text-button" data-retry="${index}" ${state.busy ? 'disabled' : ''}>${icon('refresh')}Thử lại câu hỏi này</button></div></article>`;
  const answer = message.answer, citations = answer.abstained ? [] : answer.citations || [];
  const coverageNote = message.coverage?.complete === false ? '<div class="answer-note">Câu trả lời dựa trên phần tài liệu đã đọc; một số trang ảnh chưa xử lý xong.</div>' : '';
  const claims = answer.abstained ? [] : answer.claims || [];
  const claimSources = claims.map(claim => {
    const indexes = (claim.citation_ids || []).map(id => citations.findIndex(citation => citation.chunk_id === id)).filter(i => i >= 0);
    return indexes.length ? `<p>${esc(claim.text)} ${indexes.map(i => marker(i,index)).join('')}</p>` : '';
  }).join('');
  const sourceLinks = citations.map((citation,i) => marker(i,index)).join('');
  if (message.fallback) return `<article class="message assistant-message"><span class="message-avatar" aria-hidden="true">${icon('cap')}</span><div class="message-bubble">${excerptBody(message.fallback,index,marker)}<button class="text-button" data-copy="${index}">${icon('copy')}Sao chép trích đoạn</button><span class="message-time">${esc(message.time)}</span></div></article>`;
  return `<article class="message assistant-message"><span class="message-avatar" aria-hidden="true">${icon('cap')}</span><div class="message-bubble">${coverageNote}${answer.abstained ? `<div class="answer-note">${esc(note(answer))}</div>` : ''}<div class="answer-body">${safeMarkdown(answer.answer)}</div>${sourceLinks ? `<div class="claim-sources">Nguồn ${sourceLinks}</div>` : ''}${claimSources ? `<details class="claim-sources"><summary>Kiểm chứng các ý chính</summary>${claimSources}</details>` : ''}<div class="message-actions"><button class="text-button ${message.feedback === 'helpful' ? 'selected' : ''}" data-feedback="helpful" data-message="${index}" aria-pressed="${message.feedback === 'helpful'}" ${message.saving ? 'disabled' : ''}>${icon('thumb-up')}Hữu ích</button><button class="text-button ${message.feedback === 'incorrect' ? 'selected' : ''}" data-feedback="incorrect" data-message="${index}" aria-pressed="${message.feedback === 'incorrect'}" ${message.saving ? 'disabled' : ''}>${icon('thumb-down')}Chưa chính xác</button><button class="text-button" data-copy="${index}">${icon('copy')}Sao chép</button><span class="message-time">${esc(message.time)}</span></div><p class="inline-status" data-feedback-status="${index}" role="status">${esc(message.feedbackError || '')}</p></div></article>`;
}
function renderConversation() {
  $('#conversation').innerHTML = messages.map(renderMessage).join('') + (state.busy ? '<div class="loading-line"><span class="spinner" aria-hidden="true"></span>Đang tìm kiếm và kiểm tra bằng chứng...</div>' : '');
  $('#welcome').hidden = messages.length > 0;
}
function renderSources(answer, highlighted = -1) {
  if (answer?.conversationKind) answer = null;
  activeSources = answer;
  const infoRows = answer?.documentInfo?.documents || [];
  const infoHtml = infoRows.map(row => `<article class="document-info-card"><h3>${esc(row.name)}</h3><p>${esc(row.page_count)} trang PDF</p><button class="text-button" data-info-preview="${esc(row.doc_id)}">${icon('eye')}Mở PDF</button></article>`).join('');
  if (answer?.documentInfo && !answer.citations?.length) {
    const rows = answer.documentInfo.documents || [];
    $('#source-count').textContent = rows.length;
    $('#source-content').innerHTML = '<p class="source-caption">Thông tin đọc từ PDF đã tải lên</p>' +
      rows.map(row => `<article class="document-info-card"><h3>${esc(row.name)}</h3><p>${esc(row.page_count)} trang PDF</p><button class="text-button" data-info-preview="${esc(row.doc_id)}">${icon('eye')}Mở PDF</button></article>`).join('');
    return;
  }
  const citations = answer && !answer.abstained ? answer.citations || [] : [];
  $('#source-count').textContent = citations.length;
  if (!citations.length) {
    $('#source-content').innerHTML = `<div class="source-empty"><div class="empty-icon">${icon('source')}</div><h3>${answer?.abstained ? 'Chưa có nguồn đủ căn cứ' : 'Mỗi câu trả lời đều có điểm tựa'}</h3><p>${answer?.abstained ? 'CampusAI không hiển thị trích dẫn chưa được kiểm chứng cho câu trả lời này.' : 'Nguồn tham khảo sẽ xuất hiện tại đây khi câu hỏi của bạn có bằng chứng trong tài liệu.'}</p><div class="source-how"><strong>Kiểm chứng thông tin dễ dàng</strong><ol><li>Đặt câu hỏi với tài liệu đã chọn.</li><li>Đọc đoạn trích đi kèm câu trả lời.</li><li>Mở PDF để đối chiếu đúng trang.</li></ol></div></div>`;
    return;
  }
  $('#source-content').innerHTML = `<p class="source-caption">${answer.sourceOnly ? 'Trích đoạn được tìm thấy trong tài liệu' : 'Trích dẫn từ câu trả lời đang xem'} · Trang vật lý trong PDF</p>` + citations.map((citation,i) => {
    const doc = state.documents.find(item => item.doc_id === citation.doc_id);
    const range = citation.page_range;
    const pageLabel = range?.length === 2 && range[0] > 0 && range[0] !== range[1] ? `${range[0]}–${range[1]}` : citation.page;
    return `<article class="source-card ${highlighted === i ? 'active' : ''}" id="citation-${i}" tabindex="-1"><div class="source-card-header">${pdfIcon()}<div><h3>${i+1}. ${esc(doc?.name || citation.source_name || 'Tài liệu nguồn')}</h3><p class="source-meta">${esc(citation.section_path || doc?.metadata.program || doc?.metadata.university || 'Nguồn được trích dẫn')}${doc?.metadata.academic_year ? ' · '+esc(doc.metadata.academic_year) : ''}</p><span class="page-badge">Trang ${esc(pageLabel)}</span></div></div><blockquote>${esc(citation.quote || 'Nguồn này không có đoạn trích hiển thị.')}</blockquote><button class="text-button" data-source-preview="${esc(citation.doc_id)}" data-source-index="${i}" data-page="${Number(citation.page) || 1}">${icon('eye')}Xem trang gốc${icon('arrow-right')}</button></article>`;
  }).join('');
  if (highlighted >= 0) requestAnimationFrame(() => { const card = $(`#citation-${highlighted}`); card?.scrollIntoView({block:'nearest'}); card?.focus({preventScroll:true}); });
}
function suggestions() {
  const docs = readySelected();
  let prompts = ['Tài liệu này đề cập đến những nội dung nào?', 'Những điều kiện nào được nêu trong tài liệu?', 'Quy trình thực hiện được quy định như thế nào?', 'Tài liệu có quy định những mốc thời gian nào?'];
  if (docs.some(doc => ['curriculum','course_catalog','syllabus'].includes(doc.metadata.document_type))) prompts = ['Điều kiện tốt nghiệp được quy định như thế nào?', 'Chương trình gồm những nhóm học phần nào?', 'Các học phần có yêu cầu tiên quyết nào?', 'Tổng số tín chỉ trong chương trình là bao nhiêu?'];
  if (docs.length > 1) prompts[3] = 'Các tài liệu này có những quy định khác nhau nào?';
  $('#suggestions').innerHTML = prompts.map(prompt => `<button class="suggestion" data-prompt="${esc(prompt)}" ${docs.length ? '' : 'disabled'}>${esc(prompt)}${icon('arrow-right')}</button>`).join('');
  $('#welcome-upload').hidden = state.documents.length > 0;
}
let providerWaitUntil = 0, waitTimer;
function updateComposer() {
  const waiting = Date.now() < providerWaitUntil;
  $('#send').disabled = state.busy || !state.aiConfigured || !$('#question').value.trim() || !readySelected().length;
  const notice = $('#runtime-notice');
  notice.hidden = state.loading || state.aiConfigured;
  notice.textContent = state.error || 'Chưa cấu hình AI cho phiên này. Mở app bằng start-campusai.cmd để dùng credential local đã có.';
  $('#new-chat').disabled = state.busy;
  $('#reply-language').disabled = state.busy;
  $('#question').readOnly = state.busy;
  $('#query-form').setAttribute('aria-busy',String(state.busy));
  if (waiting) $('#query-status').textContent = `Dịch vụ AI tạm nghỉ ${Math.ceil((providerWaitUntil-Date.now())/1000)} giây. Bạn vẫn có thể tra cứu tài liệu hoặc xem lại câu trả lời đã có.`;
}
function updateWait() {
  clearTimeout(waitTimer);
  updateComposer();
  document.querySelectorAll('[data-retry]').forEach(button => {
    const message = messages[Number(button.dataset.retry)];
    const seconds = Math.max(0,Math.ceil(((message?.retryUntil || 0)-Date.now())/1000));
    button.disabled = state.busy || seconds > 0 || Date.now() < providerWaitUntil;
    button.textContent = seconds > 0 ? `Thử lại sau ${seconds} giây` : 'Thử lại câu hỏi này';
  });
  if (Date.now() < providerWaitUntil || messages.some(message => Date.now() < (message.retryUntil || 0))) waitTimer = setTimeout(updateWait,1000);
  else if ($('#query-status').textContent.startsWith('Dịch vụ AI tạm nghỉ')) $('#query-status').textContent = 'Bạn có thể gửi lại câu hỏi. App chưa tự gửi yêu cầu mới.';
}
async function send(question, docIds = readySelected().map(doc => doc.doc_id), language = state.replyLanguage) {
  // The server checks answers and source evidence before its durable provider
  // circuit. Keep these paths available while explicit failed-turn retries wait.
  if (state.busy || !state.aiConfigured || !question.trim() || !docIds.length) return;
  const generation = epoch;
  const scopeKey = language + ':' + [...docIds].sort().join(',');
  const history = messages.filter(message => message.scopeKey === scopeKey && !message.error && !message.failed && !message.fallback)
    .map(message => ({role:message.role,content:String(message.role === 'user' ? message.text : message.answer.answer).slice(0,2000)})).slice(-6);
  state.busy = true; updateComposer();
  const userMessage = {role:'user',text:question,scopeKey};
  messages.push(userMessage);
  renderSources(null); renderConversation();
  $('#query-status').textContent = '';
  $('#question').value = ''; $('#question').style.height = '';
  $('#chat-scroll').scrollTop = $('#chat-scroll').scrollHeight;
  try {
    const payload = {question,doc_ids:docIds,language,history};
    const response = await (state.queryStreaming ? postQuery(payload, phase => {
      if (generation !== epoch) return;
      $('#query-status').textContent = phase === 'generating'
        ? 'AI đang tạo câu trả lời. Nội dung sẽ hiển thị sau khi kiểm chứng nguồn.'
        : 'Đang kiểm chứng câu trả lời và trích dẫn...';
    }, state.queryTimeoutMs) : post('/api/query', payload, state.queryTimeoutMs));
    if (generation !== epoch) return;
    if (!response.answer || typeof response.answer.answer !== 'string') throw new Error('invalid_response');
    const answer = {...response.answer, documentInfo:response.document_info, conversationKind:response.conversation_kind};
    $('#query-status').textContent = '';
    if (answer.abstained) { answer.citations = []; answer.claims = []; }
    const fallback = excerptFallback(response);
    if (fallback || response.partial) userMessage.failed = true;
    const message = {role:'assistant',answer,fallback,coverage:response.source_coverage,failed:!!response.partial,scopeKey,responseId:response.responseId,time:new Date().toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Bangkok'})};
    messages.push(message);
    renderSources(excerptSources(message));
  } catch (error) {
    userMessage.failed = true;
    if (generation === epoch) $('#query-status').textContent = '';
    if (['provider_overloaded','provider_rate_limited','provider_busy'].includes(error.code) && error.retryAfterSeconds)
      providerWaitUntil = Math.max(providerWaitUntil,Date.now()+error.retryAfterSeconds*1000);
    if (generation === epoch) messages.push({role:'assistant',error:errorText(error),question,docIds,language,
      retryUntil:Date.now()+(error.retryAfterSeconds || 0)*1000});
  } finally {
    state.busy = false; updateComposer(); renderConversation();
    updateWait();
    $('#chat-scroll').scrollTop = $('#chat-scroll').scrollHeight;
    if (state.tab === 'assistant' && !document.querySelector('dialog[open]')) $('#question').focus();
  }
}
function resetChat() { epoch++; messages = []; renderConversation(); renderSources(null); $('#query-status').textContent = ''; updateComposer(); }
export function initChat() {
  suggestions(); renderSources(null); updateComposer();
  events.addEventListener('selection', () => { suggestions(); updateComposer(); });
  events.addEventListener('documents', () => { suggestions(); updateComposer(); });
  events.addEventListener('deleted', resetChat);
  $('#new-chat').addEventListener('click', resetChat);
  $('#reply-language').addEventListener('change', () => { state.replyLanguage = $('#reply-language').value; updateComposer(); });
  $('#question').addEventListener('input', () => { $('#question').style.height = 'auto'; $('#question').style.height = `${Math.min(150,$('#question').scrollHeight)}px`; updateComposer(); });
  $('#question').addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); if (!$('#send').disabled) $('#query-form').requestSubmit(); } });
  $('#query-form').addEventListener('submit', event => { event.preventDefault(); send($('#question').value); });
  document.addEventListener('click', async event => {
    const info = event.target.closest('[data-info-preview]'); if (info) preview(info.dataset.infoPreview,1);
    const prompt = event.target.closest('[data-prompt]'); if (prompt && !prompt.disabled) { $('#question').value = prompt.dataset.prompt; updateComposer(); $('#question').focus(); }
    const citation = event.target.closest('[data-citation]');
    if (citation) { const message = messages[Number(citation.dataset.message)]; if (message?.answer) { notify('open-sources'); renderSources(excerptSources(message), Number(citation.dataset.citation)); } }
    const source = event.target.closest('[data-source-preview]'); if (source) preview(source.dataset.sourcePreview, Number(source.dataset.page), activeSources?.citations?.[Number(source.dataset.sourceIndex)]);
    const retry = event.target.closest('[data-retry]'); if (retry) { const message = messages[Number(retry.dataset.retry)]; const validIds = new Set(state.documents.filter(doc => doc.ready).map(doc => doc.doc_id)); if (message.docIds.every(id => validIds.has(id))) send(message.question,message.docIds,message.language); else $('#query-status').textContent = 'Nguồn của câu hỏi đã thay đổi. Hãy chọn lại tài liệu.'; }
    const copy = event.target.closest('[data-copy]'); if (copy) { try { await navigator.clipboard.writeText(excerptCopy(messages[Number(copy.dataset.copy)])); toast('Đã sao chép nội dung.'); } catch { toast('Trình duyệt chưa cho phép sao chép. Bạn có thể chọn và sao chép nội dung.'); } }
    const feedback = event.target.closest('[data-feedback]');
    if (feedback) {
      const index = Number(feedback.dataset.message), message = messages[index];
      if (message.saving || message.feedback === feedback.dataset.feedback) return;
      message.saving = true; message.feedbackError = ''; feedback.disabled = true;
      try { await post('/api/feedback', {response_id:message.responseId,kind:feedback.dataset.feedback}); message.feedback = feedback.dataset.feedback; toast('Đã ghi nhận phản hồi của bạn.'); }
      catch (error) { message.feedbackError = errorText(error); }
      finally { message.saving = false; renderConversation(); $(`[data-feedback="${feedback.dataset.feedback}"][data-message="${index}"]`)?.focus(); }
    }
  });
}
