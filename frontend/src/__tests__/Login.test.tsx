import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Login from '../src/pages/Login'

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

describe('Login', () => {
  it('renders login form', () => {
    renderWithRouter(<Login />)
    expect(screen.getByText('Sign in')).toBeDefined()
    expect(screen.getByPlaceholderText('you@example.com')).toBeDefined()
    expect(screen.getByPlaceholderText('••••••••')).toBeDefined()
  })

  it('renders app branding', () => {
    renderWithRouter(<Login />)
    expect(screen.getByText('MAKE AI Video')).toBeDefined()
  })
})
