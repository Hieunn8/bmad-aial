/**
 * errorMessages — RFC 9457 error.type → user-friendly Vietnamese message mapping
 * Architecture: §ST-2 utils/errorMessages.ts
 */

type ErrorCode = 'timeout' | 'permission-denied' | 'llm-unavailable' | string;

const ERROR_MESSAGES: Record<string, string> = {
  timeout: 'Yêu cầu mất quá nhiều thời gian. Vui lòng thử lại.',
  'permission-denied': 'Bạn không có quyền truy cập thông tin này.',
  'llm-unavailable': 'Dịch vụ AI tạm thời không khả dụng. Vui lòng thử lại sau.',
  'network-error': 'Lỗi kết nối mạng. Vui lòng kiểm tra kết nối và thử lại.',
  'internal-error': 'Đã xảy ra lỗi hệ thống. Vui lòng liên hệ bộ phận hỗ trợ.',
  'auth-failed': 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
  'not-found': 'Không tìm thấy tài nguyên yêu cầu.',
  'rate-limited': 'Bạn đã gửi quá nhiều yêu cầu. Vui lòng đợi một chút.',
  'validation-error': 'Dữ liệu không hợp lệ. Vui lòng kiểm tra lại.',
};

const DEFAULT_MESSAGE = 'Đã xảy ra lỗi không mong muốn. Vui lòng thử lại.';

/**
 * Get user-friendly error message from RFC 9457 error type or error code.
 * @param errorCode - RFC 9457 error type URL suffix or simple code
 */
export function getErrorMessage(errorCode: ErrorCode): string {
  if (!errorCode) return DEFAULT_MESSAGE;

  // Handle RFC 9457 URL format: "https://aial.internal/errors/permission-denied"
  const lastSegment = errorCode.split('/').pop() ?? errorCode;

  return ERROR_MESSAGES[lastSegment] ?? DEFAULT_MESSAGE;
}

/**
 * Get concise error label for UI components
 */
export function getErrorLabel(errorCode: ErrorCode): string {
  const labels: Record<string, string> = {
    timeout: 'Hết thời gian',
    'permission-denied': 'Không có quyền',
    'llm-unavailable': 'AI không khả dụng',
    'network-error': 'Lỗi mạng',
    'internal-error': 'Lỗi hệ thống',
    'auth-failed': 'Chưa đăng nhập',
  };

  const lastSegment = errorCode.split('/').pop() ?? errorCode;
  return labels[lastSegment] ?? 'Lỗi';
}
