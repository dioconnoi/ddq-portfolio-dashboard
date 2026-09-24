import { describe, expect, it } from 'vitest'
import {
  THEME_STORAGE_KEY,
  isThemePreference,
  nextPreference,
  readStoredPreference,
  resolveTheme,
  storePreference,
} from './theme'

describe('theme', () => {
  it('resolves explicit preferences and follows the system for "system"', () => {
    expect(resolveTheme('light', true)).toBe('light')
    expect(resolveTheme('dark', false)).toBe('dark')
    expect(resolveTheme('system', true)).toBe('dark')
    expect(resolveTheme('system', false)).toBe('light')
  })

  it('cycles light -> dark -> system -> light', () => {
    expect(nextPreference('light')).toBe('dark')
    expect(nextPreference('dark')).toBe('system')
    expect(nextPreference('system')).toBe('light')
  })

  it('validates preferences', () => {
    expect(isThemePreference('dark')).toBe(true)
    expect(isThemePreference('purple')).toBe(false)
    expect(isThemePreference(null)).toBe(false)
  })

  it('reads a valid stored preference and defaults otherwise', () => {
    expect(readStoredPreference({ getItem: () => 'dark' })).toBe('dark')
    expect(readStoredPreference({ getItem: () => 'garbage' })).toBe('system')
    expect(readStoredPreference({ getItem: () => null })).toBe('system')
    expect(readStoredPreference(undefined)).toBe('system')
  })

  it('does not crash when storage throws (private mode / blocked storage)', () => {
    const throwing = {
      getItem: () => {
        throw new Error('denied')
      },
      setItem: () => {
        throw new Error('denied')
      },
    }
    expect(readStoredPreference(throwing)).toBe('system')
    expect(() => storePreference(throwing, 'dark')).not.toThrow()
  })

  it('persists under the documented key', () => {
    const calls: Array<[string, string]> = []
    storePreference({ setItem: (k, v) => calls.push([k, v]) }, 'dark')
    expect(calls).toEqual([[THEME_STORAGE_KEY, 'dark']])
  })
})
