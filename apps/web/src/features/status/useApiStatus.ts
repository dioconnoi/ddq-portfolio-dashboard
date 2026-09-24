import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import type { ApiClient } from '../../api/client'
import { deriveStatus, type ApiStatus } from './deriveStatus'

/** One attempt may wait this long: long enough for a free-tier API to wake from sleep. */
const REQUEST_TIMEOUT_MS = 90_000
/** Transient failures (a gateway 502 while the API boots) are retried; a timeout is not. */
const MAX_RETRIES = 2
const TICK_MS = 500

export interface ApiSnapshot {
  readonly version: string
  readonly environment: string
  readonly dbOk: boolean
}

/** Read `data.checks.database.ok` from an untyped body: error bodies may be plain text. */
function readDbOk(body: unknown): boolean {
  if (typeof body !== 'object' || body === null) return false
  const data = (body as { data?: { checks?: { database?: { ok?: unknown } } } }).data
  return data?.checks?.database?.ok === true
}

function isTimeout(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'TimeoutError'
}

/** Abort when the parent (react-query cancellation) aborts or the deadline passes. */
function withDeadline(parent: AbortSignal, ms: number): { signal: AbortSignal; clear: () => void } {
  const controller = new AbortController()
  const onParentAbort = () => controller.abort(parent.reason)
  if (parent.aborted) onParentAbort()
  else parent.addEventListener('abort', onParentAbort, { once: true })
  const timer = setTimeout(
    () => controller.abort(new DOMException('The API did not answer in time', 'TimeoutError')),
    ms,
  )
  return {
    signal: controller.signal,
    clear: () => {
      clearTimeout(timer)
      parent.removeEventListener('abort', onParentAbort)
    },
  }
}

async function fetchSnapshot(client: ApiClient, parent: AbortSignal): Promise<ApiSnapshot> {
  const { signal, clear } = withDeadline(parent, REQUEST_TIMEOUT_MS)
  try {
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
  } finally {
    clear()
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
    queryFn: ({ signal }) => fetchSnapshot(client, signal),
    retry: (failureCount, error) => !isTimeout(error) && failureCount < MAX_RETRIES,
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
  return { status, snapshot: query.data, refetch: () => void query.refetch() }
}
