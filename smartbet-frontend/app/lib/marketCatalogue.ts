import type { SportMonksOdd } from './oddsSelection'

export type MarketCatalogueCategory =
  | 'popular'
  | 'handicaps'
  | 'goals'
  | 'team'
  | 'halves'
  | 'scores'
  | 'cards_corners'
  | 'specials'

export type MarketConsiderationStatus = 'modelled' | 'shadow' | 'prices_only'

export interface MarketCatalogueSelection {
  key: string
  label: string
  reference_price: number
  bookmaker: string
  bookmaker_count: number
  price_min: number
  price_max: number
  captured_at: string
}

export interface MarketCatalogueLine {
  key: string
  label: string | null
  selections: MarketCatalogueSelection[]
}

export interface MarketCatalogueMarket {
  market_id: number
  name: string
  category: MarketCatalogueCategory
  consideration_status: MarketConsiderationStatus
  lines: MarketCatalogueLine[]
  selection_count: number
  bookmaker_count: number
}

export interface FixtureMarketCatalogue {
  generated_at: string
  market_count: number
  selection_count: number
  bookmaker_count: number
  modelled_market_count: number
  shadow_market_count: number
  markets: MarketCatalogueMarket[]
}

const finitePrice = (value: unknown): number | null => {
  const parsed = typeof value === 'number' ? value : Number(String(value ?? '').trim())
  return Number.isFinite(parsed) && parsed > 1 ? parsed : null
}

const clean = (value: unknown): string => String(value ?? '').trim().replace(/\s+/g, ' ')

const numericLine = (value: unknown): number | null => {
  const raw = clean(value)
  if (!raw || raw.includes(',')) return null
  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : null
}

const lineIdentity = (odd: SportMonksOdd): { key: string; label: string | null } => {
  const handicap = clean(odd.handicap)
  if (handicap) {
    const parsed = numericLine(handicap)
    const magnitude = parsed === null ? handicap : String(Math.abs(parsed))
    return { key: `handicap:${magnitude}`, label: `Handicap ${magnitude}` }
  }

  const total = clean(odd.total)
  if (total) return { key: `total:${total}`, label: `Line ${total}` }
  return { key: 'main', label: null }
}

const outcomeLabel = (odd: SportMonksOdd): string => {
  const label = clean(odd.label)
  const name = clean(odd.name)
  const handicap = clean(odd.handicap)
  const total = clean(odd.total)
  const market = clean(odd.market_description).toLowerCase()

  if (market.includes('correct score') && name) return name
  if (handicap) return `${label || name || 'Selection'} ${handicap}`.trim()
  if (total && /^(over|under)$/i.test(label || name)) return `${label || name} ${total}`
  if (label && name && label.toLowerCase() !== name.toLowerCase() && !/^[12x]$/i.test(label)) {
    return label
  }
  return label || name || 'Selection'
}

const categoryFor = (name: string): MarketCatalogueCategory => {
  const value = name.toLowerCase()
  if (/handicap/.test(value)) return 'handicaps'
  if (/corner|card|booking/.test(value)) return 'cards_corners'
  if (/correct score|scorecast|winning margin|exact/.test(value)) return 'scores'
  if (/half|minute|time of|period/.test(value)) return 'halves'
  if (/goal|score|btts|both teams/.test(value)) return 'goals'
  if (/team|clean sheet|first to/.test(value)) return 'team'
  if (/result|double chance|draw no bet|home\/away/.test(value)) return 'popular'
  return 'specials'
}

const considerationFor = (
  marketId: number,
  name: string,
  lineLabel: string | null,
): MarketConsiderationStatus => {
  // Direct prediction distributions currently returned by the subscribed feed.
  if ([1, 2, 14, 29, 31, 57, 247].includes(marketId)) return 'modelled'
  if ([7, 80].includes(marketId)) {
    const line = Number(lineLabel?.replace(/^Line\s+/i, ''))
    return [1.5, 2.5, 3.5].includes(line) ? 'modelled' : 'shadow'
  }

  // These markets are deliberately captured for forward evaluation. They do
  // not become Gems until a calibrated outcome model and settlement contract
  // exist for the exact line.
  if (marketId === 86 || /handicap|goal line|alternative/i.test(name)) return 'shadow'
  return 'prices_only'
}

interface Quote {
  price: number
  bookmakerId: number | null
  bookmaker: string
  capturedAt: string
  oddId: number | null
}

/**
 * Collapse a large raw odds payload into deterministic market/line/selection
 * boards. Every displayed reference price uses the same conservative lower
 * median policy as published BetGlitch picks; stopped, suspended, anonymous or
 * undated quotes are excluded.
 */
export function buildMarketCatalogue(
  odds: SportMonksOdd[] | null | undefined,
  generatedAt = new Date(),
): FixtureMarketCatalogue {
  const marketMap = new Map<number, {
    name: string
    lines: Map<string, { label: string | null; selections: Map<string, { label: string; quotes: Quote[] }> }>
  }>()

  for (const odd of Array.isArray(odds) ? odds : []) {
    if (odd.stopped === true || odd.suspended === true || typeof odd.market_id !== 'number') continue
    const price = finitePrice(odd.value)
    const bookmaker = clean(odd.bookmaker?.name)
    const capturedAt = clean(odd.latest_bookmaker_update)
    if (price === null || !bookmaker || !capturedAt) continue

    const marketId = odd.market_id
    const marketName = clean(odd.market_description) || `Market ${marketId}`
    const line = lineIdentity(odd)
    const label = outcomeLabel(odd)
    const selectionKey = label.toLowerCase()

    if (!marketMap.has(marketId)) marketMap.set(marketId, { name: marketName, lines: new Map() })
    const market = marketMap.get(marketId)!
    if (!market.lines.has(line.key)) {
      market.lines.set(line.key, { label: line.label, selections: new Map() })
    }
    const lineGroup = market.lines.get(line.key)!
    if (!lineGroup.selections.has(selectionKey)) {
      lineGroup.selections.set(selectionKey, { label, quotes: [] })
    }
    lineGroup.selections.get(selectionKey)!.quotes.push({
      price,
      bookmakerId: odd.bookmaker_id ?? null,
      bookmaker,
      capturedAt,
      oddId: odd.id ?? null,
    })
  }

  const bookmakerIds = new Set<string>()
  const markets: MarketCatalogueMarket[] = []

  for (const [marketId, rawMarket] of Array.from(marketMap.entries())) {
    const marketBooks = new Set<string>()
    const lines: MarketCatalogueLine[] = []

    for (const [lineKey, rawLine] of Array.from(rawMarket.lines.entries())) {
      const selections: MarketCatalogueSelection[] = []
      for (const [selectionKey, rawSelection] of Array.from(rawLine.selections.entries())) {
        const latestByBook = new Map<string, Quote>()
        for (const quote of rawSelection.quotes) {
          const bookKey = String(quote.bookmakerId ?? quote.bookmaker)
          const previous = latestByBook.get(bookKey)
          if (!previous || quote.capturedAt > previous.capturedAt) latestByBook.set(bookKey, quote)
        }
        const quotes = Array.from(latestByBook.values())
        quotes.sort((a, b) =>
          a.price - b.price ||
          (a.bookmakerId ?? 0) - (b.bookmakerId ?? 0) ||
          (a.oddId ?? 0) - (b.oddId ?? 0))
        const chosen = quotes[Math.floor((quotes.length - 1) / 2)]
        const prices = quotes.map((quote) => quote.price)
        for (const quote of quotes) {
          const id = String(quote.bookmakerId ?? quote.bookmaker)
          marketBooks.add(id)
          bookmakerIds.add(id)
        }
        selections.push({
          key: selectionKey,
          label: rawSelection.label,
          reference_price: chosen.price,
          bookmaker: chosen.bookmaker,
          bookmaker_count: quotes.length,
          price_min: prices[0],
          price_max: prices[prices.length - 1],
          captured_at: chosen.capturedAt,
        })
      }

      selections.sort((a, b) => a.label.localeCompare(b.label, undefined, { numeric: true }))
      if (selections.length) lines.push({ key: lineKey, label: rawLine.label, selections })
    }

    lines.sort((a, b) => (a.label ?? '').localeCompare(b.label ?? '', undefined, { numeric: true }))
    if (!lines.length) continue
    const statuses = lines.map((line) => considerationFor(marketId, rawMarket.name, line.label))
    const considerationStatus = statuses.includes('modelled')
      ? 'modelled'
      : statuses.includes('shadow')
        ? 'shadow'
        : 'prices_only'

    markets.push({
      market_id: marketId,
      name: rawMarket.name,
      category: categoryFor(rawMarket.name),
      consideration_status: considerationStatus,
      lines,
      selection_count: lines.reduce((sum, line) => sum + line.selections.length, 0),
      bookmaker_count: marketBooks.size,
    })
  }

  const statusRank: Record<MarketConsiderationStatus, number> = { modelled: 0, shadow: 1, prices_only: 2 }
  markets.sort((a, b) =>
    statusRank[a.consideration_status] - statusRank[b.consideration_status] ||
    a.name.localeCompare(b.name))

  return {
    generated_at: generatedAt.toISOString(),
    market_count: markets.length,
    selection_count: markets.reduce((sum, market) => sum + market.selection_count, 0),
    bookmaker_count: bookmakerIds.size,
    modelled_market_count: markets.filter((market) => market.consideration_status === 'modelled').length,
    shadow_market_count: markets.filter((market) => market.consideration_status === 'shadow').length,
    markets,
  }
}
