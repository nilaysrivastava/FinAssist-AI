import { useEffect, useState } from 'react'
import { clearToken, getToken, me } from './api'
import type { User } from './types'
import AuthPage from './components/AuthPage'
import ChatPage from './components/ChatPage'

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function boot() {
      const token = getToken()
      if (!token) {
        setLoading(false)
        return
      }
      try {
        const current = await me()
        setUser(current)
      } catch {
        clearToken()
      } finally {
        setLoading(false)
      }
    }
    boot()
  }, [])

  if (loading) {
    return <div className="grid min-h-screen place-items-center text-slate-500">Loading secure workspace...</div>
  }

  return user ? <ChatPage user={user} onLogout={() => setUser(null)} /> : <AuthPage onAuth={setUser} />
}
