import type { Metadata } from 'next'
import MarketsContent from './MarketsContent'
export const metadata: Metadata = { title: 'Football selections by market | BetGlitch', description: 'Explore up to five recorded football selections per market, with price comparisons, uncertainty and results.' }
export default function MarketsPage() { return <MarketsContent /> }
