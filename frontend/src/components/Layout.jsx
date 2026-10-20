import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Layout({ children }) {
  const { role, email, logout, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>Student Course Insight Chatbot</h1>
          <p className="muted">Final Demo — RAG + LLM (OpenAI-compatible)</p>
        </div>
        {isAuthenticated && (
          <div className="topbar-right">
            <span className="badge">{role}</span>
            <span className="muted">{email}</span>
            <button className="secondary" onClick={handleLogout}>Logout</button>
          </div>
        )}
      </header>

      {isAuthenticated && (
        <nav className="nav">
          <Link to="/">Query</Link>
          <Link to="/history">History</Link>
          {role === 'admin' && <Link to="/admin">Admin Analytics</Link>}
        </nav>
      )}

      <main className="container">{children}</main>
    </div>
  )
}
