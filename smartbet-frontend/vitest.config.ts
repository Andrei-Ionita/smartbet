import { defineConfig } from 'vitest/config'
import { fileURLToPath } from 'node:url'

/**
 * Scoped to pure logic modules under app/lib. These tests must not need a DOM,
 * a Next runtime, or network access — they exist to lock down correctness of
 * odds selection after the 2026-07-29 capture defect, and the public formatting
 * of proof surfaces.
 *
 * The `@` alias mirrors tsconfig's paths mapping. Without it, importing a real
 * route handler fails at its own `@/app/lib/...` imports, which is how the
 * route-contract tests could only ever inspect source text rather than invoke
 * the handlers.
 */
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./', import.meta.url)),
    },
  },
  test: {
    environment: 'node',
    include: ['app/lib/**/*.test.ts'],
    exclude: ['**/node_modules/**', '**/.next/**'],
    watch: false,
  },
})
