import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import type { ApiClient } from '../../api/client'
import { deriveStatus, type ApiStatus } from './deriveStatus'

const REQUEST_TIMEOUT_MS = 90_000
const TICK_MS = 500

export interface ApiSnapshot {
  readonly version: string
  readonly environment: string
  readonly dbOk: boolean
}

function readDbOk(body: unknown): boolean {
  if (typeof body !== 'object' || body === null) return false
  const data = (body as { data?: { checks?: { database?: { ok?: unknown } } } }).data
  return data?.checks?.database?.ok === true
}

async function fetchSnapshot(client: ApiClient): Promise<ApiSnapshot> {
  const signal = AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  const [health, ready] = await Promise.all([
    client.GET('/health', { signal }),
    client.GET('/ready', { signal }),
  ])
  const info = health.data?.data
  if (!info) throw new Error('API returned an unexpected response')
  return {
    version: info.version,
    environment: info.environment,
    dbOk: readDbOk(ready.data ?? ready.error),
  }
}

function useElapsedMs(active: boolean): number {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    if (!active) return
    const start = Date.now()
    const id = setInterval(() => setElapsed(Date.now() - start), TICK_MS)
    return () => {
      clearInterval(id)
      setElapsed(0)
    }
  }, [active])
  return elapsed
}

export function useApiStatus(client: ApiClient) {
  const query = useQuery({
    queryKey: ['api-status'],
    queryFn: () => fetchSnapshot(client),
    refetchOnWindowFocus: false,
  })
  const elapsedMs = useElapsedMs(query.isFetching)
  const status: ApiStatus = deriveStatus({
    isLoading: query.isFetching,
    elapsedMs,
    hasSnapshot: query.data !== undefined,
    failed: query.isError,
    dbOk: query.data?.dbOk ?? false,
  })
  return { status, snapshot: query.data, elapsedMs, refetch: () => void query.refetch() }
}
