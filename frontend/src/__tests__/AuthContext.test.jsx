/**
 * Unit tests — src/context/AuthContext.jsx
 *
 * Covers: initial state, login stores token and parses role/userId,
 * logout clears sessionStorage, isAuthenticated flag.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { render, act, screen } from '@testing-library/react'
import { AuthProvider, useAuth } from '../context/AuthContext'

// ── helper: minimal component that exposes auth state ────────────────────────

function AuthDisplay() {
  const { isAuthenticated, role, email, userId } = useAuth()
  return (
    <div>
      <span data-testid="auth">{String(isAuthenticated)}</span>
      <span data-testid="role">{role ?? 'null'}</span>
      <span data-testid="email">{email ?? 'null'}</span>
      <span data-testid="userId">{String(userId)}</span>
    </div>
  )
}

function AuthActions() {
  const { login, logout } = useAuth()
  return (
    <>
      <button onClick={() => login({ token: 'fake-token', role: 'user', email: 'test@example.com' })}>Login</button>
      <button onClick={logout}>Logout</button>
    </>
  )
}

function WrappedApp({ children }) {
  return <AuthProvider>{children}</AuthProvider>
}

// ── tests ─────────────────────────────────────────────────────────────────────

describe('AuthContext', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('starts unauthenticated when sessionStorage is empty', () => {
    render(<WrappedApp><AuthDisplay /></WrappedApp>)
    expect(screen.getByTestId('auth').textContent).toBe('false')
  })

  it('role and email are null before login', () => {
    render(<WrappedApp><AuthDisplay /></WrappedApp>)
    expect(screen.getByTestId('role').textContent).toBe('null')
    expect(screen.getByTestId('email').textContent).toBe('null')
  })

  it('isAuthenticated becomes true after login', async () => {
    render(<WrappedApp><AuthDisplay /><AuthActions /></WrappedApp>)
    await act(async () => {
      screen.getByText('Login').click()
    })
    expect(screen.getByTestId('auth').textContent).toBe('true')
  })

  it('role is set after login', async () => {
    render(<WrappedApp><AuthDisplay /><AuthActions /></WrappedApp>)
    await act(async () => { screen.getByText('Login').click() })
    expect(screen.getByTestId('role').textContent).toBe('user')
  })

  it('email is set after login', async () => {
    render(<WrappedApp><AuthDisplay /><AuthActions /></WrappedApp>)
    await act(async () => { screen.getByText('Login').click() })
    expect(screen.getByTestId('email').textContent).toBe('test@example.com')
  })

  it('token is stored in sessionStorage after login', async () => {
    render(<WrappedApp><AuthActions /></WrappedApp>)
    await act(async () => { screen.getByText('Login').click() })
    expect(sessionStorage.getItem('token')).toBe('fake-token')
  })

  it('isAuthenticated becomes false after logout', async () => {
    render(<WrappedApp><AuthDisplay /><AuthActions /></WrappedApp>)
    await act(async () => { screen.getByText('Login').click() })
    await act(async () => { screen.getByText('Logout').click() })
    expect(screen.getByTestId('auth').textContent).toBe('false')
  })

  it('sessionStorage is cleared after logout', async () => {
    render(<WrappedApp><AuthActions /></WrappedApp>)
    await act(async () => { screen.getByText('Login').click() })
    await act(async () => { screen.getByText('Logout').click() })
    expect(sessionStorage.getItem('token')).toBeNull()
  })

  it('restores session from sessionStorage on mount', async () => {
    // Pre-populate sessionStorage as if a previous login occurred
    sessionStorage.setItem('token', 'existing-token')
    sessionStorage.setItem('role', 'admin')
    sessionStorage.setItem('email', 'admin@example.com')

    render(<WrappedApp><AuthDisplay /></WrappedApp>)
    expect(screen.getByTestId('auth').textContent).toBe('true')
    expect(screen.getByTestId('role').textContent).toBe('admin')
  })
})
