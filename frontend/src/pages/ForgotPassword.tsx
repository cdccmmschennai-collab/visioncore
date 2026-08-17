import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import AuthPoster from '@/components/AuthPoster'
import Logo from '@/components/Logo'
import Spinner from '@/components/Spinner'
import { COMPANY_NAME } from '@/config'
import '@/styles/login.css'

export default function ForgotPassword() {
  const [identifier, setIdentifier] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.forgotPassword(identifier.trim())
      setSent(true)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not send the reset link.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        {/* ── Form side ─────────────────────────────────────────────────── */}
        <div className="login-form-side">
          <div className="login-brand">
            <Logo size={44} showName={false} />
            <div className="stack">
              <span className="login-company">{COMPANY_NAME}</span>
              <span className="eyebrow">Asset Data Systems</span>
            </div>
          </div>

          {sent ? (
            <div className="stack gap-16">
              <div className="alert alert-success" role="status">
                <span aria-hidden="true">✓</span>
                <span>
                  If an account matches <strong>{identifier.trim()}</strong>, a password reset
                  request has been sent. An administrator will follow up shortly.
                </span>
              </div>
              <Link to="/login" className="btn btn-primary btn-block login-submit">
                Back to Login
              </Link>
            </div>
          ) : (
            <form onSubmit={submit} className="stack gap-16" noValidate>
              <p className="muted" style={{ margin: 0 }}>
                Enter your username or email and we&apos;ll send a password reset request.
              </p>

              <div className="field">
                <label htmlFor="identifier">Username or email</label>
                <input
                  id="identifier"
                  className="input"
                  value={identifier}
                  autoComplete="username"
                  autoFocus
                  required
                  onChange={(event) => setIdentifier(event.target.value)}
                  placeholder="Your username or email"
                />
              </div>

              {error && (
                <div className="alert alert-error" role="alert">
                  <span aria-hidden="true">!</span>
                  <span>{error}</span>
                </div>
              )}

              <button
                type="submit"
                className="btn btn-primary btn-block login-submit"
                disabled={busy || !identifier.trim()}
              >
                {busy ? <Spinner size={15} /> : null}
                {busy ? 'Sending…' : 'Send Reset Link'}
              </button>

              <p className="login-foot muted">
                <Link to="/login" className="link-like">Back to Login</Link>
              </p>
            </form>
          )}
        </div>

        {/* ── Poster side ───────────────────────────────────────────────── */}
        <AuthPoster />
      </div>
    </div>
  )
}
