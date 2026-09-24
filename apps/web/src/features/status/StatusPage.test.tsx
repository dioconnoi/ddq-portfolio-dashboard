import { act, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApiClient } from '../../api/client'
import { fakeFetch } from '../../test/fakeFetch'
import { renderWithProviders } from '../../test/utils'
import { StatusPage } from './StatusPage'

const HEALTH = {
  status: 200,
  body: {
    data: { status: 'ok', version: '0.1.0', environment: 'production' },
    error: null,
    meta: {},
  },
}
const READY_OK = {
  status: 200,
  body: { data: { status: 'ready', checks: { database: { ok: true } } }, error: null, meta: {} },
}
const READY_DOWN = {
  status: 503,
  body: {
    data: { status: 'degraded', checks: { database: { ok: false } } },
    error: { code: 'not_ready', message: 'x', details: null },
    meta: {},
  },
}

const clientFor = (routes: Parameters<typeof fakeFetch>[0]) =>
  createApiClient('http://api.test', fakeFetch(routes))

afterEach(() => vi.useRealTimers())

describe('StatusPage', () => {
  it('shows online with version and a connected database', async () => {
    renderWithProviders(
      <StatusPage client={clientFor({ '/health': HEALTH, '/ready': READY_OK })} />,
    )
    expect(await screen.findByText('Online')).toBeInTheDocument()
    expect(screen.getByText('0.1.0')).toBeInTheDocument()
    expect(screen.getByText('Connected')).toBeInTheDocument()
  })

  it('shows degraded when the database check fails', async () => {
    renderWithProviders(
      <StatusPage client={clientFor({ '/health': HEALTH, '/ready': READY_DOWN })} />,
    )
    expect(await screen.findByText('Degraded')).toBeInTheDocument()
    expect(screen.getByText('Unavailable')).toBeInTheDocument()
  })

  it('treats a non-JSON 502 page (Render cold start) as offline without crashing', async () => {
    const html = { status: 502, body: '<html>Bad Gateway</html>', contentType: 'text/html' }
    renderWithProviders(<StatusPage client={clientFor({ '/health': html, '/ready': html })} />)
    expect(await screen.findByText('Offline')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('explains the cold start once the API has been silent for a few seconds', async () => {
    vi.useFakeTimers()
    renderWithProviders(<StatusPage client={clientFor({ '/health': null, '/ready': null })} />)
    expect(screen.getByText('Checking')).toBeInTheDocument()
    await act(async () => {
      vi.advanceTimersByTime(3500)
    })
    expect(screen.getByText(/waking the api/i)).toBeInTheDocument()
  })

  it('retries when the user asks', async () => {
    const html = { status: 502, body: 'bad', contentType: 'text/plain' }
    const routes: Parameters<typeof fakeFetch>[0] = { '/health': html, '/ready': html }
    const client = createApiClient('http://api.test', (req) => fakeFetch(routes)(req))
    renderWithProviders(<StatusPage client={client} />)
    await screen.findByText('Offline')
    routes['/health'] = HEALTH
    routes['/ready'] = READY_OK
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(await screen.findByText('Online')).toBeInTheDocument()
  })
})
