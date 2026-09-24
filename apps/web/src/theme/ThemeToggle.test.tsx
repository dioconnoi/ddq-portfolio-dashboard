import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '../test/utils'
import { ThemeToggle } from './ThemeToggle'

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

  it('still renders and works when localStorage is unavailable', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('denied')
    })
    renderWithProviders(<ThemeToggle />)
    await userEvent.click(screen.getByRole('button', { name: /theme/i }))
    expect(document.documentElement.dataset.theme).toBeDefined()
    vi.restoreAllMocks()
  })
})
