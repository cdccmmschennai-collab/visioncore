import {
  createContext, useCallback, useContext, useEffect, useMemo, useRef, useState,
  type ReactNode,
} from 'react'
import { ACTIVITY_EVENT, api, AUTH_EXPIRED_EVENT, tokenStore } from '@/api/client'
import type { User } from '@/api/types'

interface AuthValue {
  user: User | null
  loading: boolean
  isAdmin: boolean
  signIn: (username: string, password: string, remember: boolean) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthValue | null>(null)
const REMEMBERED_USER = 'visioncore.remembered'

// Auto-logout after this long with no mouse/keyboard/API activity.
const IDLE_LIMIT_MS = 15 * 60 * 1000
// Coalesce high-frequency events (mousemove) so we touch localStorage/timers at most this often.
const ACTIVITY_THROTTLE_MS = 1000
// Last-activity timestamp, shared across tabs and survives a page refresh.
const LAST_ACTIVITY_KEY = 'visioncore.lastActivity'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const idleTimerRef = useRef<number | null>(null)
  const lastActivityRef = useRef<number>(Date.now())

  const clearIdleTimer = useCallback(() => {
    if (idleTimerRef.current !== null) {
      window.clearTimeout(idleTimerRef.current)
      idleTimerRef.current = null
    }
  }, [])

  const signOut = useCallback(() => {
    clearIdleTimer()
    tokenStore.clear()
    localStorage.removeItem(LAST_ACTIVITY_KEY)
    setUser(null)
  }, [clearIdleTimer])

  // (Re)arm the single idle timer — never let more than one run at once.
  const armIdleTimer = useCallback((delay: number) => {
    clearIdleTimer()
    idleTimerRef.current = window.setTimeout(signOut, delay)
  }, [clearIdleTimer, signOut])

  const recordActivity = useCallback(() => {
    const now = Date.now()
    if (now - lastActivityRef.current < ACTIVITY_THROTTLE_MS) return
    lastActivityRef.current = now
    localStorage.setItem(LAST_ACTIVITY_KEY, String(now))
    armIdleTimer(IDLE_LIMIT_MS)
  }, [armIdleTimer])

  // Restore the session on reload if a stored token is still good — unless the
  // user had already been idle past the limit before the refresh happened.
  useEffect(() => {
    let cancelled = false
    async function restore() {
      if (!tokenStore.access) {
        setLoading(false)
        return
      }
      const storedActivityRaw = localStorage.getItem(LAST_ACTIVITY_KEY)
      const storedActivity = storedActivityRaw ? Number(storedActivityRaw) : 0
      // No provable recent activity (or too old) — never trust a bare token.
      if (!storedActivity || Date.now() - storedActivity >= IDLE_LIMIT_MS) {
        tokenStore.clear()
        localStorage.removeItem(LAST_ACTIVITY_KEY)
        setLoading(false)
        return
      }
      try {
        const me = await api.me()
        if (!cancelled) setUser(me)
      } catch {
        tokenStore.clear()
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void restore()
    return () => { cancelled = true }
  }, [])

  // The client dispatches this when a refresh fails mid-session.
  useEffect(() => {
    window.addEventListener(AUTH_EXPIRED_EVENT, signOut)
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, signOut)
  }, [signOut])

  // Idle-logout: only active while signed in; a single timer, reset by activity.
  useEffect(() => {
    if (!user) return

    const storedActivity = Number(localStorage.getItem(LAST_ACTIVITY_KEY)) || Date.now()
    const elapsed = Date.now() - storedActivity
    if (elapsed >= IDLE_LIMIT_MS) {
      signOut()
      return
    }
    lastActivityRef.current = storedActivity
    armIdleTimer(IDLE_LIMIT_MS - elapsed)

    const activityEvents = ['mousemove', 'mousedown', 'keydown', 'wheel', 'touchstart'] as const
    activityEvents.forEach((evt) => window.addEventListener(evt, recordActivity, { passive: true }))
    window.addEventListener(ACTIVITY_EVENT, recordActivity)

    // Background tabs throttle setTimeout, so re-check elapsed time on refocus.
    const onVisible = () => {
      if (document.visibilityState !== 'visible') return
      const idleFor = Date.now() - lastActivityRef.current
      if (idleFor >= IDLE_LIMIT_MS) signOut()
      else armIdleTimer(IDLE_LIMIT_MS - idleFor)
    }
    document.addEventListener('visibilitychange', onVisible)

    // Cross-tab sync: activity (or a logout) in one tab must be honored in others.
    const onStorage = (event: StorageEvent) => {
      if (event.key !== LAST_ACTIVITY_KEY) return
      if (!event.newValue) { signOut(); return }
      const ts = Number(event.newValue)
      if (ts <= lastActivityRef.current) return
      lastActivityRef.current = ts
      const idleFor = Date.now() - ts
      if (idleFor >= IDLE_LIMIT_MS) signOut()
      else armIdleTimer(IDLE_LIMIT_MS - idleFor)
    }
    window.addEventListener('storage', onStorage)

    return () => {
      activityEvents.forEach((evt) => window.removeEventListener(evt, recordActivity))
      window.removeEventListener(ACTIVITY_EVENT, recordActivity)
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('storage', onStorage)
      clearIdleTimer()
    }
  }, [user, recordActivity, armIdleTimer, clearIdleTimer, signOut])

  const signIn = useCallback(
    async (username: string, password: string, remember: boolean) => {
      const data = await api.login(username, password, remember)
      tokenStore.set(data.access_token, data.refresh_token)
      localStorage.setItem(LAST_ACTIVITY_KEY, String(Date.now()))
      // "Remember me" recalls the username only — never the password.
      if (remember) localStorage.setItem(REMEMBERED_USER, username)
      else localStorage.removeItem(REMEMBERED_USER)
      setUser(data.user)
    },
    [],
  )

  const value = useMemo<AuthValue>(
    () => ({ user, loading, isAdmin: user?.role === 'admin', signIn, signOut }),
    [user, loading, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}

export function rememberedUsername(): string {
  return localStorage.getItem(REMEMBERED_USER) ?? ''
}
