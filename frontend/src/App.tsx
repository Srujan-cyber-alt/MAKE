import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/common/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Project from './pages/Project'
import Generate from './pages/Generate'
import Editor from './pages/Editor'
import Director from './pages/Director'
import Transformation from './pages/Transformation'
import MagicEditor from './pages/MagicEditor'
import NewProject from './pages/NewProject'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state: any) => state.isAuthenticated)
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  const LayoutComponent = Layout as React.ComponentType<{ children: React.ReactNode }>
  return <LayoutComponent>{children}</LayoutComponent>
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
        path="/register"
        element={isAuthenticated ? <Navigate to="/" replace /> : <Register />}
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
        path="/projects/new"
        element={
          <ProtectedRoute>
            <NewProject />
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
      <Route
        path="/projects/:projectId/director"
        element={
          <ProtectedRoute>
            <Director />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId/transform"
        element={
          <ProtectedRoute>
            <Transformation />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId/magic"
        element={
          <ProtectedRoute>
            <MagicEditor />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App
