import {esc} from '../scripts/shared.js';

export const excerptNotice = 'AI tạm thời không thể tổng hợp câu trả lời. Dưới đây là trích đoạn nguyên văn được tìm thấy trong tài liệu. Bạn vẫn có thể tiếp tục tra cứu và mở PDF để đối chiếu.';
export function excerptFallback(response) {
  const fallback = response.fallback;
  if (fallback?.kind !== 'source_excerpts' || !Array.isArray(fallback.citations)) return null;
  const citations = fallback.citations.filter(citation => typeof citation.quote === 'string' && citation.quote.trim());
  return citations.length ? {...fallback,citations:citations.slice(0,3)} : null;
}
export function excerptSources(message) {
  return message.fallback ? {abstained:false,sourceOnly:true,citations:message.fallback.citations} : message.answer;
}
export function excerptBody(fallback, index, marker) {
  return `<div class="answer-note" role="status">${esc(excerptNotice)}</div><div class="answer-body">`+
    fallback.citations.map((citation,i) => `<blockquote>${esc(citation.quote)}</blockquote>${marker(i,index)}`).join('')+'</div>';
}
export function excerptCopy(message) {
  return message.fallback ? excerptNotice+'\n\n'+message.fallback.citations.map(citation => citation.quote).join('\n\n') : message.answer.answer;
}
