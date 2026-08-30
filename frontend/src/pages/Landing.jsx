import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AGENTS } from '../data/mockData.js'
import './Landing.css'

/* ---------- Animated particle constellation canvas ---------- */
function Constellation() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    let raf
    const particles = []
    const mouse = { x: -9999, y: -9999 }

    const resize = () => {
      canvas.width = canvas.offsetWidth * devicePixelRatio
      canvas.height = canvas.offsetHeight * devicePixelRatio
    }
    resize()
    window.addEventListener('resize', resize)

    const COUNT = 70
    for (let i = 0; i < COUNT; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        r: Math.random() * 1.8 + 0.4,
      })
    }

    const step = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      const linkDist = 130 * devicePixelRatio

      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1

        const dxm = p.x - mouse.x
        const dym = p.y - mouse.y
        const dm = Math.hypot(dxm, dym)
        if (dm < 160 * devicePixelRatio && dm > 0) {
          p.x += (dxm / dm) * 0.6
          p.y += (dym / dm) * 0.6
        }
      }

      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i]
          const b = particles[j]
          const d = Math.hypot(a.x - b.x, a.y - b.y)
          if (d < linkDist) {
            const alpha = (1 - d / linkDist) * 0.35
            ctx.strokeStyle = `rgba(124,92,255,${alpha})`
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.stroke()
          }
        }
      }

      for (const p of particles) {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r * devicePixelRatio, 0, Math.PI * 2)
        ctx.fillStyle = 'rgba(124,92,255,0.8)'
        ctx.fill()
      }

      raf = requestAnimationFrame(step)
    }
    step()

    const onMove = (e) => {
      const rect = canvas.getBoundingClientRect()
      mouse.x = (e.clientX - rect.left) * devicePixelRatio
      mouse.y = (e.clientY - rect.top) * devicePixelRatio
    }
    window.addEventListener('mousemove', onMove)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onMove)
    }
  }, [])

  return <canvas ref={canvasRef} className="constellation" aria-hidden="true" />
}

/* ---------- Nexus logo mark ---------- */
export function NexusMark({ size = 30 }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size}>
      <circle cx="32" cy="32" r="6" fill="url(#nx)" />
      <circle cx="14" cy="16" r="4" fill="url(#g2)" />
      <circle cx="50" cy="16" r="4" fill="url(#g2)" />
      <circle cx="14" cy="48" r="4" fill="url(#g2)" />
      <circle cx="50" cy="48" r="4" fill="url(#g2)" />
      <line x1="14" y1="16" x2="32" y2="32" stroke="url(#g2)" strokeWidth="1.6" opacity="0.7" />
      <line x1="50" y1="16" x2="32" y2="32" stroke="url(#g2)" strokeWidth="1.5" opacity="0.7" />
      <line x1="14" y1="48" x2="32" y2="32" stroke="url(#g2)" strokeWidth="1.5" opacity="0.7" />
      <line x1="50" y1="48" x2="32" y2="32" stroke="url(#g2)" strokeWidth="1.5" opacity="0.7" />
      <defs>
        <linearGradient id="g2" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#7C5CFF" />
          <stop offset="55%" stopColor="#4F7CFF" />
          <stop offset="100%" stopColor="#22D3EE" />
        </linearGradient>
      </defs>
    </svg>
  )
}

/* ---------- Animated counter ---------- */
function Counter({ target, suffix = '', duration = 1600 }) {
  const [val, setVal] = useState(0)
  const ref = useRef(null)
  const started = useRef(false)

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true
          const t0 = performance.now()
          const tick = (t) => {
            const p = Math.min((t - t0) / duration, 1)
            const eased = 1 - Math.pow(1 - p, 3)
            setVal(Math.round(target * eased))
            if (p < 1) requestAnimationFrame(tick)
          }
          requestAnimationFrame(tick)
        }
      },
      { threshold: 0.4 }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [target, duration])

  return <span ref={ref}>{val.toLocaleString()}{suffix}</span>
}

/* ---------- Generic agent pipeline visual (use-case agnostic) ---------- */
function PipelineVisual() {
  const stages = [
    { id: 'A1', label: 'Capture', icon: '⬇', color: '#22d3ee' },
    { id: 'A2', label: 'Harmonize', icon: '⇄', color: '#7c5cff' },
    { id: 'A3', label: 'Match', icon: '⧉', color: '#a78bfa' },
    { id: 'A4', label: 'Validate', icon: '✓', color: '#34d399' },
    { id: 'A5', label: 'Explain', icon: '✦', color: '#fbbf24' },
    { id: 'A6', label: 'Coordinate', icon: '◈', color: '#f87171' },
  ]

  return (
    <div className="flow-visual anim-scale-in anim-delay-3">
      <div className="flow-head">
        <span className="status-dot ok" />
        <span>Agent pipeline · live</span>
        <span className="flow-run">any workflow</span>
      </div>
      <div className="flow-track">
        {stages.map((s, i) => (
          <div key={s.id} className="flow-stage" style={{ animationDelay: `${i * 0.12}s` }}>
            <div className="flow-node" style={{ '--node-color': s.color }}>
              <span className="flow-icon">{s.icon}</span>
              <span className="flow-id">{s.id}</span>
              <span className="flow-label">{s.label}</span>
            </div>
            {i < stages.length - 1 && (
              <div className="flow-connector">
                <div className="flow-line" />
                <div className="flow-particle" style={{ animationDelay: `${i * 0.12 + 0.2}s` }} />
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="flow-foot">
        <div className="flow-bar"><span style={{ '--w': '100%' }} /></div>
        <span>6 agents active · any finance workflow</span>
      </div>
    </div>
  )
}

/* ---------- Landing page ---------- */
export default function Landing() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="landing">
      <Constellation />
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      {/* ---------- Nav ---------- */}
      <header className={`nav ${scrolled ? 'nav-scrolled' : ''}`}>
        <div className="nav-inner">
          <a href="/" className="brand anim-fade-in">
            <NexusMark size={32} />
            <span>NEXUS <small>2.0</small></span>
          </a>
          <nav className="nav-links anim-fade-in anim-delay-1">
            <a href="#agents">The Agents</a>
            <a href="#how">How it works</a>
            <a href="#trust">Trust</a>
          </nav>
          <div className="nav-cta anim-fade-in anim-delay-2">
            <a href="#how" className="btn btn-ghost">How it works</a>
            <Link to="/signin" className="btn btn-gold">Launch Workspace</Link>
          </div>
        </div>
      </header>

      {/* ---------- Hero ---------- */}
      <section className="hero">
        <div className="hero-copy">
          <span className="chip anim-fade-up">◆ Nexus 2.0 · Finance Operations Agent Platform</span>
          <h1 className="anim-fade-up anim-delay-1">
            One platform.<br />
            <em className="grad-text">Every finance process. Intelligent agents.</em>
          </h1>
          <p className="anim-fade-up anim-delay-2">
            Define any finance workflow in natural language — Nexus autonomously assembles the optimal agent constellation,
            ingests your data, applies governed rules, and maintains human oversight.
            From record-to-report to procure-to-pay to order-to-cash, a single platform orchestrates it all.
          </p>
          <div className="hero-actions anim-fade-up anim-delay-3">
            <Link to="/signin" className="btn btn-gold">
              Enter the Platform
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </Link>
            <a href="#how" className="btn btn-ghost">See how it works</a>
          </div>
          <div className="hero-stats anim-fade-up anim-delay-4">
            <div className="hero-stat-highlight">
              <strong><Counter target={50} suffix="+" /></strong>
              <span>use cases, one platform</span>
            </div>
            <div><strong>100%</strong><span>every number explained</span></div>
          </div>
        </div>

        <div className="hero-visual">
          <PipelineVisual />
          <div className="hero-glow" />
        </div>
      </section>

      {/* ---------- Ticker ---------- */}
      <div className="ticker-wrap anim-fade-in anim-delay-5">
        <div className="ticker">
          {[...Array(2)].map((_, k) => (
            <div className="ticker-half" key={k}>
              {['R2R', 'P2P', 'O2C', 'SAP', 'Excel', 'CSV', 'PDF', 'Rule Engine', 'Calculation Engine', 'Audit Lineage', 'Human Review', 'Master Data'].map((t) => (
                <span key={t + k}>{t}<i>◆</i></span>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* ---------- Domain coverage ---------- */}
      <section className="section">
        <span className="chip anim-fade-up">Built for all of finance</span>
        <h2 className="section-title anim-fade-up anim-delay-1">
          Your processes. <span className="grad-text">Your rules. Any domain.</span>
        </h2>
        <p className="section-sub anim-fade-up anim-delay-2">
          Nexus doesn't ship with fixed use cases. You bring the process — the platform brings the agents.
        </p>
        <div className="how-grid">
          {[
            ['R2R', 'Record to Report', 'Close faster with automated comparisons, certifications and evidence-backed reporting.'],
            ['P2P', 'Procure to Pay', 'From invoice capture to payment approval — matched, validated and explained.'],
            ['O2C', 'Order to Cash', 'Receipts, deductions and customer balances reconciled without the spreadsheet marathon.'],
          ].map(([tag, title, desc], i) => (
            <div key={tag} className={`lux-card how-card anim-fade-up anim-delay-${i + 1}`}>
              <span className="how-num" style={{ fontSize: '0.85rem', letterSpacing: '0.1em' }}>{tag}</span>
              <h3>{title}</h3>
              <p>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- How it works ---------- */}
      <section id="how" className="section section-alt">
        <span className="chip anim-fade-up">How it works</span>
        <h2 className="section-title anim-fade-up anim-delay-1">
          Describe the job. <span className="grad-text">The agents do it.</span>
        </h2>
        <p className="section-sub anim-fade-up anim-delay-2">
          No new software per task. Define your requirements in natural language — Nexus constructs the workflow from a library of reusable agents.
        </p>
        <div className="how-grid">
          {[
            ['1', 'Describe', 'Type what you need — in your words, for your process.'],
            ['2', 'Nexus suggests', 'The AI proposes a workflow and shows which agents it will use.'],
            ['3', 'You configure', 'Pick your data, rules and tolerances. Test with sample data.'],
            ['4', 'Approve & run', 'A controller approves. The workflow runs — every decision audited.'],
          ].map(([n, t, d], i) => (
            <div key={n} className={`lux-card how-card anim-fade-up anim-delay-${i + 1}`}>
              <span className="how-num">{n}</span>
              <h3>{t}</h3>
              <p>{d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- Agents explained ---------- */}
      <section id="agents" className="section section-alt">
        <span className="chip anim-fade-up">Meet the team</span>
        <h2 className="section-title anim-fade-up anim-delay-1">
          Core agents. <span className="grad-text">Infinite workflows.</span>
        </h2>
        <p className="section-sub anim-fade-up anim-delay-2">
          A growing library of specialist agents powers every use case — only the configuration changes.
        </p>
        <div className="agent-grid">
          {AGENTS.map((a, i) => (
            <div key={a.id} className={`lux-card agent-card anim-fade-up anim-delay-${(i % 3) + 1} ${a.status === 'dev' ? 'agent-card-disabled' : ''}`}>
              <div className="agent-card-top">
                <span className="agent-emoji">{a.icon}</span>
                <span className="agent-badge">{a.id}</span>
                {a.status === 'dev' && <span className="agent-soon">Coming soon</span>}
              </div>
              <h3>{a.name}</h3>
              <p className="agent-tagline">{a.tagline}</p>
              <p className="agent-simple">{a.simple}</p>
              <div className="agent-chips">
                {a.reads.slice(0, 3).map((r) => <span key={r}>{r}</span>)}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- Trust ---------- */}
      <section id="trust" className="section section-alt trust">
        <div className="trust-inner">
          <span className="chip anim-fade-up">Trust by design</span>
          <h2 className="section-title anim-fade-up anim-delay-1">
            AI drafts it.<br />
            <span className="grad-text">Only approved configuration runs.</span>
          </h2>
          <div className="trust-flow anim-fade-up anim-delay-2">
            {['You describe', 'Nexus drafts', 'You test', 'Controller approves', 'It runs'].map((s, i) => (
              <div key={s} className="trust-step" style={{ animationDelay: `${i * 0.15}s` }}>
                <span className="trust-dot" />
                <span>{s}</span>
              </div>
            ))}
          </div>
          <blockquote className="anim-fade-up anim-delay-3">
            "Nothing posts automatically. A human reviews every exception — and every decision is recorded forever."
          </blockquote>
        </div>
      </section>

      {/* ---------- CTA ---------- */}
      <section className="cta">
        <div className="cta-card lux-card anim-scale-in">
          <h2>Whatever finance throws at you, <span className="grad-text">Nexus runs it.</span></h2>
          <p>Sign in and explore the workspace — configure your first workflow in minutes.</p>
          <Link to="/signin" className="btn btn-gold">Open the Workspace</Link>
        </div>
      </section>

      {/* ---------- Footer ---------- */}
      <footer className="footer">
        <hr className="hairline" />
        <div className="footer-inner">
          <div className="brand">
            <NexusMark size={22} />
            <span>NEXUS 2.0</span>
          </div>
          <p>Finance Operations Agent Platform · On-premises first · SAP read-only</p>
          <p className="footer-fine">© 2026 Nexus Systems. Every decision audited.</p>
        </div>
      </footer>
    </div>
  )
}