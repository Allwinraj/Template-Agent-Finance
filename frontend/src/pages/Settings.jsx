import { useState } from 'react'
import './Settings.css'

const TABS = ['Profile', 'Platform', 'Audit Policy', 'Notifications']

export default function Settings() {
  const [tab, setTab] = useState(TABS[0])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p>Platform preferences will live here</p>
        </div>
      </div>

      <div className="set-tabs anim-fade-up">
        {TABS.map((t) => (
          <button key={t} className={`set-tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      <div className="lux-card set-shell anim-fade-up anim-delay-1">
        <span className="set-gear anim-float">⚙</span>
        <h3>{tab}</h3>
        <p>Settings for this section are coming soon. The layout is ready — connect the backend to bring it to life.</p>
        <span className="chip">placeholder</span>
      </div>
    </div>
  )
}