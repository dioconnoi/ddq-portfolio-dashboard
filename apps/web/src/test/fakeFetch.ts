export interface FakeRoute {
  readonly status: number
  readonly body: unknown
  readonly contentType?: string
}

/** A fetch stand-in that answers by URL path; `null` means "never answers" (cold start). */
export function fakeFetch(routes: Record<string, FakeRoute | null>) {
  return async (input: Request): Promise<Response> => {
    const route = routes[new URL(input.url).pathname]
    if (route === undefined) return new Response('not found', { status: 404 })
    if (route === null) {
      return new Promise<Response>((_resolve, reject) => {
        input.signal.addEventListener('abort', () => reject(input.signal.reason))
      })
    }
    const contentType = route.contentType ?? 'application/json'
    const payload = typeof route.body === 'string' ? route.body : JSON.stringify(route.body)
    return new Response(payload, { status: route.status, headers: { 'content-type': contentType } })
  }
}
