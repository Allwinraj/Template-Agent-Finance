import { useEffect, useRef, useState, Component } from 'react'
import { useNavigate } from 'react-router-dom'
import './CreateAgent.css'


const API = 'http://127.0.0.1:8000'
const DESCRIPTION = ''
const STEPS = ['Describe', 'Add Data', 'Pipeline', 'Configure Agents', 'Create']

function Stepper({ current }) {
  return (
    <div className="wiz-steps">
      {STEPS.map((s, i) => (
        <div key={s} className={`wiz-step ${i === current ? 'active' : ''} ${i < current ? 'done' : ''}`}>
          <span className="wiz-dot">{i < current ? '✓' : i + 1}</span>
          <span className="wiz-label">{s}</span>
          {i < STEPS.length - 1 && <span className="wiz-line" />}
        </div>
      ))}
    </div>
  )
}

function Tooltip({ children, title, meta, body }) {
  const [show, setShow] = useState(false)
  return (
    <span className="tip" onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      {children}
      {show && (
        <div className="tip-popup">
          {title && <strong>{title}</strong>}
          {meta && <div className="tip-meta">{meta}</div>}
          {body && <div>{body}</div>}
        </div>
      )}
    </span>
  )
}

/* ================================================================
   STEP 0 — Describe + LLM selector
   ================================================================ */
function StepDescribe({ description, setDescription, llm, setLlm, agentName, setAgentName, onNext }) {
  const providers = [
    { id: 'openrouter', name: 'OpenRouter', model: 'liquid/lfm-2.5-2.6b:free', desc: 'Fastest · primary model with auto-fallback' },
    { id: 'sap_ai_core', name: 'SAP AI Core', model: 'gpt-4.1', desc: 'Enterprise · SAP AI Core (GPT-4.1)' },

  ]
  return (
    <div className="wiz-body anim-fade-up">
      <h2>Create your agent</h2>
      <label className="wiz-name-label">
        <span className="wiz-subhead" style={{ marginBottom: 4 }}>Agent name</span>
        <input className="wiz-name-input" value={agentName} placeholder="e.g. Monthly Budget Review" onChange={(e) => setAgentName(e.target.value)} />
      </label>
      <h3 className="wiz-subhead" style={{ marginTop: 20 }}>Describe your use case</h3>
      <p className="wiz-hint">Describe the finance process you want to automate. Include what the data should show and what outputs you expect. The LLM will design the agent flow, calculations, rules and report template from your description and uploaded files.</p>
      <textarea className="wiz-textarea" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
      <h3 className="wiz-subhead">Choose your LLM</h3>
      <p className="wiz-hint">This LLM powers pipeline design, orchestration and the A5 narrative.</p>
      <div className="llm-slim-list">
        {providers.map((p) => (
          <button key={p.id} className={`llm-slim-row ${llm === p.id ? 'selected' : ''}`} onClick={() => setLlm(p.id)}>
            <span className={`llm-slim-radio ${llm === p.id ? 'checked' : ''}`} />
            <div className="llm-slim-info">
              <strong>{p.name}</strong>
              <span className="llm-slim-model">{p.model}</span>
            </div>
            <span className="llm-slim-desc">{p.desc}</span>
            {llm === p.id && <span className="llm-check">✓</span>}
          </button>
        ))}
      </div>
      <div className="wiz-actions"><button className="btn btn-gold" onClick={onNext}>Continue → Add Data</button></div>
    </div>
  )
}

/* ================================================================
   STEP 1 — Add data
   ================================================================ */
function StepData({ profiles, setProfiles, description, onNext, onBack }) {
  const fileRef = useRef(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const upload = async (files) => {
    if (!files?.length) return
    setBusy(true); setError('')
    console.log('[wizard] step 1 → uploading', files.length, 'file(s):', Array.from(files).map((f) => `${f.name} (${f.size} bytes)`))
    try {
      const fd = new FormData()
      for (const f of files) {
        if (f.size === 0) throw new Error(`File "${f.name}" is empty (0 bytes).`)
        fd.append('files', f)
      }
      fd.append('description', description || '')
      console.log('[wizard] step 1 → POST /llm/profile-data…')
      const res = await fetch(`${API}/llm/profile-data`, { method: 'POST', body: fd })
      console.log('[wizard] step 1 → backend responded', res.status)
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `Backend returned ${res.status}`)
      if (data.errors?.length) {
        const msgs = data.errors.map((e) => `${e.file}: ${e.error}`).join(' · ')
        console.warn('[wizard] step 1 → some files failed to profile:', data.errors)
        setError(`Some files could not be read: ${msgs}`)
      }
      const profs = data.profiles || []
      console.log('[wizard] step 1 → profiled', profs.length, 'file(s):', profs.map((p) => `${p.file} → ${p.role} (${p.row_count} rows)`))
      setProfiles(profs)
    } catch (err) {
      // Surface the REAL reason — file read errors (e.g. OneDrive-locked files,
      // unreadable/cloud-only files) also land here as "Failed to fetch".
      console.error('[wizard] step 1 → upload FAILED:', err)
      const msg = String(err?.message || err)
      const hint = /failed to fetch|networkerror|load failed/i.test(msg)
        ? 'Browser could not read a file or reach the backend. If the file lives in OneDrive/Desktop, make sure it is synced locally (right-click → Always keep on this device), or copy it outside the synced folder and retry.'
        : msg
      setError(`Upload failed — ${hint}`)
    } finally { setBusy(false) }
  }
  const useSamples = () => {
    setProfiles([
      { file: 'budget_actuals.csv', role: 'actuals', row_count: 18, columns: ['Company Code', 'GL Account', 'Cost Center', 'Fiscal Period', 'Amount'], sample_rows: [{ 'Company Code': '1000', 'GL Account': '400000', 'Cost Center': 'CC-10', 'Fiscal Period': '2026-08', Amount: 64210.5 }], suggested_mappings: { 'Company Code': 'company_code', 'GL Account': 'gl_account', 'Cost Center': 'cost_center', 'Fiscal Period': 'fiscal_period', Amount: 'amount' } },
      { file: 'budget_plan.csv', role: 'budget', row_count: 18, columns: ['Company Code', 'GL Account', 'Cost Center', 'Fiscal Period', 'Budget Amount'], sample_rows: [{ 'Company Code': '1000', 'GL Account': '400000', 'Cost Center': 'CC-10', 'Fiscal Period': '2026-08', 'Budget Amount': 61000.0 }], suggested_mappings: { 'Company Code': 'company_code', 'GL Account': 'gl_account', 'Cost Center': 'cost_center', 'Fiscal Period': 'fiscal_period', 'Budget Amount': 'amount' } },
    ])
  }
  return (
    <div className="wiz-body anim-fade-up">
      <h2>Add your data</h2>
      <p className="wiz-hint">Your data is previewed here — no AI needed yet. In the next step Nexus reads your description, these columns and your expected outputs, then designs roles, calculations, rules and the report template.</p>
      <div className="wiz-drop" onClick={() => fileRef.current?.click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); upload(e.dataTransfer.files) }}>
        {busy ? <span className="wiz-busy">Reading files…</span> : (<><span className="wiz-drop-icon">⬆</span><strong>Drop files here or click to browse</strong><span>CSV · Excel · any finance dataset</span></>)}
      </div>
      <input ref={fileRef} type="file" multiple accept=".csv,.xlsx,.xls" hidden onChange={(e) => upload(e.target.files)} />
      <button className="btn btn-ghost wiz-sample" onClick={useSamples}>✨ Use demo dataset</button>
      {error && <p className="wiz-error">{error}</p>}
      {profiles.map((p) => (
        <div key={p.file} className="lux-card wiz-profile anim-fade-up">
          <div className="wiz-profile-head"><span className="wiz-role">{p.role}</span><strong>{p.file}</strong><span className="chip">{p.row_count} rows</span></div>
          <div className="wiz-cols">{p.columns.map((c) => <span key={c} className="wiz-col">{c} {p.suggested_mappings?.[c] && <em>→ {p.suggested_mappings[c]}</em>}</span>)}</div>
          <table className="wiz-table"><thead><tr>{p.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>{p.sample_rows.map((r, i) => (<tr key={i}>{p.columns.map((c) => { const v = r[c]; return <td key={c}>{v != null ? String(v) : '\u2014'}</td>; })}</tr>))}</tbody></table>
        </div>
      ))}
      <div className="wiz-actions">
        <button className="btn btn-ghost" onClick={onBack}>← Back</button>
        <button className="btn btn-gold" disabled={!profiles.length} onClick={onNext}>Continue → Pipeline</button>
      </div>
    </div>
  )
}

/* ================================================================
   STEP 2 — Pipeline (AI thinking + flow chart)
   ================================================================ */
const THINK_STAGES = [
  { label: 'Parsing your use case & intent…', icon: '◈' },
  { label: 'Profiling uploaded data — columns, types, quality…', icon: '⬇' },
  { label: 'Consulting the LLM to architect the agent flow…', icon: '✦' },
  { label: 'Selecting agents A1–A6 and wiring hand-offs…', icon: '⇄' },
  { label: 'Composing calculations from the engine library…', icon: '✓' },
  { label: 'Binding rules, thresholds & exception routing…', icon: '⧉' },
  { label: 'Polishing the pipeline — almost there…', icon: '✧' },
]

const RAIL_AGENTS = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6']

function ThinkingBox({ provider }) {
  const [stage, setStage] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    const iv = setInterval(() => setStage((s) => Math.min(s + 1, THINK_STAGES.length - 1)), 900)
    const sec = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => { clearInterval(iv); clearInterval(sec) }
  }, [])
  const railActive = Math.min(THINK_STAGES.length - 1, stage) + 1
  const providerLabel = provider === 'sap_ai_core' ? 'SAP AI Core' : 'OpenRouter'
  return (
    <div className="think-box lux-card">
      <div className="think-head">
        <div className="think-orb">
          <div className="think-spinner" />
          <span className="think-orb-icon">{THINK_STAGES[stage].icon}</span>
        </div>
        <div className="think-title">
          <strong>Nexus AI is architecting your agent</strong>
          <span className="think-typing">{THINK_STAGES[stage].label}<span className="think-ellipsis" /></span>
        </div>
        <span className="think-provider" title="Active LLM provider">{providerLabel}</span>
        <span className="think-timer">{elapsed}s</span>
      </div>

      <div className="think-bar"><span className="think-bar-fill" /></div>

      <div className="think-rail">
        {RAIL_AGENTS.map((a, i) => (
          <div key={a} className="think-rail-seg">
            <div className={`think-node ${i < railActive ? 'lit' : ''}`}>
              <span className="think-node-id">{a}</span>
              <span className="think-node-pulse" />
            </div>
            {i < RAIL_AGENTS.length - 1 && <div className={`think-link ${i < railActive - 1 ? 'lit' : ''}`}><span className="think-link-fill" /></div>}
          </div>
        ))}
      </div>

      <div className="think-steps">
        {THINK_STAGES.map((t, i) => (
          <div key={i} className={`think-item ${i < stage ? 'done' : i === stage ? 'active' : ''}`}>
            <span className="think-dot" />{t.icon} {t.label}
          </div>
        ))}
      </div>
    </div>
  )
}

function StepPipeline({ pipeline, thinking, error, onRetry, onNext, onBack, llm }) {
  if (!pipeline && !thinking && !error) return null

  const agentInfo = {
    A1: { icon: '⬇', name: 'Capture', desc: 'Reads your Excel/CSV files and extracts rows with confidence scoring.' },
    A2: { icon: '⇄', name: 'Harmonize', desc: 'Maps source columns to canonical fields, normalizes dates/amounts, detects duplicates.' },
    A3: { icon: '⧉', name: 'Match', desc: 'Matches records across datasets using exact then tolerant matching with scores.' },
    A4: { icon: '✓', name: 'Validate', desc: 'Runs the calculation pipeline per aligned record, applies rules, flags exceptions.' },
    A5: { icon: '✦', name: 'Explain', desc: 'Produces the variance report with evidence links and management commentary.' },
    A6: { icon: '◈', name: 'Coordinate', desc: 'Routes exceptions to review queues, collects human decisions, escalates overdue items.' },
    A7: { icon: '🔬', name: 'OCR Engine', desc: 'Extracts structured data from scanned invoices and documents (in development).' },
  }

  const steps = pipeline?.calculations || pipeline?.calculation_pipeline || []
  const ruleList = pipeline?.rules || []
  const explanation = pipeline?.explanation

  return (
    <div className="wiz-body anim-fade-up">
      <h2>{thinking ? 'Designing your pipeline…' : error ? 'Pipeline design failed' : 'Pipeline ready — review & tune'}</h2>

      {thinking && <ThinkingBox provider={llm || 'sap_ai_core'} />}

      {!thinking && error && (
        <div className="think-box lux-card wiz-error">
          <p><strong>The AI could not design your pipeline.</strong></p>
          <p className="wiz-hint">{error}</p>
          <p className="wiz-hint">Check the backend terminal for the <code>[pipeline]</code> / <code>[llm]</code> logs, then retry. A data-driven template is used automatically when no LLM key is configured.</p>
          <div className="wiz-actions">
            <button className="btn btn-ghost" onClick={onBack}>← Back to data</button>
            <button className="btn btn-gold" onClick={onRetry}>↻ Retry pipeline design</button>
          </div>
        </div>
      )}

      {!thinking && pipeline && (
        <>
          {pipeline.source === 'mock' && (
            <p className="wiz-hint" style={{ color: '#fbbf24' }}>⚠ Designed from the built-in data-driven template. You can tune everything in the next step.</p>
          )}
          <p className="wiz-hint">
            Your LLM analyzed the use case and your data, then designed this agent flow. You'll configure the details on the next page.
            {pipeline.model && <span className="pipe-model-chip" title="Model that designed this pipeline">✦ {pipeline.model}</span>}
          </p>

          {(() => {
            const roles = (pipeline.sources || []).map((s) => s?.role).filter(Boolean)
            return roles.length > 0 ? (
              <p className="wiz-hint">Roles assigned by the LLM: {roles.map((r) => <span key={r} className="pipe-model-chip">{r}</span>)}</p>
            ) : null
          })()}

          {explanation && (
            <div className="pipe-explain lux-card anim-fade-up">
              <div className="pipe-explain-head"><span className="flow-icon">✦</span><strong>Why this pipeline</strong></div>
              <p>{explanation}</p>
            </div>
          )}

          <div className="flow-chart">
            {(pipeline.agents || ['A1', 'A2', 'A4', 'A5']).map((id, i) => {
              const agent = agentInfo[id] || { icon: '🤖', name: id, desc: 'Specialized agent in the workflow chain.' }
              return (
                <div key={id || i} className="flow-row">
                  <div className="flow-node lux-card">
                    <span className="flow-icon">{agent.icon}</span>
                    <div>
                      <strong>{id} · {agent.name}</strong>
                      <p>{agent.desc}</p>
                    </div>
                  </div>
                  {i < (pipeline.agents?.length || 0) - 1 && <div className="flow-arrow">→</div>}
                </div>
              )
            })}
          </div>

          <p className="wiz-hint" style={{ marginTop: 14 }}>→ Continue to Configure Agents to change engines, parameters and mappings.</p>
        </>
      )}

      <div className="wiz-actions">
        <button className="btn btn-ghost" onClick={onBack}>← Back</button>
        <button className="btn btn-gold" disabled={!pipeline || thinking} onClick={onNext}>Continue → Configure Agents</button>
      </div>
    </div>
  )
}

/* ================================================================
   STEP 3 — Configure agents (editable templates + engine library)
   ================================================================ */
function InfoIcon({ calculator, rule }) {
  const meta = calculator || rule
  if (!meta) return null
  const title = meta.name || meta.id
  const version = meta.version ? `v${meta.version}` : ''
  const category = meta.category ? `Category: ${meta.category}` : ''
  const desc = meta.description || meta.desc || ''
  const inputs = meta.inputs || Object.keys(meta.params || {})
  return (
    <Tooltip
      title={title}
      meta={`${version} ${category}`.trim()}
      body={
        <div>
          {desc && <div style={{ marginBottom: 6 }}>{desc}</div>}
          {inputs.length > 0 && (
            <div className="tip-inputs">
              {inputs.map((inp) => (
                <div key={inp}>{inp}</div>
              ))}
            </div>
          )}
        </div>
      }
    >
      <span className="tip-trigger">ⓘ</span>
    </Tooltip>
  )
}

function StepConfigure({ pipeline, configs, setConfigs, calculators, rules, profiles, onNext, onBack }) {
  const schema = pipeline?.settings_schema || [
    { key: 'materiality', label: 'Materiality threshold', type: 'number', default: 5000, unit: 'USD', description: 'Variances above this amount are flagged as material exceptions' },
    { key: 'on_track_pct', label: 'On-track band', type: 'number', default: 5, unit: '%', description: 'Variance percentage below this is on track' },
    { key: 'review_pct', label: 'Review threshold', type: 'number', default: 10, unit: '%', description: 'Variance percentage at or above this needs finance review' },
  ]
  const settingsValues = { ...Object.fromEntries(schema.map((s) => [s.key, s.default])), ...(pipeline?.settings || {}), ...(configs.settings || {}) }

  const updateSetting = (key, value) => {
    const next = { ...(configs.settings || {}), [key]: value }
    setConfigs({ ...configs, settings: next })
  }

  const [policy, setPolicy] = useState(pipeline?.calculation_policy || {
    null_behavior: 'create_exception',
    blank_behavior: 'create_exception',
    zero_denominator: 'create_exception',
    rounding_mode: 'half_even',
    decimal_places: 2,
    currency_mismatch: 'stop_pipeline',
  })
  const agentIds = pipeline?.agents || []

  // A5 report template — pre-filled by the LLM from the 'Output:' bullets,
  // editable here so the user controls the final report layout.
  const outputSpec = configs.output_spec || pipeline?.output_spec || []
  const updateBlock = (idx, field, value) => {
    const next = [...outputSpec]
    next[idx] = { ...next[idx], [field]: value }
    setConfigs({ ...configs, output_spec: next })
  }
  const removeBlock = (idx) => setConfigs({ ...configs, output_spec: outputSpec.filter((_, x) => x !== idx) })
  const addBlock = () => setConfigs({ ...configs, output_spec: [...outputSpec, { id: `output_${outputSpec.length + 1}`, title: '', render: 'table', description: '' }] })

  const calcs = configs.calculations || pipeline?.calculations || pipeline?.calculation_pipeline || []
  const rls = configs.rules || pipeline.rules || []

  const setCalcs = (next) => setConfigs({ ...configs, calculations: next })
  const setRules = (next) => setConfigs({ ...configs, rules: next })

  // split calculations by the agent that uses them
  const a3Calcs = calcs.filter((c) => c.used_by === 'A3')
  const a4Calcs = calcs.filter((c) => c.used_by === 'A4' || !c.used_by)
  const setA3Calcs = (next) => {
    const rest = calcs.filter((c) => c.used_by !== 'A3')
    setCalcs([...next, ...rest])
  }
  const setA4Calcs = (next) => {
    const rest = calcs.filter((c) => c.used_by !== 'A4')
    setCalcs([...rest, ...next])
  }

  const fieldOptions = (() => {
    const opts = new Set()
    // generic: prefix each column with its detected role — works for any use case
    for (const p of (profiles || [])) {
      const prefix = p.role || 'data'
      for (const c of (p.columns || [])) opts.add(`${prefix}.${c}`)
    }
    for (const k of Object.keys(settingsValues)) opts.add(`settings.${k}`)
    return Array.from(opts).sort()
  })()

  // outputs of earlier calculation steps (for chaining)
  const resultOptions = calcs.map((c) => c.output_mapping?.result || `results.${c.id}`).filter(Boolean)
  const allFieldOptions = [...fieldOptions, ...resultOptions]

  // ---- generic structural field matching: token overlap only, no domain words ----
  const tokenize = (s) => String(s || '').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)
  const scoreField = (inputName, fieldName) => {
    const inTok = tokenize(inputName)
    const fTok = tokenize(fieldName.replace(/^[a-z0-9_]+\./, '')) // ignore role prefix for body match
    let score = 0
    for (const t of inTok) {
      if (fTok.some((f) => f === t)) score += 3
      else if (fTok.some((f) => f.includes(t) || t.includes(f))) score += 1
    }
    // structural bonuses (no domain vocabulary):
    // role-prefix match — input mentions the role the field belongs to
    const role = fieldName.split('.')[0]
    if (inTok.includes(role)) score += 2
    // chained results match computation-style inputs
    if (fieldName.startsWith('results.') && inTok.some((t) => ['result', 'output', 'value'].includes(t))) score += 2
    // settings match parameter-style inputs
    if (fieldName.startsWith('settings.') && inTok.some((t) => ['threshold', 'limit', 'max', 'min', 'rate', 'days'].includes(t))) score += 2
    return score
  }

  const bestField = (inputName, { exclude } = {}) => {
    let best = null, bestScore = 0
    for (const f of allFieldOptions) {
      if (exclude && exclude.includes(f)) continue
      const s = scoreField(inputName, f)
      if (s > bestScore) { bestScore = s; best = f }
    }
    return bestScore > 0 ? best : null
  }

  // auto-fill a calculator's input mapping from the use case + data columns;
  // keeps existing valid values, only fills gaps
  const autoMapInputs = (calc, meta) => {
    const mapping = {}
    const taken = []
    for (const inp of (meta?.inputs || [])) {
      const existing = calc.input_mapping?.[inp]
      if (existing && allFieldOptions.includes(existing)) {
        mapping[inp] = existing
        taken.push(existing)
      } else {
        const pick = bestField(inp, { exclude: taken }) || existing || ''
        mapping[inp] = pick
        if (pick) taken.push(pick)
      }
    }
    return mapping
  }

  // auto-fill rule params: field-like params map to fields, list params to comparison keys
  const autoMapRuleParams = (ruleId, baseParams) => {
    const meta = ruleMeta(ruleId)
    const defaults = { ...(meta?.params || {}), ...(baseParams || {}) }
    const params = {}
    for (const [k, v] of Object.entries(defaults)) {
      const lk = k.toLowerCase()
      if (Array.isArray(v)) {
        const cmpKeys = pipeline?.comparison?.keys
        params[k] = (cmpKeys && /keys?$/.test(lk)) ? [...cmpKeys] : v
      } else if (typeof v === 'string' && (v.includes('.') || /fields?$/.test(lk))) {
        params[k] = bestField(lk) || v
      } else {
        params[k] = v
      }
    }
    return params
  }

  const updateCalc = (idx, field, value) => {
    const next = [...calcs]
    next[idx] = { ...next[idx], [field]: value }
    setCalcs(next)
  }

  const swapCalc = (idx, calcName) => {
    const lib = (calculators || []).find((c) => c.name === calcName)
    const current = calcs[idx] || {}
    const id = current.id || `calc_${idx + 1}`
    const calc = {
      ...current,
      calculator: calcName,
      version: lib?.version ?? 1,
      // auto-fill from use case + data columns; keeps values the user already set
      input_mapping: autoMapInputs({ ...current, input_mapping: current.input_mapping || {} }, lib),
      output_mapping: { result: current.output_mapping?.result || `results.${id}` },
    }
    const next = [...calcs]
    next[idx] = calc
    setCalcs(next)
  }

  const updateRule = (idx, field, value) => {
    const next = [...rls]
    next[idx] = { ...next[idx], [field]: value }
    setRules(next)
  }

  const swapRule = (idx, name) => {
    const lib = (rules || []).find((r) => r.name === name)
    const next = [...rls]
    next[idx] = { id: name, version: lib?.version ?? 1, params: autoMapRuleParams(name, {}) }
    setRules(next)
  }

  const updateA3Calc = (idx, field, value) => {
    const next = [...a3Calcs]
    next[idx] = { ...next[idx], [field]: value }
    setA3Calcs(next)
  }

  const swapA3Calc = (idx, calcName) => {
    const lib = (calculators || []).find((c) => c.name === calcName)
    const current = a3Calcs[idx] || {}
    const id = current.id || `a3_calc_${idx + 1}`
    const calc = {
      ...current,
      calculator: calcName,
      version: lib?.version ?? 1,
      used_by: 'A3',
      input_mapping: autoMapInputs({ ...current, input_mapping: current.input_mapping || {} }, lib),
      output_mapping: { result: current.output_mapping?.result || `results.${id}` },
    }
    const next = [...a3Calcs]
    next[idx] = calc
    setA3Calcs(next)
  }

  const handleA3MappingChange = (calcIdx, inputName, newValue) => {
    const next = [...a3Calcs]
    const calc = { ...next[calcIdx] }
    calc.input_mapping = { ...calc.input_mapping, [inputName]: newValue }
    const deps = new Set()
    for (const [k, v] of Object.entries(calc.input_mapping || {})) {
      if (v && v.startsWith('results.')) {
        const ref = v.split('.')[1]
        if (ref && ref !== calc.id) deps.add(ref)
      }
    }
    calc.depends_on = Array.from(deps)
    next[calcIdx] = calc
    setA3Calcs(next)
  }

  const addA3Calc = () => {
    const lib = (calculators || []).find((c) => ['amount_difference', 'date_difference', 'match_score'].includes(c.name)) || (calculators || [])[0]
    const id = `a3_calc_${a3Calcs.length + 1}`
    const calc = {
      id, calculator: lib?.name || 'amount_difference', version: lib?.version || 1, used_by: 'A3', scope: 'row',
      input_mapping: {}, output_mapping: { result: `results.${id}` }, depends_on: [],
    }
    calc.input_mapping = autoMapInputs(calc, lib)
    const deps = new Set()
    for (const v of Object.values(calc.input_mapping)) {
      if (v && v.startsWith('results.')) deps.add(v.split('.')[1])
    }
    calc.depends_on = Array.from(deps)
    setA3Calcs([...a3Calcs, calc])
  }

  const removeA3Calc = (idx) => setA3Calcs(a3Calcs.filter((_, x) => x !== idx))

  const parseVal = (v) => {
    if (v === '' || v == null) return v
    const n = Number(v)
    return Number.isNaN(n) ? v : n
  }

  const addCalc = () => {
    const lib = (calculators || []).find((c) => c.name === 'subtract_values') || (calculators || [])[0]
    const id = `calc_${calcs.length + 1}`
    const calc = {
      id, calculator: lib?.name || 'subtract_values', version: lib?.version || 1, used_by: 'A4', scope: 'row',
      input_mapping: {}, output_mapping: { result: `results.${id}` }, depends_on: [],
    }
    // auto-map inputs from the use case + data columns, and auto-link dependencies
    calc.input_mapping = autoMapInputs(calc, lib)
    const deps = new Set()
    for (const v of Object.values(calc.input_mapping)) {
      if (v && v.startsWith('results.')) deps.add(v.split('.')[1])
    }
    calc.depends_on = Array.from(deps)
    setCalcs([...calcs, calc])
  }

  const removeCalc = (idx) => setCalcs(calcs.filter((_, x) => x !== idx))

  const addRuleRow = () => {
    const lib = (rules || [])[0]
    if (!lib) return
    setRules([...rls, { id: lib.name, version: lib.version, params: autoMapRuleParams(lib.name, {}) }])
  }

  const removeRuleRow = (idx) => setRules(rls.filter((_, x) => x !== idx))

  // Seed the editable copy from the LLM-designed pipeline on first entry, and
  // auto-fill any params the LLM left empty — user only edits if they want to.
  useEffect(() => {
    if (configs.calculations || configs.rules) return
    const seededRules = (pipeline.rules || []).map((r) => {
      const meta = ruleMeta(r.id)
      const hasEmpty = !r.params || Object.keys(r.params).length === 0 ||
        Object.values(r.params).some((v) => v == null || v === '')
      if (!hasEmpty || !meta) return r
      return { ...r, params: autoMapRuleParams(r.id, r.params || {}) }
    })
    setConfigs({ ...configs, calculations: pipeline.calculations || pipeline.calculation_pipeline || [], rules: seededRules })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pipeline])

  const handleMappingChange = (calcIdx, inputName, newValue) => {
    const next = [...calcs]
    const calc = { ...next[calcIdx] }
    calc.input_mapping = { ...calc.input_mapping, [inputName]: newValue }
    const deps = new Set()
    for (const [k, v] of Object.entries(calc.input_mapping || {})) {
      if (v && v.startsWith('results.')) {
        const ref = v.split('.')[1]
        if (ref && ref !== calc.id) deps.add(ref)
      }
    }
    calc.depends_on = Array.from(deps)
    next[calcIdx] = calc
    setCalcs(next)
  }

  const calcMeta = (name) => (calculators || []).find((c) => c.name === name)
  const ruleMeta = (name) => (rules || []).find((r) => r.name === name)

  return (
    <div className="wiz-body anim-fade-up">
      <h2>Configure agents</h2>
      <p className="wiz-hint">Templates pre-filled by analyzing your Excel data. Edit any field, or change the calculation/rule engine from the library. Hover over ⓘ for details.</p>

      <div className="cfg-settings lux-card">
        <div className="cfg-settings-head">
          <span className="cfg-settings-icon">⚙</span>
          <div>
            <strong>Use-case settings</strong>
            <p>Tuning knobs the LLM chose for this specific use case — change values; behavior follows.</p>
          </div>
        </div>
        <div className="cfg-settings-grid">
          {schema.map((s) => (
            <label key={s.key} className="cfg-setting" title={s.description || ''}>
              <span className="cfg-setting-label">{s.label}{s.unit ? <em> ({s.unit})</em> : ''} <span className="cfg-setting-key">settings.{s.key}</span></span>
              {s.type === 'select' && s.options ? (
                <select value={settingsValues[s.key] ?? s.default} onChange={(e) => updateSetting(s.key, parseVal(e.target.value))}>
                  {s.options.map((o) => <option key={String(o)} value={o}>{String(o)}</option>)}
                </select>
              ) : (
                <input
                  type={s.type === 'number' ? 'number' : 'text'}
                  value={settingsValues[s.key] ?? s.default ?? ''}
                  step={s.step || (s.type === 'number' ? 1 : undefined)}
                  min={s.min}
                  onChange={(e) => updateSetting(s.key, s.type === 'number' ? Number(e.target.value) : e.target.value)}
                />
              )}
              {s.description && <span className="cfg-setting-desc">{s.description}</span>}
            </label>
          ))}
        </div>
      </div>

      {agentIds.includes('A5') && (
        <div className="lux-card cfg-card">
          <div className="cfg-head"><span className="cfg-icon">✦</span><div><strong>A5 · Explain — Report template</strong><p>Pre-filled from the Output section of your use case. Edit, reorder, add or remove blocks — the chat report renders exactly this.</p></div></div>
          <div className="cfg-detail">
            <strong>Output blocks</strong>
            <div className="tmpl-list">
              {outputSpec.map((b, i) => (
                <div key={i} className="tmpl-block">
                  <div className="tmpl-row">
                    <input className="tmpl-title" value={b.title || ''} placeholder="Block title" onChange={(e) => updateBlock(i, 'title', e.target.value)} />
                    <select value={b.render || 'table'} onChange={(e) => updateBlock(i, 'render', e.target.value)} title="How this block renders in the chat">
                      <option value="kpi">kpi — headline figures</option>
                      <option value="table">table — row-level listing</option>
                      <option value="exceptions">exceptions — failed rows</option>
                      <option value="narrative">narrative — written text</option>
                    </select>
                    <select value={b.source || ''} onChange={(e) => updateBlock(i, 'source', e.target.value)} title="Which data this block shows">
                      <option value="">auto — all results</option>
                      <option value="summary">summary — headline numbers</option>
                      <option value="compared_rows">compared rows — full table</option>
                      <option value="exceptions">exceptions — failed rows</option>
                      {(calcs || []).map((c) => (
                        <option key={c.id} value={c.output_mapping?.result || `results.${c.id}`}>
                          {c.output_mapping?.result || `results.${c.id}`}
                        </option>
                      ))}
                    </select>
                    <button className="pipe-remove" onClick={() => removeBlock(i)} title="Remove block">✕</button>
                  </div>
                  <input className="tmpl-desc" value={b.description || ''} placeholder="What this section shows" onChange={(e) => updateBlock(i, 'description', e.target.value)} />
                  {i < outputSpec.length - 1 && <div className="chain-arrow" />}
                </div>
              ))}
              <button className="pipe-add" onClick={addBlock}>+ Add output block</button>
            </div>
          </div>
        </div>
      )}

      {agentIds.includes('A3') && (
        <div className="lux-card cfg-card">
          <div className="cfg-head"><span className="cfg-icon">⧉</span><div><strong>A3 · Match</strong><p>Matching calculations per record pair — configure the scoring logic used during tolerant matching.</p></div></div>
          <div className="cfg-detail">
            <strong>Matching calculations</strong>

            {a3Calcs.length > 0 && (
              <div className="chain-viz">
                {a3Calcs.map((calc, i) => {
                  const meta = calcMeta(calc.calculator)
                  return (
                    <div key={i} className="chain-node">
                      <div className="chain-node-header">
                        <span className="chain-node-id">{calc.id}</span>
                        <span className="chain-node-name">{meta?.name || calc.calculator}</span>
                        <span className="chain-node-ver">v{calc.version} {meta?.category ? `· ${meta.category}` : ''}</span>
                        <button className="pipe-remove" onClick={() => removeA3Calc(i)} title="Remove step">✕</button>
                      </div>
                      <div className="chain-io">
                        {(meta?.inputs || []).map((inp) => (
                          <span key={inp} className="chain-badge">{inp} → {calc.input_mapping?.[inp] || '—'}</span>
                        ))}
                        <span className="chain-badge" style={{ color: '#34d399' }}>→ {calc.output_mapping?.result || `results.${calc.id}`}</span>
                      </div>
                      {i < a3Calcs.length - 1 && <div className="chain-arrow" />}
                    </div>
                  )
                })}
              </div>
            )}

            {a3Calcs.map((calc, i) => {
              const meta = calcMeta(calc.calculator)
              return (
                <div key={i} className="cfg-engine-block">
                  <div className="cfg-engine-row">
                    <span className="cfg-engine-id">{calc.id}</span>
                    <select value={calc.calculator} onChange={(e) => swapA3Calc(i, e.target.value)} title="Change matching calculation engine from the library">
                      {(calculators || []).map((c) => (
                        <option key={c.name} value={c.name}>{c.name} — {c.description}</option>
                      ))}
                    </select>
                    <InfoIcon calculator={meta} />
                    <span className="cfg-engine-ver">v{calc.version}</span>
                    <button className="pipe-remove" onClick={() => removeA3Calc(i)} title="Remove step">✕</button>
                  </div>
                  <div className="cfg-mappings">
                    {(meta?.inputs || []).map((inp) => (
                      <label key={inp} className="pipe-in-edit">
                        <span>{inp} ←</span>
                        <select value={calc.input_mapping?.[inp] || ''} onChange={(e) => handleA3MappingChange(i, inp, e.target.value)} placeholder="Select a field">
                          <option value="">— select field —</option>
                          {allFieldOptions.map((f) => <option key={f} value={f}>{f}</option>)}
                          {(calc.input_mapping?.[inp] || '') && !allFieldOptions.includes(calc.input_mapping[inp]) && (
                            <option key={calc.input_mapping[inp]} value={calc.input_mapping[inp]}>{calc.input_mapping[inp]}</option>
                          )}
                        </select>
                      </label>
                    ))}
                    {(!meta?.inputs || meta.inputs.length === 0) && (
                      <p className="wiz-hint" style={{ marginTop: 6 }}>No inputs required for this calculator.</p>
                    )}
                  </div>
                  {calc.depends_on?.length > 0 && (
                    <div style={{ marginTop: 6, fontSize: '0.72rem', color: '#fbbf24' }}>
                      Auto-linked: depends on {calc.depends_on.join(', ')}
                    </div>
                  )}
                </div>
              )
            })}
            <button className="pipe-add" onClick={addA3Calc}>+ Add matching calculation</button>
          </div>
        </div>
      )}

      {agentIds.includes('A4') && (
        <div className="lux-card cfg-card">
          <div className="cfg-head"><span className="cfg-icon">✓</span><div><strong>A4 · Validate</strong><p>Calculations and rules applied per aligned record.</p></div></div>
          <div className="cfg-detail">
            <strong>Calculation pipeline</strong>

            {a4Calcs.length > 0 && (
              <div className="chain-viz">
                {a4Calcs.map((calc, i) => {
                  const meta = calcMeta(calc.calculator)
                  return (
                    <div key={i} className="chain-node">
                      <div className="chain-node-header">
                        <span className="chain-node-id">{calc.id}</span>
                        <span className="chain-node-name">{meta?.name || calc.calculator}</span>
                        <span className="chain-node-ver">v{calc.version} {meta?.category ? `· ${meta.category}` : ''}</span>
                        <button className="pipe-remove" onClick={() => removeCalc(calcs.findIndex((c) => c.id === calc.id))} title="Remove step">✕</button>
                      </div>
                      <div className="chain-io">
                        {(meta?.inputs || []).map((inp) => (
                          <span key={inp} className="chain-badge">{inp} → {calc.input_mapping?.[inp] || '—'}</span>
                        ))}
                        <span className="chain-badge" style={{ color: '#34d399' }}>→ {calc.output_mapping?.result || `results.${calc.id}`}</span>
                      </div>
                      {i < a4Calcs.length - 1 && <div className="chain-arrow" />}
                    </div>
                  )
                })}
              </div>
            )}

            {a4Calcs.map((calc, i) => {
              const meta = calcMeta(calc.calculator)
              const originalIdx = calcs.findIndex((c) => c.id === calc.id)
              return (
                <div key={i} className="cfg-engine-block">
                  <div className="cfg-engine-row">
                    <span className="cfg-engine-id">{calc.id}</span>
                    <select value={calc.calculator} onChange={(e) => swapCalc(originalIdx, e.target.value)} title="Change calculation engine from the library">
                      {(calculators || []).map((c) => (
                        <option key={c.name} value={c.name}>{c.name} — {c.description}</option>
                      ))}
                    </select>
                    <InfoIcon calculator={meta} />
                    <span className="cfg-engine-ver">v{calc.version}</span>
                    <button className="pipe-remove" onClick={() => removeCalc(originalIdx)} title="Remove step">✕</button>
                  </div>
                  <div className="cfg-mappings">
                    {(meta?.inputs || []).map((inp) => (
                      <label key={inp} className="pipe-in-edit">
                        <span>{inp} ←</span>
                        <select value={calc.input_mapping?.[inp] || ''} onChange={(e) => handleMappingChange(originalIdx, inp, e.target.value)} placeholder="Select a field">
                          <option value="">— select field —</option>
                          {allFieldOptions.map((f) => <option key={f} value={f}>{f}</option>)}
                          {(calc.input_mapping?.[inp] || '') && !allFieldOptions.includes(calc.input_mapping[inp]) && (
                            <option key={calc.input_mapping[inp]} value={calc.input_mapping[inp]}>{calc.input_mapping[inp]}</option>
                          )}
                        </select>
                      </label>
                    ))}
                    {(!meta?.inputs || meta.inputs.length === 0) && (
                      <p className="wiz-hint" style={{ marginTop: 6 }}>No inputs required for this calculator.</p>
                    )}
                  </div>
                  {calc.depends_on?.length > 0 && (
                    <div style={{ marginTop: 6, fontSize: '0.72rem', color: '#fbbf24' }}>
                      Auto-linked: depends on {calc.depends_on.join(', ')}
                    </div>
                  )}
                </div>
              )
            })}
            <button className="pipe-add" onClick={addCalc}>+ Add calculation step</button>

            <strong style={{ marginTop: 18, display: 'block' }}>Rules</strong>
            {rls.map((rule, i) => {
              const meta = ruleMeta(rule.id)
              return (
                <div key={i} className="cfg-engine-block">
                  <div className="cfg-engine-row">
                    <span className="cfg-engine-id">{rule.id}</span>
                    <select value={rule.id} onChange={(e) => swapRule(i, e.target.value)} title="Change rule engine from the library">
                      {(rules || []).map((r) => <option key={r.name} value={r.name}>{r.name} — {r.description}</option>)}
                    </select>
                    <InfoIcon rule={meta} />
                    <span className="cfg-engine-ver">v{rule.version || meta?.version || 1}</span>
                    <button className="pipe-remove" onClick={() => removeRuleRow(i)} title="Remove rule">✕</button>
                  </div>
                  <div className="cfg-mappings">
                    {(meta?.params && Object.keys(meta.params).length > 0) ? (
                      Object.entries(meta.params).map(([k, defaultVal]) => {
                        const currentVal = rule.params?.[k] ?? defaultVal
                        const isFieldRef = typeof currentVal === 'string' && (currentVal.startsWith('settings.') || currentVal.startsWith('results.'))
                        const isList = Array.isArray(defaultVal)
                        if (isFieldRef) {
                          return (
                            <label key={k} className="pipe-in-edit">
                              <span>{k}</span>
                              <select value={currentVal} onChange={(e) => updateRule(i, 'params', { ...rule.params, [k]: e.target.value })}>
                                <option value="">— select —</option>
                                {allFieldOptions.map((f) => <option key={f} value={f}>{f}</option>)}
                                {!allFieldOptions.includes(currentVal) && <option key={currentVal} value={currentVal}>{currentVal}</option>}
                              </select>
                            </label>
                          )
                        }
                        if (isList) {
                          return (
                            <label key={k} className="pipe-in-edit">
                              <span>{k}</span>
                              <input value={JSON.stringify(currentVal || [])} onChange={(e) => {
                                try { updateRule(i, 'params', { ...rule.params, [k]: JSON.parse(e.target.value) }) }
                                catch { updateRule(i, 'params', { ...rule.params, [k]: e.target.value }) }
                              }} placeholder='e.g. ["reference"]' />
                            </label>
                          )
                        }
                        return (
                          <label key={k} className="pipe-in-edit">
                            <span>{k}</span>
                            <input type={typeof defaultVal === 'number' ? 'number' : 'text'} value={currentVal ?? ''} onChange={(e) => updateRule(i, 'params', { ...rule.params, [k]: parseVal(e.target.value) })} />
                          </label>
                        )
                      })
                    ) : (
                      <p className="wiz-hint" style={{ marginTop: 6 }}>No configurable parameters for this rule.</p>
                    )}
                  </div>
                </div>
              )
            })}
            <button className="pipe-add" onClick={addRuleRow}>+ Add rule</button>
          </div>
        </div>
      )}

      <details className="policy-panel">
        <summary>Calculation policy (advanced)</summary>
        <div className="policy-grid">
          <div className="policy-field">
            <label>Rounding mode</label>
            <select value={policy.rounding_mode} onChange={(e) => setPolicy({ ...policy, rounding_mode: e.target.value })}>
              <option value="half_even">Half even (banker's)</option>
              <option value="half_up">Half up</option>
              <option value="down">Round down</option>
            </select>
          </div>
          <div className="policy-field">
            <label>Decimal places</label>
            <input type="number" min={0} max={6} value={policy.decimal_places} onChange={(e) => setPolicy({ ...policy, decimal_places: Number(e.target.value) })} />
          </div>
          <div className="policy-field">
            <label>Null / missing value</label>
            <select value={policy.null_behavior} onChange={(e) => setPolicy({ ...policy, null_behavior: e.target.value })}>
              <option value="create_exception">Create exception</option>
              <option value="zero">Treat as zero</option>
              <option value="skip">Skip calculation</option>
            </select>
          </div>
          <div className="policy-field">
            <label>Zero denominator</label>
            <select value={policy.zero_denominator} onChange={(e) => setPolicy({ ...policy, zero_denominator: e.target.value })}>
              <option value="create_exception">Create exception</option>
              <option value="return_null">Return null</option>
              <option value="skip">Skip calculation</option>
            </select>
          </div>
          <div className="policy-field">
            <label>Currency mismatch</label>
            <select value={policy.currency_mismatch} onChange={(e) => setPolicy({ ...policy, currency_mismatch: e.target.value })}>
              <option value="stop_pipeline">Stop pipeline</option>
              <option value="create_exception">Create exception</option>
              <option value="warn">Warn and continue</option>
            </select>
          </div>
        </div>
      </details>

      <div className="wiz-actions">
        <button className="btn btn-ghost" onClick={onBack}>← Back</button>
        <button className="btn btn-gold" onClick={() => { setConfigs({ ...configs, calculations: calcs, rules: rls, settings: settingsValues, output_spec: outputSpec, calculation_policy: policy }); onNext() }}>Create Agent →</button>
      </div>
    </div>
  )
}

/* ================================================================
   STEP 4 — Create
   ================================================================ */
function StepCreate({ pipeline, configs, profiles, agentName, onCreated, onBack }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const create = async () => {
    setBusy(true); setError('')
    try {
      const saved = pipeline.sources || pipeline.agent_configs?.A1?.sources || []
      let sources = saved.map((s) => ({ ...s, file: profiles.find((p) => p.role === s.role)?.file || s.file }))
      if (!sources.length) {
        sources = profiles.map((p) => ({ role: p.role, file: p.file, required_fields: [], field_mappings: p.suggested_mappings || {} }))
      }
      const config = {
        agents: pipeline.agents, template: pipeline.template, sources,
        comparison: pipeline.comparison, calculations: configs.calculations || pipeline.calculations,
        rules: configs.rules || pipeline.rules,
        settings: { ...(pipeline.settings || {}), ...(configs.settings || {}) },
        output_spec: configs.output_spec || pipeline.output_spec || [],
        routing: pipeline.routing, report: pipeline.report, llm_provider: configs.llm || 'openrouter',
        calculation_policy: configs.calculation_policy || pipeline.calculation_policy,
      }
      const res = await fetch(`${API}/registry/workflows`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: agentName?.trim() || pipeline.title, description: pipeline.description, config }) })
      const wf = await res.json()
      if (!wf.workflow_id) throw new Error(wf.detail || 'Failed')
      onCreated(wf)
      navigate(`/app/agent-chat/${wf.workflow_id}`)
    } catch (e) { setError(e.message || 'Could not create the agent.') }
    finally { setBusy(false) }
  }
  return (
    <div className="wiz-body anim-fade-up">
      <h2>Create the agent</h2>
      <p className="wiz-hint">Saves the workflow as a published agent. A chat window opens to test it.</p>
      <div className="lux-card cfg-card">
        <strong>{pipeline?.title}</strong><p>{pipeline?.description}</p>
        <div className="wiz-cols">
          <span className="wiz-col">{pipeline?.agents?.join(' → ')}</span>
          <span className="wiz-col">LLM: {pipeline?.model || configs.llm || 'openrouter'}</span>
          {Object.entries(configs.settings || pipeline?.settings || {}).slice(0, 3).map(([k, v]) => (
            <span key={k} className="wiz-col">{k}: {String(v)}</span>
          ))}
        </div>
      </div>
      {error && <p className="wiz-error">{error}</p>}
      <div className="wiz-actions">
        <button className="btn btn-ghost" onClick={onBack}>← Back</button>
        <button className="btn btn-gold" disabled={busy} onClick={create}>{busy ? 'Creating…' : '🚀 Create Agent & Open Chat'}</button>
      </div>
    </div>
  )
}

/* ================================================================
   Wizard Error Boundary & Container
   ================================================================ */
class WizardErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error, errorInfo) {
    console.error('[CreateAgent] Uncaught render error in wizard:', error, errorInfo)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="think-box lux-card wiz-error" style={{ margin: '2rem auto', maxWidth: 800 }}>
          <h2>Something went wrong loading this step</h2>
          <p className="wiz-hint">Error: {String(this.state.error?.message || this.state.error)}</p>
          <div className="wiz-actions">
            <button className="btn btn-gold" onClick={() => { this.setState({ hasError: false }); window.location.reload() }}>
              ↻ Reload Wizard
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function CreateAgent() {
  const [step, setStep] = useState(0)
  const [description, setDescription] = useState(DESCRIPTION)
  const [agentName, setAgentName] = useState('')
  const [llm, setLlm] = useState('sap_ai_core')
  const [profiles, setProfiles] = useState([])
  const [pipeline, setPipeline] = useState(null)
  const [thinking, setThinking] = useState(false)
  const [pipelineError, setPipelineError] = useState('')
  const [configs, setConfigs] = useState({ materiality: 10000, llm: 'sap_ai_core' })
  const [created, setCreated] = useState(null)
  const [calculators, setCalculators] = useState([])
  const [rules, setRules] = useState([])

  useEffect(() => {
    fetch(`${API}/api/calculators`).then((r) => r.json()).then((d) => setCalculators(d.calculators || [])).catch(() => {})
    fetch(`${API}/api/rules`).then((r) => r.json()).then((d) => setRules(d.rules || [])).catch(() => {})
  }, [])

  const startedRef = useRef(false)
  useEffect(() => {
    if (step !== 2 || pipeline || startedRef.current) return
    startedRef.current = true
    setThinking(true)
    setPipelineError('')
    console.log('[wizard] step 2 → POST /llm/design-pipeline (profiles:', profiles.length, ', provider:', llm, ')')
    ;(async () => {
      try {
        const res = await fetch(`${API}/llm/design-pipeline`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ description, profiles, llm_provider: llm }),
        })
        if (!res.ok) throw new Error(`Backend returned ${res.status}`)
        const data = await res.json()
        if (data.error) throw new Error(data.error)
        console.log('[wizard] pipeline received:', data?.title, data?.agents, '| source:', data?.source, '| provider:', llm)
        setPipeline(data)
      } catch (err) {
        console.error('[wizard] pipeline generation failed:', err)
        setPipelineError(String(err?.message || err))
      } finally {
        setThinking(false)
      }
    })()
  }, [step, pipeline, description, profiles, llm])


  const retryPipeline = () => {
    startedRef.current = false
    setPipelineError('')
    setPipeline(null)
    setThinking(false)
  }

  return (
    <WizardErrorBoundary>
      <div className="page">
        <header className="page-head">
          <div>
            <h1>Create Agent</h1>
            <p>Describe → add data → AI designs pipeline → configure → create.</p>
          </div>
          {created && <span className="chip"><span className="status-dot ok" /> {created.workflow_id} created</span>}
        </header>
        <Stepper current={step} />
        <div className="lux-card wiz-card">
          {step === 0 && <StepDescribe description={description} setDescription={setDescription} llm={llm} setLlm={setLlm} agentName={agentName} setAgentName={setAgentName} onNext={() => { setConfigs((c) => ({ ...c, llm })); setStep(1) }} />}
          {step === 1 && <StepData profiles={profiles} setProfiles={setProfiles} description={description} onNext={() => setStep(2)} onBack={() => setStep(0)} />}
          {step === 2 && <StepPipeline pipeline={pipeline} thinking={thinking} error={pipelineError} llm={llm} onRetry={retryPipeline} onNext={() => setStep(3)} onBack={() => setStep(1)} />}
          {step === 3 && <StepConfigure pipeline={pipeline} configs={configs} setConfigs={setConfigs} calculators={calculators} rules={rules} profiles={profiles} onNext={() => setStep(4)} onBack={() => setStep(2)} />}
          {step === 4 && <StepCreate pipeline={pipeline} configs={configs} profiles={profiles} agentName={agentName} onCreated={setCreated} onBack={() => setStep(3)} />}
        </div>
      </div>
    </WizardErrorBoundary>
  )
}
