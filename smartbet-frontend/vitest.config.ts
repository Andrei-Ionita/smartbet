import { defineConfig } from 'vitest/config'

/**
 * Scoped to pure logic modules under app/lib. These tests must not need a DOM,
 * a Next runtime, or network access — they exist to lock down correctness of
 * odds selection after the 2026-07-29 capture defect.
 */
export default defineConfig({
  test: {
    environment: 'node',
    include: ['app/lib/**/*.test.ts'],
    exclude: ['**/node_modules/**', '**/.next/**'],
    watch: false,
  },
})
