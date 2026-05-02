/**
 * CitationBadge — Story 2B.2 (UX-DR10)
 *
 * AC: citationNumber from CitationRef object (NOT array index);
 * focusable button; aria-label="Xem nguồn số N";
 * tooltip shows: source name, table/doc reference, freshness;
 * supports type="sql" and type="document".
 */
import { useRef, useState } from 'react';

export interface CitationDetails {
  sourceName: string;
  tableOrDocRef: string;
  freshnessTimestamp: string;
}

export interface CitationRef {
  citationNumber: number;
  type: 'sql' | 'document';
  label: string;
  details: CitationDetails;
}

export interface CitationBadgeProps {
  citation: CitationRef;
}

export function CitationBadge({ citation }: CitationBadgeProps): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);

  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      <button
        ref={buttonRef}
        type="button"
        aria-label={`Xem nguồn số ${citation.citationNumber}`}
        aria-expanded={open}
        aria-haspopup="true"
        onClick={() => setOpen(v => !v)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '1.25rem',
          height: '1.25rem',
          borderRadius: '50%',
          backgroundColor: 'var(--color-primary, #2563eb)',
          color: 'white',
          border: 'none',
          cursor: 'pointer',
          fontSize: '0.65rem',
          fontWeight: 700,
          fontFamily: 'var(--font-family-base)',
          verticalAlign: 'super',
          lineHeight: 1,
        }}
      >
        {citation.citationNumber}
      </button>

      {open && (
        <div
          role="tooltip"
          aria-label={`Nguồn ${citation.citationNumber}: ${citation.label}`}
          style={{
            position: 'absolute',
            zIndex: 50,
            bottom: '1.75rem',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'var(--color-neutral-900, #111827)',
            color: 'white',
            borderRadius: 'var(--radius-md, 6px)',
            padding: 'var(--space-3, 12px)',
            width: '16rem',
            fontSize: 'var(--font-size-sm, 0.875rem)',
            boxShadow: 'var(--shadow-lg)',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
            {citation.type === 'sql' ? '📊' : '📄'} {citation.details.sourceName}
          </div>
          <div style={{ color: 'var(--color-neutral-300, #d1d5db)', marginBottom: '0.25rem' }}>
            {citation.details.tableOrDocRef}
          </div>
          <div style={{ color: 'var(--color-neutral-400, #9ca3af)', fontSize: '0.75rem' }}>
            🕐 {citation.details.freshnessTimestamp}
          </div>
        </div>
      )}
    </span>
  );
}
