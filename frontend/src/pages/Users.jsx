import { useState } from 'react'
import { USERS, ROLES } from '../data/mockData.js'
import { StatusPill } from './Dashboard.jsx'
import './Users.css'

export default function Users() {
  const [users, setUsers] = useState(USERS)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', role: ROLES[2], entities: '' })

  const addUser = (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.email.trim()) return
    const nu = {
      id: `usr-${Math.floor(Math.random() * 900 + 100)}`,
      ...form,
      entities: form.entities || '1000',
      status: 'invited',
      lastActive: '—',
    }
    setUsers([nu, ...users])
    setForm({ name: '', email: '', role: ROLES[0], entities: '' })
    setShowForm(false)
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Users</h1>
          <p>People who can access this workspace, and what they can see</p>
        </div>
        <button className="btn btn-gold" onClick={() => setShowForm(!showForm)}>
          {showForm ? '✕ Close' : '+ Add User'}
        </button>
      </div>

      {showForm && (
        <form className="lux-card add-user anim-scale-in" onSubmit={addUser}>
          <h3>New user</h3>
          <div className="add-grid">
            <label>
              <span>Full name</span>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Jane Cooper" required />
            </label>
            <label>
              <span>Email</span>
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="jane@company.com" required />
            </label>
            <label>
              <span>Role</span>
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {ROLES.map((r) => <option key={r}>{r}</option>)}
              </select>
            </label>
            <label>
              <span>Company codes (access)</span>
              <input value={form.entities} onChange={(e) => setForm({ ...form, entities: e.target.value })} placeholder="1000, 2000" />
            </label>
          </div>
          <div className="add-actions">
            <button type="submit" className="btn btn-gold">Create user</button>
            <button type="button" className="btn btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      <div className="lux-card anim-fade-up anim-delay-1">
        <table className="lux-table">
          <thead>
            <tr><th>User</th><th>Role</th><th>Company codes</th><th>Status</th><th>Last active</th></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>
                  <div className="user-cell">
                    <span className="u-avatar">{u.name.split(' ').map((p) => p[0]).join('')}</span>
                    <div>
                      <strong>{u.name}</strong>
                      <span className="mono dim">{u.email}</span>
                    </div>
                  </div>
                </td>
                <td><span className="role-tag">{u.role}</span></td>
                <td className="mono">{u.entities}</td>
                <td><StatusPill status={u.status} /></td>
                <td className="mono dim">{u.lastActive}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}