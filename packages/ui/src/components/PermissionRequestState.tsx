/**
 * PermissionRequestState — Story 4.5 (UX-DR17)
 *
 * AC: what is blocked (plain Vietnamese), what user CAN access,
 * primary CTA "Yêu cầu quyền truy cập" → IT Admin queue,
 * secondary CTA "Xem dữ liệu khả dụng" → re-run with available scope.
 *
 * Also used in Story 4.2 when masked 🔒 column is clicked.
 */
export interface PermissionRequestStateProps {
  blockedResource: string;
  blockedReason: string;
  availableScope: string;
  onRequestAccess: () => void;
  onViewAvailable: () => void;
}

export function PermissionRequestState({
  blockedResource,
  blockedReason,
  availableScope,
  onRequestAccess,
  onViewAvailable,
}: PermissionRequestStateProps): React.JSX.Element {
  return (
    <div
      role="region"
      aria-label="Yêu cầu quyền truy cập"
      style={{
        padding: 'var(--space-5, 20px)',
        backgroundColor: 'var(--color-surface, white)',
        border: '1px solid var(--color-border, #e5e7eb)',
        borderRadius: 'var(--radius-xl, 12px)',
      }}
    >
      {/* What is blocked */}
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
          <span aria-hidden="true" style={{ fontSize: '1.25rem' }}>🔒</span>
          <strong style={{ color: 'var(--color-neutral-900)' }}>Quyền truy cập bị giới hạn</strong>
        </div>
        <p style={{ color: 'var(--color-neutral-700)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-1)' }}>
          <strong>Tài nguyên bị chặn:</strong> {blockedResource}
        </p>
        <p style={{ color: 'var(--color-neutral-600)', fontSize: 'var(--font-size-sm)' }}>
          <strong>Lý do:</strong> {blockedReason}
        </p>
      </div>

      {/* What user CAN access */}
      <div style={{
        backgroundColor: 'var(--color-success-50, #f0fdf4)',
        border: '1px solid var(--color-success, #16a34a)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-3)',
        marginBottom: 'var(--space-4)',
        fontSize: 'var(--font-size-sm)',
        color: 'var(--color-success, #16a34a)',
      }}>
        ✅ <strong>Bạn có thể truy cập:</strong> {availableScope}
      </div>

      {/* 2 CTAs */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={onRequestAccess}
          style={{
            padding: 'var(--space-2) var(--space-4)',
            backgroundColor: 'var(--color-primary, #2563eb)',
            color: 'white',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            fontFamily: 'var(--font-family-base)',
            fontSize: 'var(--font-size-sm)',
            fontWeight: 'var(--font-weight-medium)',
          }}
        >
          Yêu cầu quyền truy cập
        </button>
        <button
          type="button"
          onClick={onViewAvailable}
          style={{
            padding: 'var(--space-2) var(--space-4)',
            backgroundColor: 'transparent',
            color: 'var(--color-primary, #2563eb)',
            border: '1px solid var(--color-primary)',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            fontFamily: 'var(--font-family-base)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          Xem dữ liệu khả dụng
        </button>
      </div>
    </div>
  );
}
