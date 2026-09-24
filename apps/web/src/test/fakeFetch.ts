export interface FakeRoute {
  readonly status: number
  readonly body: unknown
  readonly contentType?: string
}

/** A fetch stand-in that answers by URL path; `null` means "never resolves" (cold start). */
export function fakeFetch(routes: Record<string, FakeRoute | null>) {
  return async (input: Request): Promise<Response> => {
    const route = routes[new URL(input.url).pathname]
    if (route === undefined) return new Response('not found', { status: 404 })
    if (route === null) return new Promise<Response>(() => undefined)
    const contentType = route.contentType ?? 'application/json'
    const payload = typeof route.body === 'string' ? route.body : JSON.stringify(route.body)
    return new Response(payload, { status: route.status, headers: { 'content-type': contentType } })
  }
}
