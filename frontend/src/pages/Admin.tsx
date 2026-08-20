import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import Modal from '@/components/Modal'
import Spinner from '@/components/Spinner'
import { api } from '@/api/client'
import type { AdminStats, ClaudeUsageSummary, OrgCredits, User } from '@/api/types'
import { formatNumber } from '@/utils/filename'
import { useAuth } from '@/store/AuthContext'
import { useToast } from '@/store/ToastContext'

type Tab = 'usage' | 'users'

//: How often the Claude usage card re-fetches from the backend in the
//: background, in addition to the manual Refresh button.
const USAGE_REFRESH_INTERVAL_MS = 60_000

const NOT_AVAILABLE_TEXT = "Not available from Anthropic's official API."

export default function Admin() {
  const { user: me } = useAuth()
  const toast = useToast()
  const [tab, setTab] = useState<Tab>('usage')

  const [stats, setStats] = useState<AdminStats | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)

  // Claude usage has its own load lifecycle — separate from stats/users —
  // so it can auto-refresh and show its own loading/error states without
  // affecting the rest of the Admin page.
  const [usage, setUsage] = useState<ClaudeUsageSummary | null>(null)
  const [usageLoading, setUsageLoading] = useState(true)
  const [usageFetchError, setUsageFetchError] = useState<string | null>(null)

  // Organization Credits — a value an admin manually entered from the
  // Claude Console (Anthropic's official API has no balance endpoint for
  // this org type), stored in the database and editable right on the card.
  const [orgCredits, setOrgCredits] = useState<OrgCredits | null>(null)
  const [orgCreditsLoading, setOrgCreditsLoading] = useState(true)
  const [orgCreditsError, setOrgCreditsError] = useState<string | null>(null)
  const [orgCreditsInput, setOrgCreditsInput] = useState('')
  const [orgCreditsSaving, setOrgCreditsSaving] = useState(false)
  const orgCreditsInputTouched = useRef(false)

  const [createOpen, setCreateOpen] = useState(false)
  const [resetFor, setResetFor] = useState<User | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [statsData, userList] = await Promise.all([api.stats(), api.listUsers()])
      setStats(statsData); setUsers(userList)
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not load admin data.')
    } finally {
      setLoading(false)
    }
  }, [toast])

  const loadUsage = useCallback(async () => {
    setUsageLoading(true)
    try {
      const data = await api.usage(30)
      setUsage(data)
      setUsageFetchError(null)
    } catch (caught) {
      setUsageFetchError(caught instanceof Error ? caught.message : 'Could not reach the backend.')
    } finally {
      setUsageLoading(false)
    }
  }, [])

  const loadOrgCredits = useCallback(async () => {
    setOrgCreditsLoading(true)
    try {
      const data = await api.orgCredits()
      setOrgCredits(data)
      setOrgCreditsError(null)
      // Only prefill the edit box from the very first successful load —
      // background refreshes shouldn't clobber an in-progress edit.
      if (!orgCreditsInputTouched.current) {
        setOrgCreditsInput(data.amount_usd != null ? String(data.amount_usd) : '')
      }
    } catch (caught) {
      setOrgCreditsError(caught instanceof Error ? caught.message : 'Could not reach the backend.')
    } finally {
      setOrgCreditsLoading(false)
    }
  }, [])

  const submitOrgCredits = async (event: FormEvent) => {
    event.preventDefault()
    const parsed = Number(orgCreditsInput)
    if (!Number.isFinite(parsed) || parsed < 0) {
      toast.error('Enter a valid, non-negative USD amount.')
      return
    }
    setOrgCreditsSaving(true)
    try {
      const data = await api.setOrgCredits(parsed)
      setOrgCredits(data)
      orgCreditsInputTouched.current = false
      toast.success('Organization credits updated.')
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not update organization credits.')
    } finally {
      setOrgCreditsSaving(false)
    }
  }

  useEffect(() => { void load() }, [load])

  useEffect(() => {
    void loadUsage()
    void loadOrgCredits()
    const id = setInterval(() => {
      void loadUsage(); void loadOrgCredits()
    }, USAGE_REFRESH_INTERVAL_MS)
    return () => clearInterval(id)
  }, [loadUsage, loadOrgCredits])

  const toggleActive = async (target: User) => {
    try {
      const updated = await api.updateUser(target.id, { is_active: !target.is_active })
      setUsers((list) => list.map((u) => (u.id === updated.id ? updated : u)))
      toast.success(`${updated.username} ${updated.is_active ? 'enabled' : 'disabled'}.`)
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not update that user.')
    }
  }

  const changeRole = async (target: User, role: 'admin' | 'user') => {
    try {
      const updated = await api.updateUser(target.id, { role })
      setUsers((list) => list.map((u) => (u.id === updated.id ? updated : u)))
      toast.success(`${updated.username} is now ${role}.`)
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not change that role.')
    }
  }

  if (loading) {
    return (
      <div className="page">
        <div className="card"><Spinner size={24} label="Loading admin data…" /></div>
      </div>
    )
  }

  return (
    <div className="page stack gap-24">
      <header className="page-head">
        <div className="stack gap-4">
          <span className="eyebrow">Administration</span>
          <h1>Admin</h1>
        </div>
        <div className="tabs" role="tablist">
          {(['usage', 'users'] as const).map((option) => (
            <button
              key={option}
              type="button"
              role="tab"
              aria-selected={tab === option}
              className={`tab${tab === option ? ' tab-active' : ''}`}
              onClick={() => setTab(option)}
            >
              {option === 'usage' ? 'Claude usage' : 'Users'}
            </button>
          ))}
        </div>
      </header>

      {tab === 'usage' && stats && (
        <div className="stack gap-24">
          {usage?.available && usage.spend_warning_triggered && (
            <div className="alert alert-warn" role="alert">
              <span aria-hidden="true">⚠️</span>
              <span>
                <strong>Claude API usage is approaching the configured spending limit.</strong>
                {' '}Current usage: <strong>${usage.total_cost_usd.toFixed(2)}</strong>
                {' '}(≈ ₹{usage.total_cost_inr.toFixed(2)}, converted at ₹{usage.usd_to_inr_rate}/$)
                {' '}— threshold is ${usage.spend_warning_threshold_usd.toFixed(2)}, from Anthropic's
                official cost report. Adjust <code>CLAUDE_SPEND_WARNING_USD</code> in the backend
                {' '}<code>.env</code> to change this.
              </span>
            </div>
          )}

          <div className="stat-grid">
            <Stat label="Tags extracted" value={formatNumber(stats.total_tags)} />
            <Stat label="Batches" value={formatNumber(stats.total_batches)} />
            <Stat label="Downloads" value={formatNumber(stats.total_downloads)} />
            <Stat label="Active users" value={`${stats.active_users} / ${stats.total_users}`} />
          </div>

          <section className="card stack gap-16">
            <div className="card-head" style={{ marginBottom: 0 }}>
              <div className="stack gap-4">
                <h3>Claude API Usage</h3>
                <span className="muted">
                  Straight from Anthropic's official Usage &amp; Cost Admin API — no locally
                  estimated figures.
                  {usage?.available && (
                    <> Model <code>{usage.configured_model}</code> · last {usage.window_days} days</>
                  )}
                  {usage && (
                    <> · updated {new Date(usage.generated_at).toLocaleTimeString()}</>
                  )}
                </span>
              </div>
              <button type="button" className="btn btn-sm" onClick={() => void loadUsage()} disabled={usageLoading}>
                {usageLoading ? <Spinner size={14} /> : null}
                {usageLoading ? 'Refreshing…' : 'Refresh'}
              </button>
            </div>

            {usageLoading && !usage && (
              <div className="row gap-8"><Spinner size={20} label="Loading Claude usage…" /></div>
            )}

            {usageFetchError && (
              <div className="alert alert-error">
                <span aria-hidden="true">!</span>
                <span>Could not reach the VisionCore backend: {usageFetchError}</span>
              </div>
            )}

            {usage && !usage.available && (
              <div className="alert alert-error">
                <span aria-hidden="true">!</span>
                <span>
                  Claude usage data is unavailable — {usage.error} Create an Admin API key in
                  the Claude Console (Settings → Admin API keys) and set
                  {' '}<code>ANTHROPIC_ADMIN_API_KEY</code> in the backend <code>.env</code>, then refresh.
                </span>
              </div>
            )}

            {usage?.available && (
              <>
                <div className="stat-grid">
                  <Stat label="Input tokens" value={formatNumber(usage.input_tokens)} />
                  <Stat label="Output tokens" value={formatNumber(usage.output_tokens)} />
                  <Stat label="Total tokens" value={formatNumber(usage.total_tokens)} />
                  <Stat label="API cost (USD)" value={`$${usage.total_cost_usd.toFixed(4)}`} />
                  <Stat
                    label="API cost (INR)" value={`≈ ₹${usage.total_cost_inr.toFixed(2)}`}
                    hint={`Converted from official USD spend at ₹${usage.usd_to_inr_rate}/$ — not Anthropic data`}
                  />
                  {usage.unavailable_metrics.map((label) => (
                    <Stat key={label} label={label} value={NOT_AVAILABLE_TEXT} small />
                  ))}
                </div>

                {usage.by_model.length > 0 && (
                  <div className="stack gap-8">
                    <span className="eyebrow">Usage by model</span>
                    <div className="table-wrap">
                      <table className="data">
                        <thead>
                          <tr>
                            <th>Model</th>
                            <th>Input tokens</th>
                            <th>Output tokens</th>
                            <th>Total tokens</th>
                          </tr>
                        </thead>
                        <tbody>
                          {usage.by_model.map((m) => (
                            <tr key={m.model}>
                              <td><code>{m.model}</code></td>
                              <td>{formatNumber(m.input_tokens)}</td>
                              <td>{formatNumber(m.output_tokens)}</td>
                              <td>{formatNumber(m.total_tokens)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {usage.daily.length > 0 && (
                  <div className="stack gap-8">
                    <span className="eyebrow">Daily usage &amp; spend — last {usage.window_days} days</span>
                    <span className="muted" style={{ fontSize: 12 }}>
                      The cards above total this same {usage.window_days}-day window (Anthropic's
                      Usage &amp; Cost API reports at most 31 days of daily-granularity history per
                      request, so "monthly" and "last 30 days" are effectively the same view here).
                    </span>
                    <div className="spark" role="img" aria-label="Daily Claude API usage and cost">
                      {(() => {
                        const peak = Math.max(...usage.daily.map((d) => d.cost_usd), 0.000001)
                        return usage.daily.map((day) => (
                          <span
                            key={day.day}
                            className="spark-bar"
                            style={{ height: `${Math.max(4, (day.cost_usd / peak) * 100)}%` }}
                            title={
                              `${new Date(day.day).toLocaleDateString()} — `
                              + `${formatNumber(day.total_tokens)} tokens, $${day.cost_usd.toFixed(4)}`
                            }
                          />
                        ))
                      })()}
                    </div>
                  </div>
                )}

              </>
            )}
          </section>

          <section className="card stack gap-16">
            <div className="card-head" style={{ marginBottom: 0 }}>
              <div className="stack gap-4">
                <h3>Organization Credits</h3>
                <span className="muted">
                  Anthropic's official API has no endpoint for account credit balance on
                  Claude Console/Platform organizations, so this isn't fetched automatically —
                  {' '}<strong>enter what the Claude Console's Billing page shows.</strong>
                </span>
              </div>
              <button
                type="button" className="btn btn-sm"
                onClick={() => void loadOrgCredits()} disabled={orgCreditsLoading}
              >
                {orgCreditsLoading ? <Spinner size={14} /> : null}
                {orgCreditsLoading ? 'Refreshing…' : 'Refresh'}
              </button>
            </div>

            {orgCreditsLoading && !orgCredits && (
              <div className="row gap-8"><Spinner size={20} label="Loading organization credits…" /></div>
            )}

            {orgCreditsError && (
              <div className="alert alert-error">
                <span aria-hidden="true">!</span>
                <span>Could not reach the VisionCore backend: {orgCreditsError}</span>
              </div>
            )}

            {orgCredits && (
              <>
                <div className="stat-grid">
                  <Stat
                    label="Available balance (USD)"
                    value={orgCredits.amount_usd != null ? `$${orgCredits.amount_usd.toFixed(2)}` : 'Not set'}
                  />
                  <Stat
                    label="Available balance (INR)"
                    value={orgCredits.amount_inr != null ? `≈ ₹${orgCredits.amount_inr.toFixed(2)}` : 'Not set'}
                    hint={`Converted at ₹${orgCredits.usd_to_inr_rate}/$ — a display conversion, not Anthropic data`}
                  />
                </div>

                {orgCredits.updated_at && (
                  <span className="muted" style={{ fontSize: 12 }}>
                    Last updated {new Date(orgCredits.updated_at).toLocaleString()}
                  </span>
                )}

                <form onSubmit={submitOrgCredits} className="row gap-8" style={{ alignItems: 'flex-end' }}>
                  <div className="field" style={{ flex: 1, maxWidth: 220 }}>
                    <label htmlFor="org-credits-input">Update from Console (USD)</label>
                    <input
                      id="org-credits-input" type="number" step="0.01" min="0" className="input"
                      value={orgCreditsInput}
                      onChange={(event) => {
                        orgCreditsInputTouched.current = true
                        setOrgCreditsInput(event.target.value)
                      }}
                    />
                  </div>
                  <button type="submit" className="btn btn-primary btn-sm" disabled={orgCreditsSaving}>
                    {orgCreditsSaving ? <Spinner size={14} /> : null}
                    {orgCreditsSaving ? 'Saving…' : 'Save'}
                  </button>
                </form>
              </>
            )}
          </section>

        </div>
      )}

      {tab === 'users' && (
        <section className="stack gap-16">
          <div className="row gap-12">
            <h3>Users</h3>
            <span className="spacer" />
            <button type="button" className="btn btn-primary btn-sm" onClick={() => setCreateOpen(true)}>
              Add user
            </button>
          </div>

          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th style={{ width: 130 }}>Role</th>
                  <th style={{ width: 100 }}>Status</th>
                  <th style={{ width: 210 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((row) => {
                  const isMe = row.id === me?.id
                  return (
                    <tr key={row.id}>
                      <td><strong>{row.username}</strong>{isMe && <span className="chip chip-orange" style={{ marginLeft: 8 }}>You</span>}</td>
                      <td>{row.full_name ?? <span className="muted">—</span>}</td>
                      <td className="muted">{row.email ?? '—'}</td>
                      <td>
                        <select
                          className="select"
                          value={row.role}
                          disabled={isMe}
                          onChange={(event) => changeRole(row, event.target.value as 'admin' | 'user')}
                          aria-label={`Role for ${row.username}`}
                        >
                          <option value="user">User</option>
                          <option value="admin">Admin</option>
                        </select>
                      </td>
                      <td>
                        <span className={`chip ${row.is_active ? 'chip-confirmed' : 'chip-danger'}`}>
                          {row.is_active ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                      <td>
                        <div className="row gap-8">
                          <button type="button" className="btn btn-sm" onClick={() => setResetFor(row)}>
                            Reset password
                          </button>
                          <button
                            type="button"
                            className={`btn btn-sm${row.is_active ? ' btn-danger' : ''}`}
                            disabled={isMe}
                            onClick={() => toggleActive(row)}
                          >
                            {row.is_active ? 'Disable' : 'Enable'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <CreateUserModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(created) => { setUsers((list) => [created, ...list]); setCreateOpen(false) }}
      />
      <ResetPasswordModal user={resetFor} onClose={() => setResetFor(null)} />
    </div>
  )
}

function Stat({
  label, value, tone, hint, small,
}: { label: string; value: string; tone?: 'danger'; hint?: string; small?: boolean }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span
        className={
          `stat-value${tone === 'danger' ? ' stat-danger' : ''}${small ? ' stat-value-sm' : ''}`
        }
      >
        {value}
      </span>
      {hint && <span className="muted" style={{ fontSize: 11.5 }}>{hint}</span>}
    </div>
  )
}

function CreateUserModal({
  open, onClose, onCreated,
}: { open: boolean; onClose: () => void; onCreated: (user: User) => void }) {
  const toast = useToast()
  const [form, setForm] = useState({
    username: '', password: '', full_name: '', email: '', role: 'user' as 'admin' | 'user',
  })
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    try {
      const created = await api.createUser({
        username: form.username.trim(),
        password: form.password,
        full_name: form.full_name.trim() || null,
        email: form.email.trim() || null,
        role: form.role,
      })
      toast.success(`Created ${created.username}.`)
      setForm({ username: '', password: '', full_name: '', email: '', role: 'user' })
      onCreated(created)
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not create that user.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Add user" onClose={onClose}>
      <form onSubmit={submit} className="stack gap-16" id="create-user-form">
        <div className="field">
          <label htmlFor="new-username">Username</label>
          <input
            id="new-username" className="input" required minLength={3}
            value={form.username}
            onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
          />
        </div>
        <div className="field">
          <label htmlFor="new-password">Password</label>
          <input
            id="new-password" type="password" className="input" required minLength={8}
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
          />
        </div>
        <div className="field">
          <label htmlFor="new-fullname">Full name</label>
          <input
            id="new-fullname" className="input"
            value={form.full_name}
            onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
          />
        </div>
        <div className="field">
          <label htmlFor="new-email">Email</label>
          <input
            id="new-email" type="email" className="input"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          />
        </div>
        <div className="field">
          <label htmlFor="new-role">Role</label>
          <select
            id="new-role" className="select" value={form.role}
            onChange={(e) => setForm((f) => ({ ...f, role: e.target.value as 'admin' | 'user' }))}
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div className="row gap-8">
          <span className="spacer" />
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? <Spinner size={14} /> : null}
            {busy ? 'Creating…' : 'Create user'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function ResetPasswordModal({ user, onClose }: { user: User | null; onClose: () => void }) {
  const toast = useToast()
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!user) return
    setBusy(true)
    try {
      const result = await api.resetUserPassword(user.id, password)
      toast.success(result.message)
      setPassword('')
      onClose()
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not reset that password.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={user !== null}
      title={user ? `Reset password — ${user.username}` : 'Reset password'}
      onClose={onClose}
    >
      <form onSubmit={submit} className="stack gap-16">
        <p className="muted" style={{ margin: 0 }}>
          Set a temporary password and share it with {user?.username} over a secure channel.
          They can change it under Settings.
        </p>
        <div className="field">
          <label htmlFor="reset-password">New password</label>
          <input
            id="reset-password" type="password" className="input" required minLength={8}
            value={password} onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <div className="row gap-8">
          <span className="spacer" />
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={busy || password.length < 8}>
            {busy ? <Spinner size={14} /> : null}
            {busy ? 'Resetting…' : 'Reset password'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
