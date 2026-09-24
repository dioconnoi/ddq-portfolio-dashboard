import type { ApiClient } from '../../api/client'
import type { ApiStatus } from './deriveStatus'
import { useApiStatus } from './useApiStatus'

const LABEL: Record<ApiStatus, string> = {
  checking: 'Checking',
  waking: 'Waking',
  online: 'Online',
  degraded: 'Degraded',
  offline: 'Offline',
}
const ICON: Record<ApiStatus, string> = {
  checking: '…',
  waking: '⏳',
  online: '✓',
  degraded: '!',
  offline: '✕',
}
const TONE: Record<ApiStatus, string> = {
  checking: 'text-muted',
  waking: 'text-warn',
  online: 'text-good',
  degraded: 'text-warn',
  offline: 'text-bad',
}

export function StatusPage({ client }: { client: ApiClient }) {
  const { status, snapshot, refetch } = useApiStatus(client)
  return (
    <section aria-labelledby="status-heading" className="space-y-4">
      <h2 id="status-heading" className="text-xl font-semibold">
        System status
      </h2>
      <div
        role="status"
        aria-live="polite"
        className="rounded-lg border border-border bg-surface p-5"
      >
        <p className={`text-lg font-medium ${TONE[status]}`}>
          <span aria-hidden="true">{ICON[status]} </span>
          {status === 'waking' ? 'Waking the API…' : LABEL[status]}
        </p>
        {status === 'waking' && (
          <p className="mt-2 text-sm text-muted">
            The free-tier API sleeps when idle. Waking it takes about 30–60 seconds.
          </p>
        )}
        {(status === 'offline' || status === 'degraded') && (
          <button
            type="button"
            onClick={refetch}
            className="mt-3 rounded-md bg-accent px-3 py-1.5 text-sm text-accent-contrast"
          >
            Retry
          </button>
        )}
      </div>
      {snapshot && (
        <dl className="grid grid-cols-3 gap-3 text-sm">
          <Fact label="API version" value={snapshot.version} />
          <Fact label="Environment" value={snapshot.environment} />
          <Fact label="Database" value={snapshot.dbOk ? 'Connected' : 'Unavailable'} />
        </dl>
      )}
    </section>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <dt className="text-muted">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  )
}
