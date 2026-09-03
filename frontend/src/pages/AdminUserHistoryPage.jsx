import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client'
import { useToast } from '../context/ToastContext'

export default function AdminUserHistoryPage() {
  const { userId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiRequest(`/admin/users/${userId}/history`)
      .then(setData)
      .catch((err) => toast(err.message))
      .finally(() => setLoading(false))
  }, [userId])

  return (
    <div className="stack">
      <div className="card">
        <button className="outline" style={{ width: 'fit-content', marginBottom: 12 }} onClick={() => navigate('/admin')}>
          ← Back to Admin
        </button>
        {loading && <p>Loading...</p>}
        {data && (
          <>
            <h2>Query History</h2>
            <p className="muted">
              User: <strong>{data.user.email}</strong> &nbsp;·&nbsp;
              Role: <span className={`badge ${data.user.role}`}>{data.user.role}</span>
            </p>
          </>
        )}
      </div>

      {data && (
        <div className="card">
          {data.logs.length === 0 ? (
            <p className="muted">This user has no query history yet.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Program</th>
                    <th>Year</th>
                    <th>Status</th>
                    <th>Results</th>
                    <th>Latency</th>
                    <th>Question</th>
                  </tr>
                </thead>
                <tbody>
                  {data.logs.map((log) => (
                    <tr key={log.id}>
                      <td>{new Date(log.created_at).toLocaleString()}</td>
                      <td>{log.course_code}</td>
                      <td>{log.term || '—'}</td>
                      <td>{log.status}</td>
                      <td>{log.result_count}</td>
                      <td>{log.duration_ms} ms</td>
                      <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {log.question}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
