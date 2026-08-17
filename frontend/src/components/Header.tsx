import { useEffect, useRef, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import Logo from './Logo'
import { COMPANY_NAME } from '@/config'
import { useAuth } from '@/store/AuthContext'

interface NavItem {
  to: string
  label: string
  adminOnly?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Home' },
  { to: '/batch', label: 'New Batch' },
  { to: '/history', label: 'History' },
  { to: '/admin', label: 'Admin', adminOnly: true },
  { to: '/settings', label: 'Settings' },
]

export default function Header() {
  const { user, isAdmin, signOut } = useAuth()
  const items = NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin)

  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    const onPointerDown = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [menuOpen])

  return (
    <header className="app-header">
      <div className="header-left">
        <Link to="/" className="header-brand" aria-label={`${COMPANY_NAME} home`}>
          <Logo size={34} name="CDC INTERNATIONAL" />
        </Link>
      </div>

      <nav className="header-nav" aria-label="Main">
        <div className="tabs">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => `tab${isActive ? ' tab-active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="header-right">
        {user && (
          <div className="user-menu" ref={menuRef}>
            <button
              type="button"
              className="user-menu-trigger"
              onClick={() => setMenuOpen((open) => !open)}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
            >
              <span className="avatar" aria-hidden="true">
                {user.username.slice(0, 2).toUpperCase()}
              </span>
              <span className="header-user-meta">
                <span className="header-user-name">{user.full_name || user.username}</span>
                <span className="header-user-role">{user.role}</span>
              </span>
              <span className={`user-menu-caret${menuOpen ? ' user-menu-caret-open' : ''}`} aria-hidden="true">
                ▾
              </span>
            </button>

            {menuOpen && (
              <div className="user-menu-panel" role="menu">
                <Link
                  to="/settings"
                  role="menuitem"
                  className="user-menu-item"
                  onClick={() => setMenuOpen(false)}
                >
                  Settings
                </Link>
                <button
                  type="button"
                  role="menuitem"
                  className="user-menu-item"
                  onClick={() => { setMenuOpen(false); signOut() }}
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  )
}
