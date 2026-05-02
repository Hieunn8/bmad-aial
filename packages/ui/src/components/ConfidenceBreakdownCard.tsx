/**
 * ConfidenceBreakdownCard — Story 4.5 (UX-DR12)
 *
 * 5 named states: low-confidence | partial-data | stale-data | permission-limited | cross-source-conflict
 * Each state: plain-Vietnamese explanation + exactly 3 exit actions.
 * Status indicated by BOTH color AND text label (not color-only).
 * Epic 7 consumes this from packages/ui passing { type: "forecast-uncertainty" }.
 */
import type { ReactNode } from 'react';

export type ConfidenceStateType =
  | 'low-confidence'
  | 'partial-data'
  | 'stale-data'
  | 'permission-limited'
  | 'cross-source-conflict'
  | 'forecast-uncertainty'; // Epic 7 variant

export interface ConfidenceAction {
  label: string;
  onClick: () => void;
}

export interface ConfidenceBreakdownCardProps {
  type: ConfidenceStateType;
  onActions?: ConfidenceAction[];
  detail?: string;
}

const STATE_CONFIG: Record<string, { label: string; color: string; bg: string; explanation: string; defaultActions: string[] }> = {
  'low-confidence': {
    label: 'Độ tin cậy thấp',
    color: 'var(--color-warning, #d97706)',
    bg: 'var(--color-warning-50, #fffbeb)',
    explanation: 'Kết quả này có thể không chính xác do dữ liệu không đầy đủ hoặc mâu thuẫn.',
    defaultActions: ['Xem dữ liệu gốc', 'Thử câu hỏi khác', 'Báo cáo sự cố'],
  },
  'partial-data': {
    label: 'Dữ liệu một phần',
    color: 'var(--color-warning, #d97706)',
    bg: 'var(--color-warning-50, #fffbeb)',
    explanation: 'Một số nguồn dữ liệu không khả dụng. Kết quả chỉ phản ánh dữ liệu hiện có.',
    defaultActions: ['Xem nguồn khả dụng', 'Yêu cầu đầy đủ dữ liệu', 'Xuất kết quả hiện tại'],
  },
  'stale-data': {
    label: 'Dữ liệu cũ',
    color: 'var(--color-warning, #d97706)',
    bg: 'var(--color-warning-50, #fffbeb)',
    explanation: 'Dữ liệu này đã hơn 24 giờ và có thể không phản ánh tình trạng hiện tại.',
    defaultActions: ['Làm mới dữ liệu', 'Xem lịch sử cập nhật', 'Tiếp tục với dữ liệu hiện tại'],
  },
  'permission-limited': {
    label: 'Quyền truy cập bị giới hạn',
    color: 'var(--color-error, #dc2626)',
    bg: 'var(--color-error-50, #fef2f2)',
    explanation: 'Một số dữ liệu bị ẩn do quyền truy cập của bạn. Kết quả không đầy đủ.',
    defaultActions: ['Yêu cầu quyền truy cập', 'Xem dữ liệu khả dụng', 'Liên hệ IT Admin'],
  },
  'cross-source-conflict': {
    label: 'Mâu thuẫn nguồn dữ liệu',
    color: 'var(--color-error, #dc2626)',
    bg: 'var(--color-error-50, #fef2f2)',
    explanation: 'Dữ liệu từ Oracle và tài liệu mâu thuẫn nhau. Cần xác minh thủ công.',
    defaultActions: ['Xem từng nguồn riêng', 'Báo cáo mâu thuẫn', 'Thử lại sau'],
  },
  'forecast-uncertainty': {
    label: 'Độ không chắc chắn dự báo',
    color: 'var(--color-warning, #d97706)',
    bg: 'var(--color-warning-50, #fffbeb)',
    explanation: 'Dự báo này có biên độ sai số cao. Sử dụng như tham khảo, không phải quyết định cuối cùng.',
    defaultActions: ['Xem khoảng tin cậy', 'Điều chỉnh tham số', 'Xuất với lưu ý'],
  },
};

export function ConfidenceBreakdownCard({
  type,
  onActions,
  detail,
}: ConfidenceBreakdownCardProps): React.JSX.Element {
  const cfg = STATE_CONFIG[type] ?? STATE_CONFIG['low-confidence'];
  const actions = onActions ?? cfg.defaultActions.map(label => ({ label, onClick: () => {} }));

  return (
    <div
      role="alert"
      aria-label={`Trạng thái độ tin cậy: ${cfg.label}`}
      style={{
        backgroundColor: cfg.bg,
        border: `1px solid ${cfg.color}`,
        borderRadius: 'var(--radius-lg, 8px)',
        padding: 'var(--space-4, 16px)',
      }}
    >
      {/* State indicator — color AND text label (not color-only) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
        <span style={{ width: '0.75rem', height: '0.75rem', borderRadius: '50%', backgroundColor: cfg.color, flexShrink: 0 }} aria-hidden="true" />
        <strong style={{ color: cfg.color, fontSize: 'var(--font-size-sm)' }}>{cfg.label}</strong>
      </div>

      <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-700)', marginBottom: 'var(--space-3)' }}>
        {detail ?? cfg.explanation}
      </p>

      {/* Exactly 3 exit actions */}
      <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
        {actions.slice(0, 3).map((action, i) => (
          <button
            key={i}
            type="button"
            onClick={action.onClick}
            style={{
              padding: 'var(--space-1) var(--space-3)',
              border: `1px solid ${cfg.color}`,
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'transparent',
              color: cfg.color,
              cursor: 'pointer',
              fontSize: 'var(--font-size-xs)',
              fontFamily: 'var(--font-family-base)',
            }}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}
