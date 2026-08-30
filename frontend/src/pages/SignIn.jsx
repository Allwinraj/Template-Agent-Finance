import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { NexusMark } from './Landing.jsx'
import './SignIn.css'

/* Hardcoded demo credentials — replace with real auth API later */
const DEMO_USERS = [
  { email: 'admin@nexus.io', password: 'admin123', name: 'Elena Vance', role: 'Finance Admin' },
  { email: 'reviewer@nexus.io', password: 'review123', name: 'Marcus Chen', role: 'Finance Reviewer' },
]

export default function SignIn({ onSignIn }) {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')

    const found = DEMO_USERS.find(
      (u) => u.email === email.trim().toLowerCase() && u.password === password
    )

    if (!found) {
      setError('Invalid credentials. Try a demo account below.')
      return
    }

    setLoading(true)
    // Simulated backend latency — replace with real API call
    setTimeout(() => {
      onSignIn({ name: found.name, email: found.email, role: found.role })
      navigate('/app')
    }, 900)
  }

  const fillDemo = (u) => {
    setEmail(u.email)
    setPassword(u.password)
    setError('')
  }

  return (
    <div className="signin">
      <div className="si-orb si-orb-1" />
      <div className="si-orb si-orb-2" />
      <div className="si-grid" />

      <div className="si-panel">
        {/* ---------- Left: brand story ---------- */}
        <div className="si-left">
          <Link to="/" className="si-brand anim-fade-in">
            <NexusMark size={30} />
            <span>NEXUS <small>2.0</small></span>
          </Link>

          <div className="si-story">
            <h1 className="anim-fade-up">
              Finance that<br /><em className="grad-text">runs itself.</em>
            </h1>
            <p className="anim-fade-up anim-delay-1">
              Six agents. One orchestrator. Every decision audited.
            </p>

            <ul className="si-points">
              {[
                ['📥', 'Reads bank files, SAP exports, Excel and PDFs'],
                ['🔗', 'Matches everything automatically — with evidence'],
                ['🧭', 'Sends anything unusual to a human for review'],
              ].map(([icon, text], i) => (
                <li key={text} className="anim-fade-up" style={{ animationDelay: `${0.25 + i * 0.15}s` }}>
                  <span className="si-point-icon">{icon}</span>
                  {text}
                </li>
              ))}
            </ul>

            <div className="si-live anim-fade-up anim-delay-4">
              <div className="si-live-item">
                <span className="status-dot ok" />
                <span>Orchestrator</span>
                <strong>running</strong>
              </div>
              <div className="si-live-item">
                <span className="status-dot ok" />
                <span>Rule Engine</span>
                <strong>v2.4</strong>
              </div>
              <div className="si-live-item">
                <span className="status-dot warn" />
                <span>Review queue</span>
                <strong>3 open</strong>
              </div>
            </div>
          </div>

          <p className="si-quote anim-fade-in anim-delay-5">
            "You describe the job. The agents do it. Every decision is audited."
          </p>
        </div>

        {/* ---------- Right: form ---------- */}
        <div className="si-right">
          <div className="si-card anim-scale-in">
            <h2>Welcome back</h2>
            <p className="si-sub">Sign in to your Nexus workspace</p>

            <form onSubmit={handleSubmit} noValidate>
              <div className="si-field">
                <label className="si-label" htmlFor="si-email">Email address</label>
                <input
                  id="si-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  autoComplete="email"
                  autoFocus
                />
              </div>

              <div className="si-field">
                <div className="si-label-row">
                  <label className="si-label" htmlFor="si-password">Password</label>
                  <button type="button" className="si-eye" onClick={() => setShowPw(!showPw)} tabIndex={-1}>
                    {showPw ? 'Hide' : 'Show'}
                  </button>
                </div>
                <input
                  id="si-password"
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                />
              </div>

              {error && (
                <div className="si-error anim-fade-up">
                  <span>⚠</span> {error}
                </div>
              )}

              <button type="submit" className={`btn btn-gold si-submit ${loading ? 'loading' : ''}`} disabled={loading}>
                {loading ? (
                  <>
                    <span className="si-spinner" /> Signing you in…
                  </>
                ) : (
                  <>
                    Sign In
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                      <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </>
                )}
              </button>
            </form>

            <div className="si-divider"><span>demo accounts — click to fill</span></div>

            <div className="si-demo">
              {DEMO_USERS.map((u) => (
                <button key={u.email} type="button" className="si-demo-btn" onClick={() => fillDemo(u)}>
                  <span className="si-demo-role">{u.role}</span>
                  <span className="si-demo-mail">{u.email}</span>
                  <span className="si-demo-fill">Use →</span>
                </button>
              ))}
            </div>

            <p className="si-fine">
              Protected workspace · All access is recorded in the audit trail
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}