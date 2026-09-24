import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '../test/utils'
import { ThemeToggle } from './ThemeToggle'

afterEach(() => vi.restoreAllMocks())

describe('ThemeToggle', () => {
  it('applies the stored preference and cycles on click, persisting each choice', async () => {
    localStorage.setItem('ddq-theme', 'light')
    renderWithProviders(<ThemeToggle />)
    const button = screen.getByRole('button', { name: /theme/i })

    expect(document.documentElement.dataset.theme).toBe('light')
    await userEvent.click(button)
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('ddq-theme')).toBe('dark')
    expect(button).toHaveAccessibleName(/dark/i)

    await userEvent.click(button) // -> system (matchMedia stub says light)
    expect(localStorage.getItem('ddq-theme')).toBe('system')
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('still switches themes when localStorage is unavailable', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('denied')
    })
    vi.spyOn(window, 'matchMedia').mockImplementation(
      (query: string) =>
        ({
          matches: true,
          media: query,
          addEventListener: () => undefined,
          removeEventListener: () => undefined,
        }) as unknown as MediaQueryList,
    )
    renderWithProviders(<ThemeToggle />)
    expect(document.documentElement.dataset.theme).toBe('dark') // system preference, dark OS

    await userEvent.click(screen.getByRole('button', { name: /theme/i })) // system -> light
    expect(document.documentElement.dataset.theme).toBe('light')
  })
})
