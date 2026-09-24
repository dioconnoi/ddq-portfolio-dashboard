import { describe, expect, it } from 'vitest'
import { WAKE_THRESHOLD_MS, deriveStatus } from './deriveStatus'

const base = { isLoading: false, elapsedMs: 0, hasSnapshot: true, failed: false, dbOk: true }

describe('deriveStatus', () => {
  it.each([
    [{ isLoading: true, elapsedMs: 0 }, 'checking'],
    [{ isLoading: true, elapsedMs: WAKE_THRESHOLD_MS - 1 }, 'checking'],
    [{ isLoading: true, elapsedMs: WAKE_THRESHOLD_MS }, 'waking'],
    [{ failed: true }, 'offline'],
    [{ hasSnapshot: false }, 'offline'],
    [{ dbOk: false }, 'degraded'],
    [{}, 'online'],
  ] as const)('%j -> %s', (overrides, expected) => {
    expect(deriveStatus({ ...base, ...overrides })).toBe(expected)
  })
})
