export type ApiStatus = 'checking' | 'waking' | 'online' | 'degraded' | 'offline'

/** After this long without a response we assume the free-tier API is waking from sleep. */
export const WAKE_THRESHOLD_MS = 3000

export interface StatusInputs {
  readonly isLoading: boolean
  readonly elapsedMs: number
  readonly hasSnapshot: boolean
  readonly failed: boolean
  readonly dbOk: boolean
}

export function deriveStatus(inputs: StatusInputs): ApiStatus {
  if (inputs.isLoading) return inputs.elapsedMs >= WAKE_THRESHOLD_MS ? 'waking' : 'checking'
  if (inputs.failed || !inputs.hasSnapshot) return 'offline'
  return inputs.dbOk ? 'online' : 'degraded'
}
