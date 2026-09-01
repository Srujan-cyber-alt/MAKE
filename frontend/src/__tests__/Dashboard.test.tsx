import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Dashboard from '../src/pages/Dashboard'

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

describe('Dashboard', () => {
  it('renders dashboard heading', () => {
    renderWithRouter(<Dashboard />)
    expect(screen.getByText('Projects')).toBeDefined()
  })

  it('renders new project button', () => {
    renderWithRouter(<Dashboard />)
    expect(screen.getByText('New Project')).toBeDefined()
  })
})
