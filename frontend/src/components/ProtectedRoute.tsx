import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import Spinner from './Spinner'
import { useAuth } from '@/store/AuthContext'

interface Props {
  children: ReactNode
  adminOnly?: boolean
}

export default function ProtectedRoute({ children, adminOnly = false }: Props) {
  const { user, loading, isAdmin } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="route-loading">
        <Spinner size={26} label="Loading your session…" />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />

  return <>{children}</>
}
