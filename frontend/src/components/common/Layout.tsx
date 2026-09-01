import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { LayoutDashboard, Film, Wand2, Scissors, LogOut, Menu, X } from 'lucide-react'
import { useState } from 'react'

export default function Layout() {
  const { user, logout } = useAuthStore()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/projects', label: 'Projects', icon: Film },
    { path: '/generate', label: 'Generate', icon: Wand2 },
    { path: '/editor', label: 'Editor', icon: Scissors },
  ]

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <div className="min-h-screen bg-make-bg flex">
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-make-surface border-r border-make-border transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:inset-auto
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex items-center justify-between h-16 px-4 border-b border-make-border">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-make-accent rounded-lg flex items-center justify-center">
              <Film className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-white">MAKE AI</span>
          </Link>
          <button className="lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="p-3 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`
                flex items-center gap-3 px-3 py-2 rounded-lg transition-colors
                ${isActive(item.path)
                  ? 'bg-make-accent text-white'
                  : 'text-make-muted hover:text-make-text hover:bg-make-surfaceHover'
                }
              `}
              onClick={() => setSidebarOpen(false)}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-make-border">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-make-accent flex items-center justify-center text-white font-medium text-sm">
              {user?.full_name?.[0] || user?.email[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-make-text truncate">{user?.full_name || 'User'}</p>
              <p className="text-xs text-make-muted truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-make-muted hover:text-make-text transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      <main className="flex-1 min-w-0">
        <header className="h-16 border-b border-make-border flex items-center justify-between px-6">
          <button className="lg:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex-1 lg:flex-none">
            <h1 className="text-lg font-semibold text-make-text capitalize">
              {location.pathname === '/' ? 'Dashboard' : location.pathname.replace('/', '')}
            </h1>
          </div>
        </header>
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
