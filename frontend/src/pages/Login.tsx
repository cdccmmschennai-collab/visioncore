import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import Logo from '@/components/Logo'
import Spinner from '@/components/Spinner'
import { COMPANY_NAME } from '@/config'
import { rememberedUsername, useAuth } from '@/store/AuthContext'
import '@/styles/login.css'

export default function Login() {
  const { user, signIn, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: string } }

  const remembered = rememberedUsername()
  const [username, setUsername] = useState(remembered)
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [remember, setRemember] = useState(Boolean(remembered))
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (!loading && user) return <Navigate to={location.state?.from ?? '/'} replace />

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await signIn(username.trim(), password, remember)
      navigate(location.state?.from ?? '/', { replace: true })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not sign you in.')
      setPassword('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page login-hero">
      <div className="login-card login-card-solo">
        <div className="login-form-side">
          <div className="login-brand">
            <Logo size={60} showName={false} />
            <div className="stack">
              <span className="login-company">{COMPANY_NAME}</span>
              <span className="eyebrow">Asset Data Systems</span>
            </div>
          </div>

          <div className="login-welcome">
            <h1>Welcome Back</h1>
            <p className="login-welcome-sub">Sign in to continue to your account</p>
          </div>

          <form onSubmit={submit} className="stack gap-16" noValidate>
            <div className="field">
              <label htmlFor="username">Username</label>
              <div className="field-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M20 21a8 8 0 0 0-16 0" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <input
                  id="username"
                  className="input"
                  value={username}
                  autoComplete="username"
                  autoFocus={!remembered}
                  required
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="Enter your username"
                />
              </div>
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
              <div className="password-field field-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="3" y="11" width="18" height="10" rx="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className="input"
                  value={password}
                  autoComplete="current-password"
                  autoFocus={Boolean(remembered)}
                  required
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword((show) => !show)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a21.8 21.8 0 0 1 5.06-6.06M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a21.8 21.8 0 0 1-3.22 4.44M14.12 14.12a3 3 0 1 1-4.24-4.24" />
                      <path d="M1 1l22 22" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {error && (
              <div className="alert alert-error" role="alert">
                <span aria-hidden="true">!</span>
                <span>{error}</span>
              </div>
            )}

            <label className="checkbox">
              <input
                type="checkbox"
                checked={remember}
                onChange={(event) => setRemember(event.target.checked)}
              />
              Remember me
            </label>

            <button
              type="submit"
              className="btn btn-primary btn-block login-submit"
              disabled={busy || !username.trim() || !password}
            >
              {busy ? <Spinner size={15} /> : null}
              {busy ? 'Signing in…' : 'Login'}
            </button>
          </form>

          <div className="login-secure">
            <span className="login-secure-icon" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="10" rx="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </span>
            <div className="stack gap-4">
              <span className="login-secure-title">Secure Access</span>
              <span className="login-secure-sub">Your data is encrypted and protected</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
