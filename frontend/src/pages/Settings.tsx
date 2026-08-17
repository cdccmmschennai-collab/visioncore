import { useState, type FormEvent } from 'react'
import Spinner from '@/components/Spinner'
import { api } from '@/api/client'
import { useAuth } from '@/store/AuthContext'
import { useTheme } from '@/store/ThemeContext'
import { useToast } from '@/store/ToastContext'

export default function Settings() {
  const { user } = useAuth()
  const { theme, setTheme } = useTheme()
  const toast = useToast()

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)

  const mismatch = confirm.length > 0 && next !== confirm
  const tooShort = next.length > 0 && next.length < 8
  const canSubmit = current && next.length >= 8 && next === confirm && !busy

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    try {
      const result = await api.changePassword(current, next)
      toast.success(result.message)
      setCurrent(''); setNext(''); setConfirm('')
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not update your password.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page stack gap-24">
      <header className="page-head">
        <div className="stack gap-4">
          <span className="eyebrow">Your account</span>
          <h1>Settings</h1>
        </div>
      </header>

      <div className="settings-grid">
        {/* ── Reset password ───────────────────────────────────────────── */}
        <section className="card stack gap-16">
          <div className="stack gap-4">
            <h3>Reset password</h3>
            <p className="muted" style={{ margin: 0 }}>
              Signed in as <strong>{user?.username}</strong>. Use at least 8 characters.
            </p>
          </div>

          <form onSubmit={submit} className="stack gap-16">
            <div className="field">
              <label htmlFor="current">Current password</label>
              <input
                id="current"
                type="password"
                className="input"
                value={current}
                autoComplete="current-password"
                onChange={(event) => setCurrent(event.target.value)}
              />
            </div>

            <div className="field">
              <label htmlFor="next">New password</label>
              <input
                id="next"
                type="password"
                className="input"
                value={next}
                autoComplete="new-password"
                onChange={(event) => setNext(event.target.value)}
                aria-describedby={tooShort ? 'next-hint' : undefined}
              />
              {tooShort && (
                <span id="next-hint" className="field-error">
                  Needs at least 8 characters.
                </span>
              )}
            </div>

            <div className="field">
              <label htmlFor="confirm">Confirm new password</label>
              <input
                id="confirm"
                type="password"
                className="input"
                value={confirm}
                autoComplete="new-password"
                onChange={(event) => setConfirm(event.target.value)}
                aria-describedby={mismatch ? 'confirm-hint' : undefined}
              />
              {mismatch && (
                <span id="confirm-hint" className="field-error">
                  These two don't match.
                </span>
              )}
            </div>

            <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
              {busy ? <Spinner size={14} /> : null}
              {busy ? 'Updating…' : 'Update password'}
            </button>
          </form>
        </section>

        {/* ── Appearance ───────────────────────────────────────────────── */}
        <section className="card stack gap-16">
          <div className="stack gap-4">
            <h3>Appearance</h3>
            <p className="muted" style={{ margin: 0 }}>
              Applies to this browser and is remembered next time you sign in.
            </p>
          </div>

          <div className="theme-picker" role="radiogroup" aria-label="Colour theme">
            {(['dark', 'light'] as const).map((option) => (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={theme === option}
                className={`theme-option${theme === option ? ' theme-selected' : ''}`}
                onClick={() => setTheme(option)}
              >
                <span className={`theme-swatch theme-swatch-${option}`} aria-hidden="true">
                  <span /><span /><span />
                </span>
                <span className="theme-label">{option === 'dark' ? 'Dark' : 'Light'}</span>
              </button>
            ))}
          </div>

          <dl className="meta-list">
            <div><dt>Role</dt><dd>{user?.role}</dd></div>
            <div><dt>Email</dt><dd>{user?.email ?? '—'}</dd></div>
            <div>
              <dt>Last sign-in</dt>
              <dd>
                {user?.last_login_at
                  ? new Date(user.last_login_at).toLocaleString()
                  : '—'}
              </dd>
            </div>
          </dl>
        </section>
      </div>
    </div>
  )
}
