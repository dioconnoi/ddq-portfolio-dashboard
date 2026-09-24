import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'
import { renderWithProviders } from './test/utils'

describe('App', () => {
  it('shows the product name and the theme toggle', () => {
    renderWithProviders(<App />)
    expect(screen.getByRole('heading', { name: 'DDQ Portfolio Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /theme/i })).toBeInTheDocument()
  })
})
