import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Film, Clock, Play, MoreVertical } from 'lucide-react'
import api from '../services/api'

interface Project {
  id: string
  name: string
  description?: string
  status: string
  created_at: string
}

export default function Dashboard() {
  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await api.get('/projects')
      return response.data as Project[]
    },
  })

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Projects</h1>
          <p className="text-make-muted mt-1">Manage your video projects</p>
        </div>
        <Link to="/projects/new" className="btn-primary flex items-center gap-2">
          <Plus className="w-5 h-5" />
          New Project
        </Link>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-40 bg-make-border rounded-lg mb-4" />
              <div className="h-6 bg-make-border rounded w-3/4 mb-2" />
              <div className="h-4 bg-make-border rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : projects && projects.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="card group hover:border-make-accent transition-colors"
            >
              <div className="aspect-video bg-make-border rounded-lg mb-4 flex items-center justify-center">
                <Film className="w-12 h-12 text-make-muted group-hover:text-make-accent transition-colors" />
              </div>
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-white group-hover:text-make-accent transition-colors">
                    {project.name}
                  </h3>
                  <p className="text-sm text-make-muted mt-1 line-clamp-2">
                    {project.description || 'No description'}
                  </p>
                  <div className="flex items-center gap-2 mt-3 text-xs text-make-muted">
                    <Clock className="w-3 h-3" />
                    {new Date(project.created_at).toLocaleDateString()}
                  </div>
                </div>
                <button className="p-1 hover:bg-make-surfaceHover rounded">
                  <MoreVertical className="w-4 h-4 text-make-muted" />
                </button>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <Film className="w-16 h-16 text-make-muted mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">No projects yet</h2>
          <p className="text-make-muted mb-6">Create your first video project to get started</p>
          <Link to="/projects/new" className="btn-primary inline-flex items-center gap-2">
            <Plus className="w-5 h-5" />
            Create Project
          </Link>
        </div>
      )}
    </div>
  )
}
