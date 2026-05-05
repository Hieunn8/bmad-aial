/**
 * Tests for design tokens CSS file
 * Story 1.7 AC1: CSS custom properties from packages/ui/src/styles/tokens.css are loaded
 * Deep Teal #0F7B6C, warm gray neutrals, animation tokens
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';

const TOKENS_CSS_PATH = '../../packages/ui/src/styles/tokens.css';

function loadTokensCSS(): string {
  return readFileSync(TOKENS_CSS_PATH, 'utf-8');
}

describe('Design Tokens CSS', () => {
  it('tokens.css file exists at packages/ui/src/styles/tokens.css', () => {
    expect(() => loadTokensCSS()).not.toThrow();
  });

  it('contains Deep Teal #0F7B6C as primary color', () => {
    const css = loadTokensCSS();
    expect(css).toContain('#0F7B6C');
  });

  it('contains warm gray neutral system', () => {
    const css = loadTokensCSS();
    // Warm gray uses hsl with slight warm tone (hue 20-40 for warm gray)
    expect(css).toContain('--color-neutral-');
    expect(css).toContain('--color-neutral-50');
    expect(css).toContain('--color-neutral-900');
  });

  it('contains animation tokens', () => {
    const css = loadTokensCSS();
    expect(css).toContain('--animation-duration-fast');
    expect(css).toContain('--animation-duration-base');
    expect(css).toContain('--animation-duration-slow');
    expect(css).toContain('--animation-ease-');
  });

  it('includes prefers-reduced-motion media query', () => {
    const css = loadTokensCSS();
    expect(css).toContain('prefers-reduced-motion: reduce');
    // Animation tokens should be zeroed out
    expect(css).toMatch(/prefers-reduced-motion[\s\S]*?animation-duration.*?0ms/);
  });

  it('loads Inter + Noto Sans Vietnamese fonts', () => {
    const css = loadTokensCSS();
    // Font import or font-family reference
    expect(css).toMatch(/Inter/i);
    expect(css).toMatch(/Noto Sans/i);
    expect(css).toMatch(/Vietnamese/i);
  });

  it('contains --font-family-base with correct font stack', () => {
    const css = loadTokensCSS();
    expect(css).toContain('--font-family-base');
    expect(css).toContain('sans-serif');
  });

  it('defines 8-color data visualization palette', () => {
    const css = loadTokensCSS();
    for (let i = 1; i <= 8; i++) {
      expect(css).toContain(`--color-data-${i}`);
    }
  });

  it('contains :root block with all required tokens', () => {
    const css = loadTokensCSS();
    expect(css).toContain(':root {');

    // Primary color tokens
    expect(css).toContain('--color-primary');

    // Typography
    expect(css).toContain('--font-size-');
    expect(css).toContain('--font-weight-');

    // Spacing
    expect(css).toContain('--space-');

    // Z-index
    expect(css).toContain('--z-');

    // Shadows
    expect(css).toContain('--shadow-');
  });

  it('includes :focus-visible with primary color outline', () => {
    const css = loadTokensCSS();
    expect(css).toContain(':focus-visible');
    expect(css).toContain('--color-primary');
  });
});
