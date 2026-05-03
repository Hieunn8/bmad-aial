export type JobVisualState = 'queued' | 'running' | 'ready' | 'failed' | 'expired';

export interface ExportJobStatusProps {
  state: JobVisualState;
  title: string;
  detail?: string;
  etaLabel?: string | null;
}

const STATE_STYLE: Record<JobVisualState, { label: string; color: string; background: string }> = {
  queued: {
    label: 'Đã vào hàng đợi',
    color: '#9a3412',
    background: 'rgba(154, 52, 18, 0.09)',
  },
  running: {
    label: 'Đang xử lý',
    color: '#0f766e',
    background: 'rgba(15, 118, 110, 0.09)',
  },
  ready: {
    label: 'Sẵn sàng',
    color: '#166534',
    background: 'rgba(22, 101, 52, 0.1)',
  },
  failed: {
    label: 'Thất bại',
    color: '#b91c1c',
    background: 'rgba(185, 28, 28, 0.08)',
  },
  expired: {
    label: 'Đã hết hạn',
    color: '#7c2d12',
    background: 'rgba(124, 45, 18, 0.08)',
  },
};

export function ExportJobStatus({
  state,
  title,
  detail,
  etaLabel,
}: ExportJobStatusProps): React.JSX.Element {
  const style = STATE_STYLE[state];

  return (
    <section
      aria-label={`Trạng thái job: ${style.label}`}
      style={{
        borderRadius: '1rem',
        border: `1px solid ${style.color}`,
        background: style.background,
        padding: '0.95rem 1rem',
        display: 'grid',
        gap: '0.35rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center' }}>
        <strong style={{ color: style.color }}>{title}</strong>
        <span
          style={{
            borderRadius: '999px',
            padding: '0.2rem 0.55rem',
            background: 'rgba(255,255,255,0.72)',
            color: style.color,
            fontSize: '0.8rem',
            fontWeight: 700,
          }}
        >
          {style.label}
        </span>
      </div>
      {detail ? <div style={{ color: 'var(--color-neutral-700)', lineHeight: 1.5 }}>{detail}</div> : null}
      {etaLabel ? <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.86rem' }}>{etaLabel}</div> : null}
    </section>
  );
}
