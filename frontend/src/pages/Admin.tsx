import { useCallback, useEffect, useState, type FormEvent } from 'react'
import Modal from '@/components/Modal'
import Spinner from '@/components/Spinner'
import { api } from '@/api/client'
import type { AdminStats, UsageSummary, User } from '@/api/types'
import { formatNumber } from '@/utils/filename'
import { useAuth } from '@/store/AuthContext'
import { useToast } from '@/store/ToastContext'

type Tab = 'usage' | 'users'

export default function Admin() {
  const { user: me } = useAuth()
  const toast = useToast()
  const [tab, setTab] = useState<Tab>('usage')

  const [usage, setUsage] = useState<UsageSummary | null>(null)
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)

  const [createOpen, setCreateOpen] = useState(false)
  const [resetFor, setResetFor] = useState<User | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [usageData, statsData, userList] = await Promise.all([
        api.usage(30), api.stats(), api.listUsers(),
      ])
      setUsage(usageData); setStats(statsData); setUsers(userList)
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not load admin data.')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { void load() }, [load])

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

      {tab === 'usage' && usage && stats && (
        <div className="stack gap-24">
          <div className="stat-grid">
            <Stat label="Tags extracted" value={formatNumber(stats.total_tags)} />
            <Stat label="Batches" value={formatNumber(stats.total_batches)} />
            <Stat label="Downloads" value={formatNumber(stats.total_downloads)} />
            <Stat label="Active users" value={`${stats.active_users} / ${stats.total_users}`} />
          </div>

          <section className="card stack gap-16">
            <div className="card-head" style={{ marginBottom: 0 }}>
              <div className="stack gap-4">
                <h3>Claude API spend</h3>
                <span className="muted">
                  Model <code>{usage.model}</code> · measured from recorded calls at
                  ${usage.input_price_per_mtok}/M in, ${usage.output_price_per_mtok}/M out
                </span>
              </div>
              <button type="button" className="btn btn-sm" onClick={() => void load()}>
                Refresh
              </button>
            </div>

            <div className="budget">
              <div className="budget-bar">
                <div
                  className={`budget-fill${usage.percent_used > 85 ? ' budget-high' : ''}`}
                  style={{ width: `${Math.min(100, usage.percent_used)}%` }}
                />
              </div>
              <div className="budget-legend">
                <span>
                  <strong>${usage.total_cost_usd.toFixed(4)}</strong> spent
                </span>
                <span className="muted">
                  ${usage.remaining_usd.toFixed(2)} of ${usage.credit_budget_usd.toFixed(2)} remaining
                  {' '}({usage.percent_used}% used)
                </span>
              </div>
            </div>

            <div className="alert alert-info">
              <span aria-hidden="true">i</span>
              <span>
                Anthropic doesn't publish a live account-balance endpoint, so this figure is
                spend <em>measured</em> from each API response and priced with the rates in
                your <code>.env</code> — not a balance read back from the account. Update
                <code> CLAUDE_CREDIT_BUDGET_USD</code> when you top up.
              </span>
            </div>

            <div className="stat-grid">
              <Stat label="Total calls" value={formatNumber(usage.total_calls)} />
              <Stat label="Failed calls" value={formatNumber(usage.failed_calls)}
                    tone={usage.failed_calls > 0 ? 'danger' : undefined} />
              <Stat label="Input tokens" value={formatNumber(usage.input_tokens)} />
              <Stat label="Output tokens" value={formatNumber(usage.output_tokens)} />
              <Stat label="Avg latency" value={`${(usage.avg_latency_ms / 1000).toFixed(1)}s`} />
              <Stat label="Total tokens" value={formatNumber(usage.total_tokens)} />
            </div>

            {usage.daily.length > 0 && (
              <div className="stack gap-8">
                <span className="eyebrow">Last 30 days</span>
                <div className="spark" role="img" aria-label="Daily API cost">
                  {(() => {
                    const peak = Math.max(...usage.daily.map((d) => d.cost_usd), 0.000001)
                    return usage.daily.map((day) => (
                      <span
                        key={day.day}
                        className="spark-bar"
                        style={{ height: `${Math.max(4, (day.cost_usd / peak) * 100)}%` }}
                        title={`${new Date(day.day).toLocaleDateString()} — ${day.calls} call(s), $${day.cost_usd.toFixed(4)}`}
                      />
                    ))
                  })()}
                </div>
              </div>
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

function Stat({ label, value, tone }: { label: string; value: string; tone?: 'danger' }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className={`stat-value${tone === 'danger' ? ' stat-danger' : ''}`}>{value}</span>
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
