const messages = {
  invalid_pdf:'File không phải PDF hợp lệ, bị hỏng, được mã hóa hoặc vượt giới hạn số trang.',
  upload_too_large:'Tài liệu vượt dung lượng cho phép. Hãy chọn file nhỏ hơn.',
  jobs_not_configured:'Chức năng xử lý tài liệu chưa được cấu hình trên máy chủ.',
  ingestion_busy:'Máy chủ đang xử lý các tài liệu khác. Hãy chờ một tác vụ hoàn tất rồi thử lại.',
  job_store_unavailable:'Chưa lưu được trạng thái xử lý. Vui lòng kiểm tra máy chủ và thử lại sau.',
  job_source_changed:'File của tác vụ đã thiếu hoặc thay đổi. Hãy tải lại PDF gốc.',
  retrieval_not_ready:'Hệ thống tìm kiếm chưa sẵn sàng. Vui lòng thử lại sau.',
  document_not_ready:'Tài liệu chưa sẵn sàng. Hãy chờ xử lý hoàn tất.',
  empty_scope:'Chọn ít nhất một tài liệu sẵn sàng để hỏi đáp.',
  not_found:'Tài liệu hoặc tác vụ không còn tồn tại trong phạm vi truy cập.',
  source_unavailable:'Không tìm thấy PDF gốc. Bạn có thể đọc đoạn trích hoặc tải lại tài liệu.',
  document_busy:'Tài liệu đang được xử lý. Hãy chờ tác vụ kết thúc trước khi xóa.',
  provider_timeout:'Yêu cầu mất quá nhiều thời gian. Bạn có thể thử lại.',
  provider_overloaded:'Dịch vụ Gemini đang quá tải (503).',
  provider_rate_limited:'Gemini đang giới hạn tần suất hoặc hạn mức sử dụng (429). Kiểm tra quota API nếu lỗi tiếp diễn.',
  provider_authentication_failed:'Credential AI không hợp lệ hoặc không có quyền. Hãy kiểm tra cấu hình máy chủ.',
  provider_invalid_response:'AI trả về dữ liệu không hợp lệ. Câu trả lời chưa được công bố; bạn có thể thử lại.',
  provider_unavailable:'Không kết nối được dịch vụ AI. Bạn có thể thử lại sau.',
  query_busy:'Máy chủ đang xử lý một câu hỏi khác. Hãy chờ yêu cầu đó hoàn tất.',
  invalid_feedback:'Phiên phản hồi đã hết hạn. Hãy đặt lại câu hỏi để gửi phản hồi mới.',
  cross_origin_denied:'Yêu cầu bị từ chối. Hãy mở ứng dụng từ địa chỉ máy chủ.',
  upload_scope_unavailable:'Máy chủ chưa hỗ trợ gán quyền cho tài liệu mới trong phiên này.',
  retry_unavailable:'Tác vụ này không thể thử lại. Hãy kiểm tra tài liệu đầu vào.',
  job_terminal:'Tác vụ đã kết thúc; không thể yêu cầu hủy.',
};
export function errorText(error) {
  if (error.name === 'TimeoutError' || error.name === 'AbortError') return 'Yêu cầu mất quá nhiều thời gian. Bạn có thể thử lại. Việc dừng chờ không hủy xử lý trên máy chủ.';
  const text = messages[error.code] || 'Không thể hoàn tất yêu cầu. Kiểm tra kết nối và thử lại.';
  return error.retryAfterSeconds ? `${text} Chờ khoảng ${error.retryAfterSeconds} giây trước khi gửi lại. App không tự gửi lại câu hỏi.` : text;
}
export async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeout || 45000);
  try {
    const response = await fetch(path, {...options, signal:controller.signal, headers:{'Content-Type':'application/json', ...options.headers}});
    const value = await response.json();
    if (!response.ok || value.ok === false) {
      const error = new Error('request_failed'); error.code = value.error_code;
      const delay = Number(value.retry_after_seconds ?? response.headers.get('Retry-After'));
      error.retryAfterSeconds = Number.isFinite(delay) && delay > 0 ? Math.ceil(Math.min(delay,90000)) : 0;
      throw error;
    }
    return {...value, responseId:response.headers.get('X-Request-ID')};
  } finally { clearTimeout(timeout); }
}
export const post = (path, value) => request(path, {method:'POST', body:JSON.stringify(value)});
export function upload(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/documents/upload'); xhr.timeout = 60000;
    xhr.setRequestHeader('Content-Type', 'application/pdf'); xhr.setRequestHeader('X-Filename', encodeURIComponent(file.name));
    xhr.upload.onprogress = event => { if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100)); };
    xhr.onload = () => { try { const value = JSON.parse(xhr.responseText); if (xhr.status >= 400 || !value.ok) { const error = new Error('upload_failed'); error.code = value.error_code; reject(error); } else resolve(value); } catch { reject(new Error('invalid_response')); } };
    xhr.onerror = () => reject(new Error('connection_failed'));
    xhr.ontimeout = () => reject(new DOMException('timeout', 'TimeoutError'));
    xhr.send(file);
  });
}
