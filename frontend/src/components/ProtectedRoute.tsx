import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import Spinner from './Spinner'
import { useAuth } from '@/store/AuthContext'

interface Props {
  children: ReactNode
  adminOnly?: boolean
}

export default function ProtectedRoute({ children, adminOnly = false }: Props) {
  const { user, loading, isAdmin } = useAuth()

  if (loading) {
    return (
      <div className="route-loading">
        <Spinner size={26} label="Loading your session…" />
      </div>
    )
  }

  // No "return to where you were" state — every login lands on Home,
  // regardless of which page (or which prior user's page) triggered this
  // redirect, so one user's navigation never leaks into the next login.
  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />

  return <>{children}</>
}
