import createClient from 'openapi-fetch'
import { API_URL } from '../config'
import type { paths } from './schema'

type FetchImpl = (input: Request) => Promise<Response>

export function createApiClient(baseUrl: string, fetchImpl: FetchImpl = (input) => fetch(input)) {
  return createClient<paths>({ baseUrl, fetch: fetchImpl })
}

export type ApiClient = ReturnType<typeof createApiClient>

export const apiClient: ApiClient = createApiClient(API_URL)
