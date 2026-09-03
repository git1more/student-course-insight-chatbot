import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiRequest } from '../api/client'
import { useToast } from '../context/ToastContext'
import InsightResult from '../components/InsightResult'

export default function QueryPage() {
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const autoRan = useRef(false)

  const [program, setProgram] = useState('')
  const [year, setYear] = useState('')
  const [question, setQuestion] = useState('What are the main issues students mention?')

  const [programs, setPrograms] = useState([])
  const [years, setYears] = useState([])

  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const fetchFilters = async () => {
      try {
        const [programData, yearData] = await Promise.all([
          apiRequest('/insights/programs'),
          apiRequest('/insights/years'),
        ])
        const progs = programData.programs || []
        const yrs = yearData.years || []
        setPrograms(progs)
        setYears(yrs)

        // Check for re-run params from history page
        const paramProgram = searchParams.get('program')
        const paramYear = searchParams.get('year')
        const paramQuestion = searchParams.get('question')

        if (paramProgram) {
          setProgram(paramProgram)
          setYear(paramYear || '')
          setQuestion(paramQuestion || '')
          setSearchParams({}, { replace: true }) // clean URL
          if (!autoRan.current) {
            autoRan.current = true
            // slight delay so state updates settle
            setTimeout(() => submitQueryWith(paramProgram, paramYear || '', paramQuestion || ''), 100)
          }
        } else {
          if (progs.length > 0) setProgram(progs[0])
          if (yrs.length > 0) setYear(yrs[yrs.length - 1])
        }
      } catch (err) {
        toast(err.message)
      }
    }
    fetchFilters()
  }, [])

  const submitQueryWith = async (prog, yr, q) => {
    setLoading(true)
    setResult(null)
    try {
      const data = await apiRequest('/query', {
        method: 'POST',
        body: JSON.stringify({ question: q, program: prog, year: yr || null }),
      })
      setResult(data)
    } catch (err) {
      toast(err.message)
    } finally {
      setLoading(false)
    }
  }

  const submitQuery = (q) => submitQueryWith(program, year, q)

  const handleSubmit = (e) => {
    e.preventDefault()
    submitQuery(question)
  }

  const handleFollowUp = (q) => {
    setQuestion(q)
    submitQuery(q)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="stack">
      <div className="card">
        <h2>Program Insight Query</h2>
        <p className="muted">
          Ask a natural-language question about student feedback and receive a structured,
          evidence-grounded summary powered by semantic search + GPT-4o-mini.
        </p>

        <form className="form" onSubmit={handleSubmit}>
          <div className="grid two">
            <label>
              Program
              <select value={program} onChange={(e) => setProgram(e.target.value)}>
                {programs.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </label>

            <label>
              Year
              <select value={year} onChange={(e) => setYear(e.target.value)}>
                <option value="">All years</option>
                {years.map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </label>
          </div>

          <label>
            Question
            <textarea
              rows="3"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. What are the main issues students mention?"
            />
          </label>

          <button type="submit" disabled={loading || !program}>
            {loading ? 'Generating insight…' : 'Generate Insight'}
          </button>
        </form>
      </div>

      {loading && (
        <div className="card">
          <div className="loading-overlay">
            <div className="spinner" />
            <p>Searching {result ? 'again' : 'comments'} and generating structured response via GPT-4o-mini…</p>
          </div>
        </div>
      )}

      {!loading && (
        <InsightResult result={result} onFollowUp={handleFollowUp} />
      )}
    </div>
  )
}
