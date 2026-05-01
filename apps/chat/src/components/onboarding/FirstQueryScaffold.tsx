/**
 * FirstQueryScaffold — Screen 2 role-aware query input (Story 2A.9).
 *
 * AC: role-specific placeholder; intent hint after 500ms pause.
 * "First Query Guide" variant for empty data responses.
 */
import { useEffect, useRef, useState } from 'react';
import type { UserRole } from './RoleSelector';

const ROLE_PLACEHOLDERS: Record<UserRole, string> = {
  reporting: 'VD: Doanh thu chi nhánh HCM tháng này?',
  answering: 'VD: Tổng đơn hàng quý 1 so với cùng kỳ năm ngoái?',
  analysis: 'VD: Phân tích xu hướng doanh thu 6 tháng gần nhất theo kênh?',
};

const ROLE_INTENT_HINTS: Record<UserRole, string> = {
  reporting: 'AIAL sẽ dùng dữ liệu từ SALES domain',
  answering: 'AIAL sẽ tổng hợp dữ liệu từ nhiều domain',
  analysis: 'AIAL sẽ phân tích dữ liệu lịch sử chi tiết',
};

const ROLE_SUGGESTED_QUERIES: Record<UserRole, string> = {
  reporting: 'Doanh thu tháng trước theo chi nhánh là bao nhiêu?',
  answering: 'So sánh doanh thu quý này với quý trước như thế nào?',
  analysis: 'Xu hướng tăng trưởng doanh thu 12 tháng qua là gì?',
};

export interface FirstQueryScaffoldProps {
  role: UserRole;
  onSubmit: (query: string) => void;
}

export function FirstQueryScaffold({ role, onSubmit }: FirstQueryScaffoldProps): React.JSX.Element {
  const [value, setValue] = useState('');
  const [showHint, setShowHint] = useState(false);
  const hintTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>): void => {
    setValue(e.target.value);
    if (hintTimerRef.current) clearTimeout(hintTimerRef.current);
    if (e.target.value.length > 0) {
      hintTimerRef.current = setTimeout(() => setShowHint(true), 500);
    } else {
      setShowHint(false);
    }
  };

  useEffect(() => () => { if (hintTimerRef.current) clearTimeout(hintTimerRef.current); }, []);

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    if (value.trim()) onSubmit(value.trim());
  };

  return (
    <form onSubmit={handleSubmit} style={{ width: '100%' }}>
      <div style={{ position: 'relative' }}>
        <textarea
          aria-label="Nhập câu hỏi của bạn"
          placeholder={ROLE_PLACEHOLDERS[role]}
          value={value}
          onChange={handleChange}
          rows={3}
          style={{
            width: '100%',
            padding: 'var(--space-3, 12px)',
            border: '1px solid var(--color-border, #e5e7eb)',
            borderRadius: 'var(--radius-md, 6px)',
            fontSize: 'var(--font-size-md, 1rem)',
            fontFamily: 'var(--font-family-base)',
            resize: 'none',
            boxSizing: 'border-box',
          }}
        />
        {showHint && (
          <div
            role="note"
            aria-live="polite"
            style={{
              marginTop: 'var(--space-1, 4px)',
              fontSize: 'var(--font-size-xs, 0.75rem)',
              color: 'var(--color-primary, #2563eb)',
            }}
          >
            {ROLE_INTENT_HINTS[role]}
          </div>
        )}
      </div>
      <button
        type="submit"
        disabled={!value.trim()}
        style={{
          marginTop: 'var(--space-3, 12px)',
          padding: 'var(--space-2, 8px) var(--space-4, 16px)',
          backgroundColor: 'var(--color-primary, #2563eb)',
          color: 'white',
          border: 'none',
          borderRadius: 'var(--radius-md, 6px)',
          cursor: 'pointer',
          fontSize: 'var(--font-size-md, 1rem)',
          fontFamily: 'var(--font-family-base)',
        }}
      >
        Gửi câu hỏi
      </button>
    </form>
  );
}

export interface FirstQueryGuideProps {
  role: UserRole;
  onTryAlternative: (query: string) => void;
  onGoHome: () => void;
}

export function FirstQueryGuide({ role, onTryAlternative, onGoHome }: FirstQueryGuideProps): React.JSX.Element {
  const suggested = ROLE_SUGGESTED_QUERIES[role];
  return (
    <div
      role="region"
      aria-labelledby="first-query-guide-heading"
      style={{
        padding: 'var(--space-6, 24px)',
        backgroundColor: 'var(--color-surface, white)',
        borderRadius: 'var(--radius-xl, 12px)',
        border: '1px solid var(--color-border, #e5e7eb)',
      }}
    >
      <h2 id="first-query-guide-heading" style={{ fontSize: 'var(--font-size-lg, 1.125rem)', marginBottom: 'var(--space-3)' }}>
        Không tìm thấy dữ liệu
      </h2>
      <p style={{ color: 'var(--color-neutral-600)', marginBottom: 'var(--space-4)' }}>
        Dữ liệu sản xuất cho domain của bạn chưa được kết nối. Bạn có thể thử câu hỏi mẫu sau:
      </p>
      <button
        type="button"
        onClick={() => onTryAlternative(suggested)}
        style={{
          display: 'block',
          width: '100%',
          padding: 'var(--space-3)',
          border: '1px dashed var(--color-primary)',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'transparent',
          cursor: 'pointer',
          textAlign: 'left',
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-primary)',
          marginBottom: 'var(--space-3)',
        }}
      >
        "{suggested}" →
      </button>
      <button type="button" onClick={onGoHome} style={{ color: 'var(--color-neutral-500)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 'var(--font-size-sm)' }}>
        ← Quay về trang chủ
      </button>
    </div>
  );
}
