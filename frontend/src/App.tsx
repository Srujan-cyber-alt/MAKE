import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/common/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Project from './pages/Project'
import Generate from './pages/Generate'
import Editor from './pages/Editor'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return <Layout>{children}</Layout>
}

function App() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <Login />}
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId"
        element={
          <ProtectedRoute>
            <Project />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId/generate"
        element={
          <ProtectedRoute>
            <Generate />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId/editor"
        element={
          <ProtectedRoute>
            <Editor />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App
