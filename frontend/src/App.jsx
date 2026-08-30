import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Landing from './pages/Landing.jsx'
import SignIn from './pages/SignIn.jsx'
import Dashboard from './pages/Dashboard.jsx'

export default function App() {
  // Hardcoded auth — replace with real backend later
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem('aurum_user')) || null
    } catch {
      return null
    }
  })

  const signIn = (mockUser) => {
    sessionStorage.setItem('aurum_user', JSON.stringify(mockUser))
    setUser(mockUser)
  }

  const signOut = () => {
    sessionStorage.removeItem('aurum_user')
    setUser(null)
  }

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signin" element={<SignIn onSignIn={signIn} />} />
      <Route
        path="/app/*"
        element={user ? <Dashboard user={user} onSignOut={signOut} /> : <Navigate to="/signin" replace />}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}