import { createContext, useContext, useMemo, useState } from 'react'

const AuthContext = createContext(null)

function parseUserId(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return parseInt(payload.sub, 10)
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(sessionStorage.getItem('token'))
  const [role, setRole] = useState(sessionStorage.getItem('role'))
  const [email, setEmail] = useState(sessionStorage.getItem('email'))

  const login = ({ token, role, email }) => {
    sessionStorage.setItem('token', token)
    sessionStorage.setItem('role', role)
    sessionStorage.setItem('email', email)
    setToken(token)
    setRole(role)
    setEmail(email)
  }

  const logout = () => {
    sessionStorage.removeItem('token')
    sessionStorage.removeItem('role')
    sessionStorage.removeItem('email')
    setToken(null)
    setRole(null)
    setEmail(null)
  }

  const userId = token ? parseUserId(token) : null
  const value = useMemo(
    () => ({ token, role, email, userId, login, logout, isAuthenticated: !!token }),
    [token, role, email, userId]
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
