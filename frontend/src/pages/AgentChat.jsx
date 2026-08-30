import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { NexusMark } from './Landing.jsx'
import './AgentChat.css'


const API = 'http://127.0.0.1:8000'

const fmt = (n) =>
  n == null || n === '' ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const STATUS_META = {
  on_track: {
    label: 'On track',
    tone: 'ok',
    hint: 'Within acceptable variance — no action needed',
  },
  matched: {
    label: 'On track',
    tone: 'ok',
    hint: 'Within acceptable variance — no action needed',
  },
  notable: {
    label: 'Notable',
    tone: 'warn',
    hint: 'Moderate variance — worth a glance, not urgent',
  },
  review: {
    label: 'Needs review',
    tone: 'warn',
    hint: 'Large variance or soft rule failed — finance should review',
  },
  requires_review: {
    label: 'Needs review',
    tone: 'warn',
    hint: 'Large variance or soft rule failed — finance should review',
  },
  exception: {
    label: 'Exception',
    tone: 'err',
    hint: 'Hard rule fired (material amount, zero-budget, missing pair) — action required',
  },
}

function StatusBadge({ row }) {
  const raw = row.status || (row.actions?.length ? 'exception' : 'on_track')
  const meta = STATUS_META[raw] || { label: String(raw).replace(/_/g, ' '), tone: 'dim', hint: '' }
  return (
    <span className={`chat-badge ${meta.tone}`} title={meta.hint}>
      {meta.label}
    </span>
  )
}

function VarianceTable({ rows }) {
  const flagged = (r) => ['review', 'exception', 'requires_review', 'notable'].includes(r.status) || (r.actions || []).length > 0
  return (
    <div className="chat-table-wrap">
      <table className="chat-table">
        <thead>
          <tr>
            <th>GL Account</th>
            <th>Cost Center</th>
            <th>Period</th>
            <th className="num">Actual</th>
            <th className="num">Budget</th>
            <th className="num">Variance</th>
            <th className="num">Var %</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={flagged(r) ? 'row-flagged' : ''}>
              <td>{r.gl_account}</td>
              <td>{r.cost_center}</td>
              <td>{r.fiscal_period}</td>
              <td className="num">{fmt(r.actual)}</td>
              <td className="num">{fmt(r.budget)}</td>
              <td className={`num ${Number(r.calc_results?.variance) > 0 ? 'pos' : Number(r.calc_results?.variance) < 0 ? 'neg' : ''}`}>
                {fmt(r.calc_results?.variance ?? r.variance)}
              </td>
              <td className="num">
                {(r.calc_results?.variance_percentage ?? r.variance_pct) == null
                  ? '—'
                  : `${r.calc_results?.variance_percentage ?? r.variance_pct}%`}
              </td>
              <td><StatusBadge row={r} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function GenericTable({ columns, rows }) {
  if (!columns?.length) return null
  return (
    <div className="chat-table-wrap">
      <table className="chat-table">
        <thead>
          <tr>{columns.map((c) => <th key={c}>{String(c).replace(/_/g, ' ')}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {columns.map((c) => {
                const v = r[c]
                const num = typeof v === 'number'
                return <td key={c} className={num ? 'num' : ''}>{num ? fmt(v) : (v == null || v === '' ? '—' : String(v))}</td>
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function OutputsRenderer({ outputs }) {
  if (!outputs?.length) return null
  return (
    <div className="chat-outputs">
      {outputs.map((o) => (
        <div key={o.id || o.title} className="chat-output-block">
          <div className="chat-output-title">{o.title}</div>
          {o.description && <p className="chat-output-desc">{o.description}</p>}
          {o.render === 'kpi' && o.data && (
            <div className="chat-kpis">
              {Object.entries(o.data)
                .filter(([, v]) => typeof v === 'number' || typeof v === 'string')
                .slice(0, 6)
                .map(([k, v]) => (
                  <div key={k} className="chat-kpi dim">
                    <strong>{typeof v === 'number' ? fmt(v) : String(v)}</strong>
                    <span>{String(k).replace(/_/g, ' ')}</span>
                  </div>
                ))}
            </div>
          )}
          {o.render === 'table' && (o.rows?.length ? <GenericTable columns={o.columns} rows={o.rows} /> : <p className="chat-exec-empty">No rows to show.</p>)}
          {o.render === 'exceptions' && (o.rows?.length ? <GenericTable columns={o.columns} rows={o.rows} /> : <p className="chat-exec-empty">No exceptions — all rows passed.</p>)}
          {o.render === 'narrative' && o.text && <p>{o.text}</p>}
        </div>
      ))}
    </div>
  )
}

function SummaryCards({ summary, executive }) {
  if (!summary && !executive) return null
  const exec = executive || {}
  const bd = exec.status_breakdown || summary?.status_breakdown || {}
  const needs =
    exec.needs_attention ??
    summary?.needs_attention ??
    ((bd.review || 0) + (bd.exception || 0) + (bd.notable || 0))
  const cards = [
    { label: 'Compared', value: exec.total_compared ?? summary?.compared ?? 0, tone: 'dim' },
    { label: 'On track', value: bd.on_track ?? bd.matched ?? summary?.on_track ?? summary?.matched ?? 0, tone: 'ok' },
    { label: 'Notable', value: bd.notable ?? summary?.notable ?? 0, tone: 'warn' },
    { label: 'Need review', value: (bd.review || 0) + (bd.exception || 0) || summary?.requires_review || 0, tone: needs ? 'err' : 'ok' },
    { label: 'Total variance', value: fmt(exec.total_variance ?? summary?.total_variance), tone: 'dim' },
  ]
  return (
    <div className="chat-kpis">
      {cards.map((c) => (
        <div key={c.label} className={`chat-kpi ${c.tone}`}>
          <strong>{c.value ?? 0}</strong>
          <span>{c.label}</span>
        </div>
      ))}
    </div>
  )
}

function Legend({ executive }) {
  const legend = executive?.legend || {
    on_track: 'Variance within acceptable band (default |var%| < 5%) — no action needed',
    notable: 'Moderate variance (default 5–10%) — worth a glance, not urgent',
    review: 'Large variance (default |var%| ≥ 10%) or a soft rule failed — finance should review',
    exception: 'Hard rule fired (material amount, zero-budget spend, missing pair) — action required',
  }
  const thr = executive?.thresholds || {}
  return (
    <div className="chat-legend">
      <div className="chat-legend-title">How to read Status</div>
      <ul>
        {Object.entries(legend).map(([k, v]) => (
          <li key={k}>
            <StatusBadge row={{ status: k }} /> <span>{v}</span>
          </li>
        ))}
      </ul>
      {(thr.on_track_pct != null || thr.review_pct != null) && (
        <p className="chat-legend-thr">
          Thresholds used: on-track &lt; {thr.on_track_pct ?? 5}% · review ≥ {thr.review_pct ?? 10}%
          {thr.materiality ? ` · materiality ${fmt(thr.materiality)}` : ''}
        </p>
      )}
    </div>
  )
}

function ExecutiveSummary({ exec }) {
  if (!exec) return null
  const rows = exec.top_attention || []
  const bd = exec.status_breakdown || {}
  return (
    <div className="chat-exec">
      <div className="chat-exec-head">
        <strong>What needs attention</strong>
        <span className="chat-exec-total">
          {Object.entries(bd).map(([k, v]) => (
            <span key={k} className={`chat-tier tier-${k}`}>{STATUS_META[k]?.label || k} · {v}</span>
          ))}
        </span>
      </div>
      {rows.length === 0 ? (
        <p className="chat-exec-empty">All compared rows are on track — nothing flagged for review.</p>
      ) : (
        <table className="chat-table chat-exec-table">
          <thead>
            <tr>
              <th>GL Account</th>
              <th>Cost Center</th>
              <th>Period</th>
              <th className="num">Variance</th>
              <th className="num">Var %</th>
              <th>Status</th>
              <th>Why</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.gl_account}</td>
                <td>{r.cost_center}</td>
                <td>{r.fiscal_period}</td>
                <td className="num">{fmt(r.variance)}</td>
                <td className="num">{r.variance_pct == null ? '—' : `${r.variance_pct}%`}</td>
                <td><StatusBadge row={r} /></td>
                <td className="chat-why">{r.reason || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default function AgentChat() {
  const { workflowId } = useParams()
  const navigate = useNavigate()
  const [workflow, setWorkflow] = useState(null)
  const [messages, setMessages] = useState([])
  const [files, setFiles] = useState([])
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef(null)
  const fileRef = useRef(null)

  useEffect(() => {
    fetch(`${API}/registry/workflows/${workflowId}`)
      .then((r) => r.json())
      .then((w) => {
        setWorkflow(w)
        setMessages([
          {
            role: 'agent',
            kind: 'markdown',
            text: `### Ready to run **${w.name || workflowId}**\nAttach new Excel or CSV files below (optional) and press **▶ Run** to execute the pipeline with saved mappings, calculations, and rules.`,
          },
        ])
      })
      .catch(() => setMessages([{ role: 'agent', kind: 'markdown', text: '⚠️ **Could not load workflow metadata.** Please ensure the backend is running.' }]))
  }, [workflowId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  const push = (m) => setMessages((prev) => [...prev, m])

  async function run() {
    if (busy) return
    setBusy(true)
    push({
      role: 'user',
      kind: 'markdown',
      text: files.length
        ? `Run pipeline with attached files: **${files.map((f) => f.name).join(', ')}**`
        : 'Run pipeline with configured sample data',
    })

    try {
      // optional: upload files first so backend has them under uploads/
      const fileMap = {}
      if (files.length) {
        const fd = new FormData()
        files.forEach((f) => fd.append('files', f))
        // profile endpoint also stores uploads; keep simple role=filename map
        const prof = await fetch(`${API}/llm/profile-data`, { method: 'POST', body: fd }).then((r) => r.json())
        ;(prof.profiles || []).forEach((p) => {
          if (p.role && p.file) fileMap[p.role] = p.file
        })
      }

      const res = await fetch(`${API}/workflows/${workflowId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: fileMap }),
      })
      const runData = await res.json()

      if (!res.ok || runData.error || runData.detail || runData.state === 'failed') {
        push({ role: 'agent', kind: 'markdown', text: `⚠️ **Run failed:** ${runData.error || runData.detail || `HTTP ${res.status}`}` })
      } else {
        push({
          role: 'agent',
          kind: 'markdown',
          text: `✅ **Run completed** (\`${runData.run_id}\`)\nPipeline executed: **${(runData.steps || []).map((s) => s.agent_id).join(' → ')}**`,
        })

        const warnings = (runData.steps || []).flatMap((s) => s.output_summary?.warnings || [])
        warnings.forEach((w) => push({ role: 'agent', kind: 'markdown', text: `⚠️ ${w}` }))

        // full payload has compared_rows + executive
        const full = await fetch(`${API}/workflows/runs/${runData.run_id}`).then((r) => r.json())
        const result = full?.result || runData.result || {}
        const summary = result.summary || {}
        const executive = result.executive || result.report?.executive_summary || null
        const compared = result.compared_rows || result.report?.tables?.compared || []

        push({ role: 'agent', kind: 'summary', summary, executive })
        push({ role: 'agent', kind: 'legend', executive })
        if (executive) push({ role: 'agent', kind: 'exec', executive })
        // render the user-requested outputs (from the design's output_spec)
        if (result.report?.outputs?.length) {
          push({ role: 'agent', kind: 'outputs', outputs: result.report.outputs })
        } else if (compared.length) {
          push({ role: 'agent', kind: 'table', rows: compared })
        }
        if (result.report?.narrative) {
          push({ role: 'agent', kind: 'markdown', text: result.report.narrative })
        }
      }
    } catch (e) {
      push({ role: 'agent', kind: 'markdown', text: '⚠️ **Could not reach the backend.** Is it running on port 8000?' })
    } finally {
      setBusy(false)
      setFiles([])
    }
  }

  const agents = (workflow?.config?.agents || []).join(' → ') || 'A1 → A2 → A4 → A5'

  return (
    <div className="chat-page">
      {/* Top Header */}
      <header className="chat-head">
        <div className="chat-head-left">
          <button className="chat-back-btn" onClick={() => navigate('/app/agent-library')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
              <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Back
          </button>
          <div className="chat-brand">
            <NexusMark size={28} />
            <div>
              <strong>{workflow?.name || 'Agent Workspace'}</strong>
              <span>{workflowId} · {agents}</span>
            </div>
          </div>
        </div>
        <div className="chat-head-right">
          <span className="chip"><span className="status-dot ok" /> agent online</span>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="chat-scroll">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.role === 'agent' && <div className="chat-avatar">✦</div>}
            <div className="chat-bubble">
              {(m.kind === 'markdown' || m.kind === 'text') && (
                <div className="chat-markdown">
                  <ReactMarkdown>{m.text}</ReactMarkdown>
                </div>
              )}
              {m.kind === 'summary' && <SummaryCards summary={m.summary} executive={m.executive} />}
              {m.kind === 'legend' && <Legend executive={m.executive} />}
              {m.kind === 'exec' && <ExecutiveSummary exec={m.executive} />}
              {m.kind === 'outputs' && <OutputsRenderer outputs={m.outputs} />}
              {m.kind === 'table' && <VarianceTable rows={m.rows} />}
            </div>
          </div>
        ))}
        {busy && (
          <div className="chat-msg agent">
            <div className="chat-avatar">✦</div>
            <div className="chat-bubble">
              <p className="chat-typing">Agents running pipeline<span>.</span><span>.</span><span>.</span></p>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Bottom Pinned Input Bar */}
      <div className="chat-input-wrap">
        <div className="chat-input">
          <button className="chat-attach" title="Attach data files" onClick={() => fileRef.current?.click()}>
            📎
          </button>
          <input
            ref={fileRef}
            type="file"
            multiple
            accept=".csv,.xlsx,.xls"
            hidden
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
          />
          <div className="chat-files">
            {files.length
              ? `Attached: ${files.map((f) => f.name).join(', ')}`
              : 'No files attached — run will use configured sample data'}
          </div>
          <button className="btn btn-gold chat-run" disabled={busy} onClick={run}>
            {busy ? 'Running…' : '▶ Run'}
          </button>
        </div>
      </div>
    </div>
  )
}

