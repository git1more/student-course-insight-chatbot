import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function AdminPage() {
  const [tab, setTab] = useState('analytics')

  return (
    <div className="stack">
      <div className="card">
        <h2>Admin Panel</h2>
        <div className="tab-bar">
          {['analytics', 'users', 'logs', 'ingest'].map((t) => (
            <button
              key={t}
              className={`tab-btn${tab === t ? ' active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {tab === 'analytics' && <AnalyticsTab />}
      {tab === 'users' && <UsersTab />}
      {tab === 'logs' && <LogsTab />}
      {tab === 'ingest' && <IngestTab />}
    </div>
  )
}

// ── Analytics ─────────────────────────────────────────────────────────────────

function AnalyticsTab() {
  const toast = useToast()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiRequest('/admin/analytics')
      .then(setData)
      .catch((err) => toast(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="card"><p>Loading...</p></div>
  if (!data) return null

  return (
    <>
      <div className="grid three">
        <div className="card stat"><span>Total Queries</span><strong>{data.total_queries}</strong></div>
        <div className="card stat"><span>OK Queries</span><strong>{data.ok_queries}</strong></div>
        <div className="card stat"><span>Blocked (Privacy)</span><strong>{data.blocked_queries}</strong></div>
        <div className="card stat"><span>Avg Latency</span><strong>{data.avg_duration_ms} ms</strong></div>
        <div className="card stat"><span>Programs Queried</span><strong>{data.most_queried_courses.length}</strong></div>
        <div className="card stat"><span>Status Types</span><strong>{data.status_breakdown.length}</strong></div>
      </div>
      <div className="grid two">
        <div className="card">
          <h3>Most Queried Programs</h3>
          <ul>
            {data.most_queried_courses.length
              ? data.most_queried_courses.map((item, i) => <li key={i}>{item.course_code}: {item.count}</li>)
              : <li className="muted">No data yet</li>}
          </ul>
        </div>
        <div className="card">
          <h3>Status Breakdown</h3>
          <ul>
            {data.status_breakdown.length
              ? data.status_breakdown.map((item, i) => <li key={i}>{item.status}: {item.count}</li>)
              : <li className="muted">No data yet</li>}
          </ul>
        </div>
      </div>
    </>
  )
}

// ── Users ─────────────────────────────────────────────────────────────────────

function UsersTab() {
  const navigate = useNavigate()
  const toast = useToast()
  const { userId: currentUserId } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(null)

  useEffect(() => {
    apiRequest('/admin/users')
      .then(setUsers)
      .catch((err) => toast(err.message))
      .finally(() => setLoading(false))
  }, [])

  const toggleRole = async (user) => {
    const newRole = user.role === 'admin' ? 'user' : 'admin'
    setUpdating(user.id)
    try {
      const updated = await apiRequest(`/admin/users/${user.id}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role: newRole }),
      })
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? { ...u, role: updated.role } : u)))
      toast(`Role updated to ${updated.role}`, 'success')
    } catch (err) {
      toast(err.message)
    } finally {
      setUpdating(null)
    }
  }

  const deleteUser = async (user) => {
    setUpdating(user.id)
    setConfirmDelete(null)
    try {
      await apiRequest(`/admin/users/${user.id}`, { method: 'DELETE' })
      setUsers((prev) => prev.filter((u) => u.id !== user.id))
      toast(`${user.email} deleted`, 'success')
    } catch (err) {
      toast(err.message)
    } finally {
      setUpdating(null)
    }
  }

  if (loading) return <div className="card"><p>Loading...</p></div>

  return (
    <>
      {confirmDelete && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div className="card" style={{ maxWidth: 420, width: '90%' }}>
            <h3 style={{ marginTop: 0 }}>Confirm Deletion</h3>
            <p>
              Are you sure you want to delete <strong>{confirmDelete.email}</strong>?
              This will permanently remove their account and all query history.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="secondary" onClick={() => setConfirmDelete(null)}>Cancel</button>
              <button className="danger" onClick={() => deleteUser(confirmDelete)}>Yes, delete</button>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h3>Registered Users <span className="muted">({users.length})</span></h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>ID</th><th>Email</th><th>Role</th><th>Joined</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td>{u.email}</td>
                  <td><span className={`badge ${u.role}`}>{u.role}</span></td>
                  <td>{new Date(u.created_at).toLocaleDateString()}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <button
                        className="outline"
                        style={{ fontSize: 13, padding: '4px 12px' }}
                        onClick={() => navigate(`/admin/users/${u.id}/history`)}
                      >
                        History
                      </button>
                      <button
                        className="secondary"
                        style={{ fontSize: 13, padding: '4px 12px' }}
                        disabled={updating === u.id || u.id === currentUserId}
                        title={u.id === currentUserId ? 'You cannot change your own role' : ''}
                        onClick={() => toggleRole(u)}
                      >
                        {updating === u.id ? '…' : `Make ${u.role === 'admin' ? 'user' : 'admin'}`}
                      </button>
                      <button
                        className="danger"
                        style={{ fontSize: 13, padding: '4px 12px' }}
                        disabled={updating === u.id}
                        onClick={() => setConfirmDelete(u)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}

// ── Query Logs ────────────────────────────────────────────────────────────────

function LogsTab() {
  const toast = useToast()
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiRequest('/admin/logs')
      .then(setLogs)
      .catch((err) => toast(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="card"><p>Loading...</p></div>

  return (
    <div className="card">
      <h3>All Query Logs <span className="muted">({logs.length} total)</span></h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Time</th><th>User</th><th>Program</th><th>Year</th><th>Status</th><th>Results</th><th>Latency</th><th>Question</th></tr>
          </thead>
          <tbody>
            {logs.length === 0
              ? <tr><td colSpan={8} className="muted">No queries yet</td></tr>
              : logs.map((log) => (
                <tr key={log.id}>
                  <td>{new Date(log.created_at).toLocaleString()}</td>
                  <td>{log.user_id}</td>
                  <td>{log.course_code}</td>
                  <td>{log.term || '—'}</td>
                  <td>{log.status}</td>
                  <td>{log.result_count}</td>
                  <td>{log.duration_ms} ms</td>
                  <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.question}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Ingest ────────────────────────────────────────────────────────────────────

function IngestTab() {
  const toast = useToast()
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  const runIngest = async () => {
    setLoading(true)
    setStatus(null)
    try {
      const data = await apiRequest('/admin/ingest', { method: 'POST' })
      setStatus(data.output || data.message)
      toast('Ingest completed successfully', 'success')
    } catch (err) {
      toast(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h3>Data Ingestion</h3>
      <p className="muted">
        Re-runs the ingestion pipeline from <code>CommentsData06032026a.xlsx</code>.
        This drops and recreates all feedback data and regenerates embeddings.
        <strong> This may take several minutes.</strong>
      </p>
      <button onClick={runIngest} disabled={loading}>
        {loading ? 'Running ingest…' : 'Trigger Ingest'}
      </button>
      {status && (
        <pre style={{ marginTop: 12, background: '#f5f5f5', padding: 12, borderRadius: 6, fontSize: 12, overflowX: 'auto', whiteSpace: 'pre-wrap' }}>
          {status}
        </pre>
      )}
    </div>
  )
}
