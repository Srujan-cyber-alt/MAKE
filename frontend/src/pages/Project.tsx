import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Plus, Play, Clock, Film, Sparkles } from 'lucide-react'
import api from '../services/api'

interface Project {
  id: string
  name: string
  description?: string
  status: string
  created_at: string
}

interface Job {
  id: string
  job_type: string
  status: string
  prompt?: string
  result?: any
  created_at: string
}

export default function Project() {
  const { projectId } = useParams()
  const { data: project, isLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => {
      const response = await api.get(`/projects/${projectId}`)
      return response.data as Project
    },
  })

  const { data: jobs } = useQuery({
    queryKey: ['jobs', projectId],
    queryFn: async () => {
      const response = await api.get(`/jobs?project_id=${projectId}`)
      return response.data as Job[]
    },
  })

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-make-border rounded w-1/4" />
          <div className="h-32 bg-make-border rounded" />
        </div>
      </div>
    )
  }

  if (!project) {
    return <div className="max-w-6xl mx-auto text-center py-20">Project not found</div>
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-400 bg-green-400/10'
      case 'processing':
      case 'generating': return 'text-yellow-400 bg-yellow-400/10'
      case 'failed': return 'text-red-400 bg-red-400/10'
      case 'queued': return 'text-blue-400 bg-blue-400/10'
      default: return 'text-make-muted bg-make-border'
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      <Link to="/" className="inline-flex items-center gap-2 text-make-muted hover:text-make-text mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to projects
      </Link>

      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">{project.name}</h1>
          <p className="text-make-muted mt-1">{project.description || 'No description'}</p>
        </div>
        <div className="flex gap-3">
          <Link to={`/projects/${projectId}/generate`} className="btn-primary flex items-center gap-2">
            <Play className="w-4 h-4" />
            Generate
          </Link>
          <Link to={`/projects/${projectId}/studio`} className="btn-primary flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Studio
          </Link>
          <Link to={`/projects/${projectId}/editor`} className="btn-secondary flex items-center gap-2">
            <Film className="w-4 h-4" />
            Editor
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4">Recent Jobs</h2>
            {jobs && jobs.length > 0 ? (
              <div className="space-y-3">
                {jobs.map((job) => (
                  <div key={job.id} className="flex items-center justify-between p-3 bg-make-bg rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-make-border rounded-lg flex items-center justify-center">
                        <Film className="w-5 h-5 text-make-muted" />
                      </div>
                      <div>
                        <p className="font-medium text-white text-sm">{job.prompt?.slice(0, 60) || job.job_type}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                            {job.status}
                          </span>
                          <span className="text-xs text-make-muted flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {new Date(job.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </div>
                    {job.result?.video_url && (
                      <video src={job.result.video_url} className="w-24 h-16 rounded object-cover" />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-make-muted text-center py-8">No jobs yet. Start generating!</p>
            )}
          </div>
        </div>

        <div>
          <div className="card">
            <h3 className="font-semibold text-white mb-4">Quick Actions</h3>
            <div className="space-y-3">
              <Link to={`/projects/${projectId}/generate`} className="block w-full btn-primary text-center">
                Text to Video
              </Link>
              <Link to={`/projects/${projectId}/generate?mode=image`} className="block w-full btn-secondary text-center">
                Image to Video
              </Link>
              <Link to={`/projects/${projectId}/editor`} className="block w-full btn-secondary text-center">
                Edit Video
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
