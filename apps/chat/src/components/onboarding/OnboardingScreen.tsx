/**
 * OnboardingScreen — Screen 0 mandatory role selection flow (Story 2A.9).
 *
 * First-time users MUST select a role before proceeding.
 * Role stored server-side — NOT in localStorage.
 */
import { useState } from 'react';
import type { UserRole } from './RoleSelector';
import { RoleSelector } from './RoleSelector';

export interface OnboardingScreenProps {
  onComplete: (role: UserRole) => void;
  /** API base URL for role preference storage */
  apiBaseUrl?: string;
  /** JWT token for authenticated request */
  token?: string;
}

export function OnboardingScreen({ onComplete, apiBaseUrl = '', token }: OnboardingScreenProps): React.JSX.Element {
  const [selected, setSelected] = useState<UserRole | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleContinue = async (): Promise<void> => {
    if (!selected) return;
    setLoading(true);
    setError(null);

    try {
      const resp = await fetch(`${apiBaseUrl}/v1/user/role-preference`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ role: selected }),
      });

      if (!resp.ok) throw new Error(`API error: ${resp.status}`);
      onComplete(selected);
    } catch (err) {
      setError('Không thể lưu lựa chọn. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main
      role="main"
      aria-labelledby="onboarding-heading"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: 'var(--space-6, 24px)',
        backgroundColor: 'var(--color-background, #f9fafb)',
      }}
    >
      <div style={{ width: '100%', maxWidth: '28rem' }}>
        <h1
          id="onboarding-heading"
          style={{
            fontSize: 'var(--font-size-xl, 1.25rem)',
            fontWeight: 'var(--font-weight-semibold, 600)',
            color: 'var(--color-neutral-900, #111827)',
            marginBottom: 'var(--space-6, 24px)',
            textAlign: 'center',
          }}
        >
          Bạn thường dùng dữ liệu để làm gì?
        </h1>

        <RoleSelector onSelect={setSelected} selected={selected} />

        {error && (
          <p
            role="alert"
            style={{ color: 'var(--color-error, #dc2626)', fontSize: 'var(--font-size-sm)', marginTop: 'var(--space-3)' }}
          >
            {error}
          </p>
        )}

        <button
          type="button"
          onClick={() => void handleContinue()}
          disabled={!selected || loading}
          aria-disabled={!selected || loading}
          style={{
            marginTop: 'var(--space-6, 24px)',
            width: '100%',
            padding: 'var(--space-3, 12px)',
            backgroundColor: selected ? 'var(--color-primary, #2563eb)' : 'var(--color-neutral-300, #d1d5db)',
            color: 'white',
            border: 'none',
            borderRadius: 'var(--radius-md, 6px)',
            cursor: selected && !loading ? 'pointer' : 'not-allowed',
            fontSize: 'var(--font-size-md, 1rem)',
            fontWeight: 'var(--font-weight-medium, 500)',
            fontFamily: 'var(--font-family-base)',
            transition: 'background-color 150ms ease',
          }}
        >
          {loading ? 'Đang lưu...' : 'Tiếp tục'}
        </button>
      </div>
    </main>
  );
}
