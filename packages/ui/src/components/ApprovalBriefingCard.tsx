/**
 * ApprovalBriefingCard — Story 4.4 (FR-A7).
 *
 * 5 required elements (all verifiable by component test):
 * 1. Requester identity + department + recent query history
 * 2. Business justification from query intent analysis
 * 3. Data scope + sensitivity_tier + estimated row count
 * 4. Anomaly risk signal (unusual time/volume pattern)
 * 5. One-click escalation button
 *
 * Renders completely in <500ms (no network calls in render).
 */
export interface ApprovalBriefingCardProps {
  requesterId: string;
  requesterDepartment: string;
  recentQueryCount: number;
  businessJustification: string;
  dataScope: string;
  sensitivityTier: number;
  estimatedRowCount: number;
  anomalySignal: string | null;
  onApprove: () => void;
  onReject: (reason: string) => void;
  onEscalate: () => void;
}

const SENSITIVITY_LABELS: Record<number, string> = {
  0: 'Công khai',
  1: 'Nội bộ',
  2: 'Bảo mật',
  3: 'Tuyệt mật',
};

export function ApprovalBriefingCard({
  requesterId,
  requesterDepartment,
  recentQueryCount,
  businessJustification,
  dataScope,
  sensitivityTier,
  estimatedRowCount,
  anomalySignal,
  onApprove,
  onReject,
  onEscalate,
}: ApprovalBriefingCardProps): React.JSX.Element {
  return (
    <article
      aria-label="Thẻ duyệt truy vấn"
      style={{
        padding: 'var(--space-5)',
        backgroundColor: 'var(--color-surface, white)',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-4)',
      }}
    >
      {/* Element 1: Requester identity */}
      <section aria-label="Người yêu cầu">
        <h3 style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', textTransform: 'uppercase', marginBottom: '4px' }}>Người yêu cầu</h3>
        <p style={{ fontWeight: 600 }}>{requesterId} — {requesterDepartment}</p>
        <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-600)' }}>{recentQueryCount} truy vấn gần đây</p>
      </section>

      {/* Element 2: Business justification */}
      <section aria-label="Lý do kinh doanh">
        <h3 style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', textTransform: 'uppercase', marginBottom: '4px' }}>Lý do kinh doanh</h3>
        <p style={{ fontSize: 'var(--font-size-sm)' }}>{businessJustification}</p>
      </section>

      {/* Element 3: Data scope + sensitivity */}
      <section aria-label="Phạm vi dữ liệu">
        <h3 style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', textTransform: 'uppercase', marginBottom: '4px' }}>Phạm vi dữ liệu</h3>
        <p style={{ fontSize: 'var(--font-size-sm)' }}>{dataScope}</p>
        <p style={{ fontSize: 'var(--font-size-sm)', color: sensitivityTier >= 3 ? 'var(--color-error)' : 'var(--color-warning)' }}>
          Mức độ nhạy cảm: <strong>{SENSITIVITY_LABELS[sensitivityTier] ?? sensitivityTier}</strong> • {estimatedRowCount.toLocaleString()} dòng ước tính
        </p>
      </section>

      {/* Element 4: Anomaly risk signal */}
      {anomalySignal && (
        <section aria-label="Tín hiệu bất thường" style={{ backgroundColor: 'var(--color-warning-50)', borderRadius: 'var(--radius-md)', padding: 'var(--space-3)' }}>
          <h3 style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-warning)', textTransform: 'uppercase', marginBottom: '4px' }}>⚠️ Tín hiệu bất thường</h3>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>{anomalySignal}</p>
        </section>
      )}

      {/* Element 5: Action buttons including one-click escalation */}
      <section aria-label="Quyết định" style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
        <button type="button" onClick={onApprove} style={{ padding: 'var(--space-2) var(--space-4)', backgroundColor: 'var(--color-success, #16a34a)', color: 'white', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer' }}>
          ✓ Duyệt
        </button>
        <button type="button" onClick={() => onReject('Không đủ lý do')} style={{ padding: 'var(--space-2) var(--space-4)', backgroundColor: 'var(--color-error, #dc2626)', color: 'white', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer' }}>
          ✗ Từ chối
        </button>
        <button type="button" onClick={onEscalate} style={{ padding: 'var(--space-2) var(--space-4)', backgroundColor: 'transparent', border: '1px solid var(--color-neutral-400)', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: 'var(--font-size-sm)' }}>
          ↑ Chuyển cấp trên
        </button>
      </section>
    </article>
  );
}
