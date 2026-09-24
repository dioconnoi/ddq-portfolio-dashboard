import { afterEach, describe, expect, it, vi } from 'vitest'
import script from '../../public/theme-init.js?raw'

function stubSystemDark(dark: boolean) {
  vi.spyOn(window, 'matchMedia').mockImplementation(
    (query: string) => ({ matches: dark, media: query }) as MediaQueryList,
  )
}

afterEach(() => vi.restoreAllMocks())

describe('theme-init.js (runs before React to prevent a flash)', () => {
  it('honours a stored preference', () => {
    stubSystemDark(true)
    localStorage.setItem('ddq-theme', 'light')
    new Function(script)()
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('follows a dark system when nothing is stored', () => {
    stubSystemDark(true)
    new Function(script)()
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('still follows a dark system when localStorage throws', () => {
    stubSystemDark(true)
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied')
    })
    new Function(script)()
    expect(document.documentElement.dataset.theme).toBe('dark')
  })
})
