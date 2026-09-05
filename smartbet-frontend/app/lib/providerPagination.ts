/** Follow numbered pages on the original endpoint; never forward credentials
 * to a provider-supplied next-page URL. A truncated scan fails explicitly. */
export async function fetchProviderPages(url: string, fetchPage: (url: string) => Promise<any>, maximumPages = 100) {
  const endpoint = new URL(url)
  const rows: any[] = []
  let first: any = null
  for (let page = 1; page <= maximumPages; page++) {
    endpoint.searchParams.set('page', String(page))
    const result = await fetchPage(endpoint.toString())
    if (!Array.isArray(result.data)) throw new Error('Invalid provider page')
    first ??= result
    rows.push(...result.data)
    if (result.pagination?.has_more !== true) return { ...first, data: rows }
  }
  throw new Error('Provider pagination exceeded the scan limit')
}
