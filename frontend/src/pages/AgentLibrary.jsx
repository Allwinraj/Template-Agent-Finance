import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { StatusPill } from './Dashboard.jsx'
import './Dashboard.css'

const API = 'http://127.0.0.1:8000'

export default function AgentLibrary() {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')
  const [deletingId, setDeletingId] = useState(null)
  const navigate = useNavigate()

  const loadAgents = () => {
    setLoading(true)
    fetch(`${API}/registry/workflows`)
      .then((r) => r.json())
      .then((d) => setAgents(Array.isArray(d) ? d : []))
      .catch(() => setError('Could not reach the backend on port 8000.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadAgents()
  }, [])

  const handleDelete = async (workflowId, name) => {
    if (!window.confirm(`Delete "${name}"? This action cannot be undone.`)) {
      return
    }
    setDeletingId(workflowId)
    try {
      const res = await fetch(`${API}/registry/workflows/${workflowId}`, { method: 'DELETE' })
      if (res.ok) {
        setAgents((prev) => prev.filter((a) => a.workflow_id !== workflowId))
      } else {
        alert('Could not delete agent. Backend returned an error.')
      }
    } catch {
      alert('Could not delete agent. Unable to connect to backend.')
    } finally {
      setDeletingId(null)
    }
  }

  const shown = filter === 'all' ? agents : agents.filter((a) => a.status === filter)

  return (
    <div className="page anim-fade-up">
      <header className="page-head">
        <div>
          <h1>Agent Library</h1>
          <p>Every super agent you've created. Open one to chat or delete tested agents.</p>
        </div>
        <div className="lib-filters">
          {['all', 'draft', 'published'].map((f) => (
            <button key={f} className={`chip-btn ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>{f}</button>
          ))}
        </div>
      </header>

      {loading && <p className="wiz-hint">Loading agents…</p>}
      {error && <p className="wiz-error">{error}</p>}
      {!loading && !shown.length && (
        <div className="lux-card lib-empty">
          <strong>No agents yet</strong>
          <p className="wiz-hint">Create your first agent from the Create Agent tab — it will appear here.</p>
          <button className="btn btn-gold" onClick={() => navigate('/app/create-agent')}>✦ Create Agent</button>
        </div>
      )}

      <div className="lib-grid">
        {shown.map((a) => (
          <div key={a.workflow_id} className="lux-card lib-card anim-fade-up">
            <div className="lib-card-head">
              <span className="lib-icon">✦</span>
              <div className="lib-title">
                <strong>{a.name}</strong>
                <span className="lib-id">{a.workflow_id} · v{a.version}</span>
              </div>
              <StatusPill status={a.status} />
              <button
                className="lib-delete"
                title="Delete this agent"
                disabled={deletingId === a.workflow_id}
                onClick={(e) => {
                  e.stopPropagation()
                  handleDelete(a.workflow_id, a.name)
                }}
              >
                {deletingId === a.workflow_id ? '…' : '🗑'}
              </button>
            </div>
            <p className="lib-desc">{a.description || 'No description'}</p>
            <div className="lib-meta">
              <span>{a.config?.agents?.length || 0} agents: {(a.config?.agents || []).join(', ') || '—'}</span>
              <span>{(a.created_at || '').slice(0, 10)}</span>
            </div>
            <button className="btn btn-gold lib-open" onClick={() => navigate(`/app/agent-chat/${a.workflow_id}`)}>
              💬 Open chat
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

