import { Routes, Route, NavLink, Link, useNavigate, useLocation } from 'react-router-dom'

import {
  KPIS, DONUT_SEGMENTS, ACTIVITY,
} from '../data/mockData.js'
import CreateAgent from './CreateAgent.jsx'
import AgentLibrary from './AgentLibrary.jsx'
import AgentChat from './AgentChat.jsx'
import Users from './Users.jsx'
import Settings from './Settings.jsx'
import { NexusMark } from './Landing.jsx'
import './Dashboard.css'

/* ---------- Shared bits ---------- */

export function StatusPill({ status }) {
  const map = {
    healthy: 'ok', active: 'ok', ok: 'ok', published: 'ok', completed: 'ok',
    degraded: 'warn', invited: 'warn', pending: 'warn',
    failed: 'err', error: 'err',
  }
  return (
    <span className={`pill pill-${map[status] || 'dim'}`}>
      <span className={`status-dot ${map[status] || 'warn'}`} />
      {String(status).replace(/_/g, ' ')}
    </span>
  )
}

/* ---------- Donut chart (SVG) ---------- */
function Donut({ segments, size = 190 }) {
  const total = segments.reduce((s, x) => s + x.value, 0)
  const r = 70
  const c = 2 * Math.PI * r
  let offset = 0

  return (
    <div className="donut-wrap">
      <svg width={size} height={size} viewBox="0 0 190 190">
        <circle cx="95" cy="95" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="20" />
        {segments.map((seg) => {
          const len = (seg.value / total) * c
          const el = (
            <circle
              key={seg.label}
              cx="95" cy="95" r={r}
              fill="none"
              stroke={seg.color}
              strokeWidth="18"
              strokeLinecap="round"
              strokeDasharray={`${len} ${c - len}`}
              strokeDashoffset={-offset}
              transform="rotate(-90 95 95)"
              className="donut-seg"
            />
          )
          offset += len
          return el
        })}
        <text x="95" y="90" textAnchor="middle" className="donut-num">92%</text>
        <text x="95" y="112" textAnchor="middle" className="donut-sub">auto-matched</text>
      </svg>
      <div className="donut-legend">
        {segments.map((s) => (
          <div key={s.label} className="donut-legend-item">
            <span className="donut-swatch" style={{ background: s.color }} />
            <span>{s.label}</span>
            <strong>{s.value}%</strong>
          </div>
        ))}
      </div>
    </div>
  )
}


/* ---------- Overview (Welcome Dashboard) ---------- */
const SUPER_AGENTS = [
  { name: 'Budget vs Actual', status: 'published', runs: 48, lastRun: '10 min ago', category: 'FP&A', icon: '📊' },
  { name: 'Bank Reconciliation', status: 'published', runs: 31, lastRun: '25 min ago', category: 'R2R', icon: '🏦' },
  { name: 'Invoice Processing', status: 'published', runs: 22, lastRun: '1 hr ago', category: 'P2P', icon: '🧾' },
  { name: 'Intercompany Recon', status: 'draft', runs: 0, lastRun: 'Never', category: 'R2R', icon: '🔄' },
  { name: 'Cash Flow Forecast', status: 'published', runs: 9, lastRun: '3 hrs ago', category: 'Treasury', icon: '💰' },
  { name: 'Vendor Dedup Check', status: 'draft', runs: 0, lastRun: 'Never', category: 'P2P', icon: '🔍' },
]

function Overview({ user }) {
  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Welcome back, {user.name.split(' ')[0]} 👋</h1>
          <p>Here's your super agent workspace at a glance.</p>
        </div>
        <span className="chip"><span className="status-dot ok" /> All systems operational</span>
      </header>

      {/* KPI row */}
      <div className="kpi-grid">
        {KPIS.map((k, i) => (
          <div key={k.id} className={`lux-card kpi anim-fade-up anim-delay-${i + 1}`}>
            <div className="kpi-top">
              <span className="kpi-icon">{k.icon}</span>
              <span className={`kpi-delta ${k.up ? 'up' : 'down'}`}>{k.delta}</span>
            </div>
            <strong className="kpi-value">{k.value}</strong>
            <span className="kpi-label">{k.label}</span>
          </div>
        ))}
      </div>

      {/* Super Agents list */}
      <div className="lux-card panel anim-fade-up anim-delay-2">
        <div className="panel-head">
          <h3>🤖 Super Agents</h3>
          <span className="chip">use-case agents</span>
        </div>
        <div className="super-agent-list">
          {SUPER_AGENTS.map((a) => (
            <div key={a.name} className="super-agent-row">
              <span className="sa-icon">{a.icon}</span>
              <div className="sa-meta">
                <strong>{a.name}</strong>
                <span className="sa-cat">{a.category}</span>
              </div>
              <div className="sa-runs">
                <span className="sa-run-count">{a.runs}</span>
                <span className="sa-run-label">runs</span>
              </div>
              <span className="sa-last">{a.lastRun}</span>
              <StatusPill status={a.status} />
            </div>
          ))}
        </div>
      </div>

      <div className="panel-grid">
        <div className="lux-card panel anim-fade-up anim-delay-2">
          <div className="panel-head">
            <h3>Agent Status Breakdown</h3>
            <span className="chip">this month</span>
          </div>
          <Donut segments={DONUT_SEGMENTS} />
        </div>

        <div className="lux-card panel anim-fade-up anim-delay-3">
          <div className="panel-head">
            <h3>Recent activity</h3>
            <span className="chip">today</span>
          </div>
          <div className="feed">
            {ACTIVITY.map((a, i) => (
              <div key={i} className="act-row">
                <span className={`act-icon ${a.tone}`}>{a.icon}</span>
                <span className="act-text">{a.text}</span>
                <span className="act-time">{a.at}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ---------- Shell ---------- */
export default function Dashboard({ user, onSignOut }) {
  const navigate = useNavigate()
  const location = useLocation()
  const isChat = location.pathname.includes('/agent-chat')

  const nav = [
    { to: '/app', label: 'Overview', icon: '◈', end: true },
    { to: '/app/create-agent', label: 'Create Agent', icon: '✦' },
    { to: '/app/agent-library', label: 'Agent Library', icon: '📚' },
    { to: '/app/users', label: 'Users', icon: '👥' },
    { to: '/app/settings', label: 'Settings', icon: '⚙' },
  ]

  return (
    <div className="dash">
      <aside className="sidebar">
        <Link to="/" className="brand dash-brand">
          <NexusMark size={28} />
          <span>NEXUS <small>2.0</small></span>
        </Link>

        <nav className="dash-nav">
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => `dash-link ${isActive ? 'active' : ''}`}>
              <span className="dash-icon">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="dash-user">
          <div className="dash-avatar">{user.name.split(' ').map((p) => p[0]).join('')}</div>
          <div>
            <strong>{user.name}</strong>
            <span>{user.role}</span>
          </div>
          <button className="dash-logout" title="Sign out" onClick={() => { onSignOut(); navigate('/') }}>
            ⏻
          </button>
        </div>
      </aside>

      <main className={`dash-main ${isChat ? 'dash-main-chat' : ''}`}>
        <Routes>
          <Route index element={<Overview user={user} />} />
          <Route path="create-agent" element={<CreateAgent />} />
          <Route path="agent-library" element={<AgentLibrary />} />
          <Route path="agent-chat/:workflowId" element={<AgentChat />} />
          <Route path="users" element={<Users />} />
          <Route path="settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}