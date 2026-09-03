const VOLUME_COLOR = { High: '#15803d', Medium: '#a16207', Low: '#6b7280' }
const EFFORT_COLOR  = { Low: '#15803d', Medium: '#a16207', High: '#b91c1c' }
const IMPACT_COLOR  = { Low: '#6b7280', Medium: '#a16207', High: '#15803d' }
const RECENCY_LABEL = { Recent: '↑ Recent', Stable: '→ Stable', Declining: '↓ Declining' }

export default function InsightResult({ result, onFollowUp }) {
  if (!result) return null

  if (result.blocked_by_privacy) {
    return (
      <div className="card warning">
        <h3>Privacy Protection Triggered</h3>
        <p>{result.message}</p>
        <ConfidencePanel typicality={result.typicality || {}} />
      </div>
    )
  }

  const t = result.typicality || {}

  return (
    <div className="stack">

      {/* Part 1 — Executive Summary */}
      <div className="card">
        <div className="section-label">Part 1 · Executive Summary</div>
        <p style={{ margin: '8px 0 0', lineHeight: 1.7 }}>{result.executive_summary}</p>
        {t.contradiction_detected && (
          <div className="contradiction-banner" style={{ marginTop: 12 }}>
            ⚠ Mixed feedback detected — conflicting views exist on at least one issue.
          </div>
        )}
      </div>

      {/* Part 2 — Ranked Themes */}
      <div className="card section-watchout">
        <div className="section-label">Part 2 · Ranked Themes / Issues</div>
        <p className="muted" style={{ fontSize: 12, marginTop: 4, marginBottom: 12 }}>
          Ordered by volume of student mentions. Recency reflects whether the theme appears in the most recent data.
        </p>
        <div className="theme-list">
          {(result.ranked_themes || []).map((t, i) => (
            <div key={i} className="theme-row">
              <span className="theme-rank">#{i + 1}</span>
              <span className="theme-name">{t.theme}</span>
              <span className="theme-badge" style={{ color: VOLUME_COLOR[t.volume] || '#6b7280' }}>
                ● {t.volume} volume
              </span>
              <span className="theme-badge muted">{RECENCY_LABEL[t.recency] || t.recency}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Part 3 — Evidence Excerpts */}
      <div className="card section-evidence">
        <div className="section-label">Part 3 · Evidence Excerpts</div>
        <p className="muted" style={{ fontSize: 12, marginTop: 4, marginBottom: 12 }}>
          Top {(result.supporting_evidence || []).length} comments retrieved from {t.sample_size} total
          via semantic similarity search. Source: anonymised "Needs Improvement" survey responses.
        </p>
        <div className="evidence-list">
          {(result.supporting_evidence || []).map((item) => (
            <div key={item.comment_id} className="evidence-item">
              <span className="badge small">#{item.comment_id}</span>
              <p style={{ margin: '6px 0 0', fontSize: 14, lineHeight: 1.6 }}>{item.excerpt}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Part 4 — Interpretation */}
      <div className="card section-tips">
        <div className="section-label">Part 4 · Interpretation</div>
        <p style={{ margin: '8px 0 0', lineHeight: 1.7 }}>{result.interpretation}</p>
      </div>

      {/* Part 5 — Recommended Actions */}
      <div className="card section-positive">
        <div className="section-label">Part 5 · Recommended Actions</div>
        <p className="muted" style={{ fontSize: 12, marginTop: 4, marginBottom: 12 }}>
          Effort and impact are estimated relative to typical course administration capacity.
        </p>
        <div className="action-list">
          {(result.recommended_actions || []).map((a, i) => (
            <div key={i} className="action-row">
              <div className="action-text">{a.action}</div>
              <div className="action-meta">
                <span className="action-chip">👤 {a.owner}</span>
                <span className="action-chip" style={{ color: EFFORT_COLOR[a.effort] }}>
                  Effort: {a.effort}
                </span>
                <span className="action-chip" style={{ color: IMPACT_COLOR[a.impact] }}>
                  Impact: {a.impact}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Part 6 — Confidence + Caveats */}
      <div className="card">
        <div className="section-label">Part 6 · Confidence &amp; Caveats</div>
        <div style={{ marginTop: 8 }}>
          <ConfidencePanel typicality={t} />
        </div>
      </div>

      {/* Follow-up Questions */}
      {(result.follow_up_questions || []).length > 0 && (
        <div className="card">
          <h3>Suggested Follow-up Questions</h3>
          <div className="follow-up-list">
            {result.follow_up_questions.map((q, i) => (
              <button key={i} className="follow-up-btn" onClick={() => onFollowUp && onFollowUp(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}

function ConfidencePanel({ typicality }) {
  const confidence = (typicality.confidence || 'Low').toLowerCase()
  return (
    <div className="typicality-panel">
      <div className="tp-item">
        <span className="tp-label">Sample Size</span>
        <span className="tp-value">n = {typicality.sample_size ?? '—'}</span>
      </div>
      <div className="tp-item">
        <span className="tp-label">Timeframe</span>
        <span className="tp-value">{typicality.timeframe ?? '—'}</span>
      </div>
      <div className="tp-item">
        <span className="tp-label">Confidence</span>
        <span className={`tp-value ${confidence}`}>{typicality.confidence ?? 'Low'}</span>
      </div>
      {typicality.limitations && (
        <div className="tp-item" style={{ flex: '1 1 100%' }}>
          <span className="tp-label">Limitations</span>
          <span className="tp-value" style={{ fontSize: 13, fontWeight: 400 }}>{typicality.limitations}</span>
        </div>
      )}
    </div>
  )
}
