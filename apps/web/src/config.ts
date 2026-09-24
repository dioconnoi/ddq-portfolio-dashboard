const DEFAULT_DEV_API_URL = 'http://localhost:8000'

export function resolveApiUrl(raw: string | undefined, isProd: boolean): string {
  if (!raw) {
    if (isProd) throw new Error('VITE_API_URL is required for production builds')
    return DEFAULT_DEV_API_URL
  }
  const url = new URL(raw) // throws on an invalid URL
  if (isProd && url.protocol !== 'https:') {
    throw new Error('VITE_API_URL must use https in production')
  }
  return url.origin
}

export const API_URL = resolveApiUrl(import.meta.env.VITE_API_URL, import.meta.env.PROD)
