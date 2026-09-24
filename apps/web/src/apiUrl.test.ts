import { describe, expect, it } from 'vitest'
import { resolveApiUrl } from './apiUrl'

describe('resolveApiUrl', () => {
  it('defaults to localhost in development', () => {
    expect(resolveApiUrl(undefined, false)).toBe('http://localhost:8000')
  })

  it('requires the variable in production builds', () => {
    expect(() => resolveApiUrl(undefined, true)).toThrow(/VITE_API_URL/)
  })

  it('requires https in production', () => {
    expect(() => resolveApiUrl('http://api.example.com', true)).toThrow(/https/)
    expect(resolveApiUrl('https://api.example.com', true)).toBe('https://api.example.com')
  })

  it('reduces the value to a clean origin', () => {
    expect(resolveApiUrl('https://api.example.com/some/path/', true)).toBe(
      'https://api.example.com',
    )
  })

  it('rejects values that are not URLs', () => {
    expect(() => resolveApiUrl('not a url', false)).toThrow()
  })

  it('rejects a host without a scheme (which URL parses as a custom protocol)', () => {
    expect(() => resolveApiUrl('localhost:8000', false)).toThrow(/http/)
    expect(() => resolveApiUrl('ddq-api.onrender.com', true)).toThrow()
  })

  it('rejects non-http protocols in every mode', () => {
    expect(() => resolveApiUrl('ftp://api.example.com', false)).toThrow(/http/)
  })
})
