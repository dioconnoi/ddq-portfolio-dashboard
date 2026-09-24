import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'
import { createApiClient } from './api/client'
import { fakeFetch } from './test/fakeFetch'
import { renderWithProviders } from './test/utils'

describe('App', () => {
  it('shows the product name, the theme toggle and the status page', () => {
    const client = createApiClient(
      'http://api.test',
      fakeFetch({ '/health': null, '/ready': null }),
    )
    renderWithProviders(<App client={client} />)
    expect(screen.getByRole('heading', { name: 'DDQ Portfolio Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /theme/i })).toBeInTheDocument()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
