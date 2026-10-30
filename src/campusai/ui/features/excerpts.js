import {esc} from '../scripts/shared.js';

export const excerptNotice = 'Dịch vụ AI chưa phản hồi thành công. Chưa có câu trả lời đã kiểm chứng; bạn có thể mở nguồn đối chiếu hoặc gửi lại câu hỏi sau.';
export function excerptFallback(response) {
  const fallback = response.fallback;
  if (fallback?.kind !== 'source_excerpts' || !Array.isArray(fallback.citations)) return null;
  const citations = fallback.citations.filter(citation => typeof citation.quote === 'string' && citation.quote.trim());
  return citations.length ? {...fallback,citations:citations.slice(0,3),providerStatus:response.provider_status} : null;
}
export function excerptSources(message) {
  return message.fallback ? {abstained:false,sourceOnly:true,citations:message.fallback.citations} : message.answer;
}
export function excerptBody(fallback, index, marker) {
  const code = fallback.providerStatus?.error_code;
  const reason = {provider_busy:'Một yêu cầu AI khác đang được xử lý. Vui lòng gửi lại sau ít giây.',provider_overloaded:'Dịch vụ AI đang quá tải.',provider_rate_limited:'Đã chạm giới hạn lượt gọi AI.',provider_timeout:'Dịch vụ AI phản hồi quá thời gian chờ.',provider_authentication_failed:'Cấu hình kết nối AI chưa hợp lệ.',provider_invalid_response:'AI trả về dữ liệu chưa hợp lệ.'}[code] || '';
  return `<div class="answer-note" role="status">${esc(reason ? reason+' Chưa có câu trả lời đã kiểm chứng.' : excerptNotice)}</div><details><summary>Mở trích đoạn nguồn để đối chiếu</summary><div class="answer-body">`+
    fallback.citations.map((citation,i) => `<blockquote>${esc(citation.quote)}</blockquote>${marker(i,index)}`).join('')+'</div></details>';
}
export function excerptCopy(message) {
  return message.fallback ? excerptNotice+'\n\n'+message.fallback.citations.map(citation => citation.quote).join('\n\n') : message.answer.answer;
}
