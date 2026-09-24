const DEFAULT_DEV_API_URL = 'http://localhost:8000'

/**
 * Validate the API base URL. Shared by the runtime (config.ts) and the build (vite.config.ts) so
 * a bad value fails the build instead of shipping a page that throws before React renders.
 */
export function resolveApiUrl(raw: string | undefined, isProd: boolean): string {
  if (!raw) {
    if (isProd) throw new Error('VITE_API_URL is required for production builds')
    return DEFAULT_DEV_API_URL
  }
  const url = new URL(raw) // throws on an invalid URL
  // `new URL('localhost:8000')` parses successfully with protocol "localhost:", so check it.
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error('VITE_API_URL must be an http(s) URL, for example https://api.example.com')
  }
  if (isProd && url.protocol !== 'https:') {
    throw new Error('VITE_API_URL must use https in production')
  }
  return url.origin
}
