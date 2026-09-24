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

  it('gives up with Offline and a Retry button when the API never answers, without retrying', async () => {
    vi.useFakeTimers()
    let calls = 0
    const silent = fakeFetch({ '/health': null, '/ready': null })
    const client = createApiClient('http://api.test', (req) => {
      calls += 1
      return silent(req)
    })
    renderWithProviders(<StatusPage client={client} />)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(90_001)
    })
    expect(screen.getByText('Offline')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    expect(calls).toBe(2) // /health and /ready once each: a timeout is not retried
  })

  it('retries transient failures a couple of times before giving up', async () => {
    let calls = 0
    const html = { status: 502, body: 'bad gateway', contentType: 'text/plain' }
    const failing = fakeFetch({ '/health': html, '/ready': html })
    const client = createApiClient('http://api.test', (req) => {
      calls += 1
      return failing(req)
    })
    renderWithProviders(<StatusPage client={client} />)
    await screen.findByText('Offline')
    expect(calls).toBeGreaterThanOrEqual(6) // 3 attempts x (/health + /ready)
  })

  it('hides the last-known facts once a refetch has failed', async () => {
    const routes: Parameters<typeof fakeFetch>[0] = { '/health': HEALTH, '/ready': READY_DOWN }
    const client = createApiClient('http://api.test', (req) => fakeFetch(routes)(req))
    renderWithProviders(<StatusPage client={client} />)
    expect(await screen.findByText('Degraded')).toBeInTheDocument()
    expect(screen.getByText('0.1.0')).toBeInTheDocument()

    const down = { status: 502, body: 'bad', contentType: 'text/plain' }
    routes['/health'] = down
    routes['/ready'] = down
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(await screen.findByText('Offline')).toBeInTheDocument()
    expect(screen.queryByText('0.1.0')).not.toBeInTheDocument()
  })
})
