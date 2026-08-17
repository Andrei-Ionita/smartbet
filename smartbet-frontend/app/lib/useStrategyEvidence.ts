'use client'

import { useEffect, useState } from 'react'

export type EvidenceStatus =
  | 'not_started'
  | 'insufficient_evidence'
  | 'collecting_evidence'
  | 'review_ready'
  | 'validated'

export interface PublicStrategyEvidence {
  strategy_key: string
  version: string
  market: string
  evidence_status: EvidenceStatus
  forward_settled: number
  minimum_forward_settled_for_review: number
  evidence_progress_percent: number
  promotion_ready: boolean
}

export function useStrategyEvidence() {
  const [evidence, setEvidence] = useState<Record<string, PublicStrategyEvidence>>({})
  const [available, setAvailable] = useState(true)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    fetch('/api/strategy-lab', { cache: 'no-store' })
      .then(async (response) => {
        if (!response.ok) throw new Error(String(response.status))
        return response.json()
      })
      .then((body) => {
        if (!active) return
        const rows: PublicStrategyEvidence[] = body?.data?.strategies ?? []
        setEvidence(Object.fromEntries(rows.map((row) => [row.strategy_key, row])))
        setLoading(false)
      })
      .catch(() => {
        if (active) {
          setAvailable(false)
          setLoading(false)
        }
      })
    return () => { active = false }
  }, [])

  return { evidence, available, loading }
}
