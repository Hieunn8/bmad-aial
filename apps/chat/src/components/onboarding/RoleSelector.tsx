/**
 * RoleSelector — Screen 0, mandatory role selection (Story 2A.9, UX-DR26a).
 *
 * 3 visual options; user CANNOT proceed without selecting.
 * Role preference stored server-side via POST /v1/user/role-preference.
 */
import { useState } from 'react';

export type UserRole = 'reporting' | 'answering' | 'analysis';

export interface RoleOption {
  role: UserRole;
  emoji: string;
  label: string;
}

export const ROLE_OPTIONS: RoleOption[] = [
  { role: 'reporting', emoji: '📅', label: 'Báo cáo định kỳ' },
  { role: 'answering', emoji: '⚡', label: 'Trả lời câu hỏi từ sếp' },
  { role: 'analysis', emoji: '🔍', label: 'Phân tích chuyên sâu' },
];

export interface RoleSelectorProps {
  onSelect: (role: UserRole) => void;
  selected?: UserRole | null;
}

export function RoleSelector({ onSelect, selected }: RoleSelectorProps): React.JSX.Element {
  return (
    <div
      role="group"
      aria-label="Chọn cách bạn dùng dữ liệu"
      style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3, 12px)', width: '100%' }}
    >
      {ROLE_OPTIONS.map(({ role, emoji, label }) => {
        const isSelected = selected === role;
        return (
          <button
            key={role}
            type="button"
            onClick={() => onSelect(role)}
            aria-pressed={isSelected}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-3, 12px)',
              padding: 'var(--space-4, 16px)',
              border: `2px solid ${isSelected ? 'var(--color-primary, #2563eb)' : 'var(--color-border, #e5e7eb)'}`,
              borderRadius: 'var(--radius-lg, 8px)',
              backgroundColor: isSelected ? 'var(--color-primary-50, #eff6ff)' : 'transparent',
              cursor: 'pointer',
              width: '100%',
              textAlign: 'left',
              fontSize: 'var(--font-size-md, 1rem)',
              fontFamily: 'var(--font-family-base)',
              color: 'var(--color-neutral-900, #111827)',
              transition: 'border-color 150ms ease, background-color 150ms ease',
            }}
          >
            <span aria-hidden="true" style={{ fontSize: '1.5rem' }}>{emoji}</span>
            <span style={{ fontWeight: isSelected ? 'var(--font-weight-semibold, 600)' : 'normal' }}>
              {label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
