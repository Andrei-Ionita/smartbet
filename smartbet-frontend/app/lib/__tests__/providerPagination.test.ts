import { describe, it, expect, vi } from 'vitest'
import { fetchProviderPages } from '../providerPagination'
describe('complete provider scanning', () => {
  it('fetches beyond the first page on the original trusted endpoint', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce({ data: [1], pagination: { has_more: true, next_page: 'https://untrusted.test' } }).mockResolvedValueOnce({ data: [2], pagination: { has_more: false } })
    expect((await fetchProviderPages('https://api.example.test/fixtures?per_page=50', fetcher)).data).toEqual([1, 2])
    expect(fetcher.mock.calls[1][0]).toBe('https://api.example.test/fixtures?per_page=50&page=2')
  })
  it('does not label a truncated scan complete', async () => {
    await expect(fetchProviderPages('https://api.example.test', async () => ({ data: [1], pagination: { has_more: true } }), 2)).rejects.toThrow('scan limit')
  })
  it('propagates a failed later page instead of returning a partial league', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce({ data: [1], pagination: { has_more: true } }).mockRejectedValueOnce(new Error('timeout'))
    await expect(fetchProviderPages('https://api.example.test', fetcher)).rejects.toThrow('timeout')
  })
})
