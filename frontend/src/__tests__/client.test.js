/**
 * Unit tests — src/api/client.js
 *
 * Covers: Authorization header injection, successful response parsing,
 * error throwing on non-OK responses, missing token handling.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// ── helpers ──────────────────────────────────────────────────────────────────

function mockFetch(status, body) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

// ── tests ─────────────────────────────────────────────────────────────────────

describe('apiRequest', () => {
  let apiRequest

  beforeEach(async () => {
    // Reset module registry so sessionStorage state doesn't leak between tests
    vi.resetModules()
    sessionStorage.clear()
    const mod = await import('../api/client.js')
    apiRequest = mod.apiRequest
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends Authorization header when token is in sessionStorage', async () => {
    sessionStorage.setItem('token', 'my-jwt-token')
    global.fetch = mockFetch(200, { ok: true })

    await apiRequest('/health')

    const [, options] = global.fetch.mock.calls[0]
    expect(options.headers['Authorization']).toBe('Bearer my-jwt-token')
  })

  it('does NOT send Authorization header when no token stored', async () => {
    global.fetch = mockFetch(200, { data: 'ok' })

    await apiRequest('/health')

    const [, options] = global.fetch.mock.calls[0]
    expect(options.headers['Authorization']).toBeUndefined()
  })

  it('returns parsed JSON on success', async () => {
    global.fetch = mockFetch(200, { status: 'ok' })
    const result = await apiRequest('/health')
    expect(result).toEqual({ status: 'ok' })
  })

  it('throws an error with detail message on non-OK response', async () => {
    global.fetch = mockFetch(400, { detail: 'Email already registered' })
    await expect(apiRequest('/auth/signup')).rejects.toThrow('Email already registered')
  })

  it('throws generic message when no detail field present', async () => {
    global.fetch = mockFetch(500, {})
    await expect(apiRequest('/query')).rejects.toThrow('Request failed')
  })

  it('sends Content-Type application/json by default', async () => {
    global.fetch = mockFetch(200, {})
    await apiRequest('/auth/login')
    const [, options] = global.fetch.mock.calls[0]
    expect(options.headers['Content-Type']).toBe('application/json')
  })

  it('passes through custom options (method, body)', async () => {
    global.fetch = mockFetch(200, {})
    await apiRequest('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email: 'a@b.com' }),
    })
    const [, options] = global.fetch.mock.calls[0]
    expect(options.method).toBe('POST')
    expect(options.body).toBe(JSON.stringify({ email: 'a@b.com' }))
  })

  it('throws on 401 unauthorized', async () => {
    global.fetch = mockFetch(401, { detail: 'Invalid token' })
    await expect(apiRequest('/history')).rejects.toThrow('Invalid token')
  })

  it('throws on 403 forbidden', async () => {
    global.fetch = mockFetch(403, { detail: 'Admin access required' })
    await expect(apiRequest('/admin/users')).rejects.toThrow('Admin access required')
  })
})
