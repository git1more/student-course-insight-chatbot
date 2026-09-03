import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const toast = useToast()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('user@example.com')
  const [password, setPassword] = useState('password123')
  const [role, setRole] = useState('user')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const path = mode === 'login' ? '/auth/login' : '/auth/signup'
      const payload = mode === 'login' ? { email, password } : { email, password, role }
      const data = await apiRequest(path, { method: 'POST', body: JSON.stringify(payload) })
      const userRole = data.role || 'user'
      login({ token: data.access_token, role: userRole, email })
      navigate(userRole === 'admin' ? '/admin' : '/')
    } catch (err) {
      toast(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="center-wrap">
      <div className="card auth-card">
        <h2>{mode === 'login' ? 'Login' : 'Create Account'}</h2>
        <p className="muted">Demo users: user@example.com / password123, admin@example.com / password123</p>
        <form onSubmit={submit} className="form">
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {mode === 'signup' && (
            <label>
              Role
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </label>
          )}
          <button type="submit" disabled={loading}>{loading ? 'Loading...' : mode === 'login' ? 'Login' : 'Sign up'}</button>
        </form>
        <button className="link-btn" onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}>
          {mode === 'login' ? 'Need an account? Sign up' : 'Already have an account? Login'}
        </button>
      </div>
    </div>
  )
}
