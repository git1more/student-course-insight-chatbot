import { useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import { useToast } from '../context/ToastContext'
import InsightResult from '../components/InsightResult'

export default function HistoryPage() {
  const toast = useToast()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [viewing, setViewing] = useState(null) // { item } | null

  useEffect(() => {
    apiRequest('/history')
      .then(setHistory)
      .catch((err) => toast(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <div className="card">
        <h2>My Query History</h2>
        {loading && <p>Loading...</p>}
        {!loading && !history.length && <p className="muted">No history yet. Run a query first.</p>}
        {!!history.length && (
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
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id}>
                    <td>{new Date(item.created_at).toLocaleString()}</td>
                    <td>{item.course_code}</td>
                    <td>{item.term || '—'}</td>
                    <td>{item.status}</td>
                    <td>{item.result_count}</td>
                    <td>{item.duration_ms} ms</td>
                    <td style={{ maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.question}
                    </td>
                    <td>
                      <button
                        className="outline"
                        style={{ fontSize: 12, padding: '4px 12px', whiteSpace: 'nowrap' }}
                        disabled={!item.result}
                        title={item.result ? 'View saved output' : 'No saved output for this entry'}
                        onClick={() => setViewing(item)}
                      >
                        View Output
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {viewing && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setViewing(null)}>
          <div className="modal-box">
            <div className="modal-header">
              <div>
                <h3 style={{ margin: 0 }}>{viewing.course_code} {viewing.term ? `· ${viewing.term}` : ''}</h3>
                <p className="muted" style={{ margin: '4px 0 0', fontSize: 14 }}>{viewing.question}</p>
              </div>
              <button className="modal-close" onClick={() => setViewing(null)}>Close ✕</button>
            </div>
            <InsightResult result={viewing.result} />
          </div>
        </div>
      )}
    </>
  )
}
