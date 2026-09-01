import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ArrowLeft, Wand2, Play, Loader2, Film, Scissors, Trash2 } from 'lucide-react'
import api from '../services/api'

interface Job {
  id: string
  job_type: string
  status: string
  prompt?: string
  result?: any
  created_at: string
}

export default function Editor() {
  const { projectId } = useParams()
  const [command, setCommand] = useState('')
  const [videoUrl, setVideoUrl] = useState<string | null>(null)

  const { data: jobs, refetch } = useQuery({
    queryKey: ['jobs', projectId],
    queryFn: async () => {
      const response = await api.get(`/jobs?project_id=${projectId}`)
      return response.data as Job[]
    },
  })

  const editMutation = useMutation({
    mutationFn: async (cmd: string) => {
      const response = await api.post(`/editing/execute?project_id=${projectId}`, {
        command: cmd,
      })
      return response.data
    },
    onSuccess: () => {
      setCommand('')
      refetch()
    },
  })

  const completedJobs = jobs?.filter((j) => j.job_type === 'edit' && j.status === 'completed' && j.result?.video_url) || []
  if (!videoUrl && completedJobs.length > 0) {
    setVideoUrl(completedJobs[0].result.video_url)
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center gap-2 text-make-muted hover:text-make-text mb-6">
        <ArrowLeft className="w-4 h-4" />
        <span className="text-sm">Back</span>
      </div>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">AI Video Editor</h1>
        <p className="text-make-muted mt-1">Edit your video using natural language commands</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4">Preview</h2>
            <div className="aspect-video bg-make-border rounded-lg flex items-center justify-center">
              {videoUrl ? (
                <video
                  src={videoUrl}
                  controls
                  className="w-full h-full rounded-lg object-contain"
                />
              ) : (
                <div className="text-center">
                  <Film className="w-12 h-12 text-make-muted mx-auto mb-2" />
                  <p className="text-make-muted">No video loaded. Upload or generate one first.</p>
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4">Timeline</h2>
            <div className="h-24 bg-make-bg rounded-lg border border-make-border flex items-center px-4">
              <div className="flex gap-2 items-center">
                <div className="w-32 h-12 bg-make-accent/20 border border-make-accent/40 rounded flex items-center justify-center">
                  <span className="text-xs text-make-accent">Video Track</span>
                </div>
                <div className="w-24 h-12 bg-make-border rounded flex items-center justify-center">
                  <span className="text-xs text-make-muted">Audio</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Wand2 className="w-5 h-5" />
              AI Edit Command
            </h2>
            <form onSubmit={(e) => { e.preventDefault(); if (command.trim()) editMutation.mutate(command) }}>
              <textarea
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                className="input min-h-[100px] resize-y mb-3"
                placeholder="Describe your edit in natural language..."
              />
              <button
                type="submit"
                disabled={editMutation.isPending || !command.trim()}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                {editMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Scissors className="w-4 h-4" />
                    Apply Edit
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="card">
            <h3 className="font-semibold text-white mb-3">Quick Commands</h3>
            <div className="space-y-2">
              {[
                'Remove the person on the left',
                'Make the car black',
                'Replace the background with a beach',
                'Add a dog running behind him',
                'Make the explosion larger',
                'Remove the first five seconds',
                'Add captions',
                'Make it feel like a Hollywood trailer',
              ].map((cmd) => (
                <button
                  key={cmd}
                  onClick={() => setCommand(cmd)}
                  className="w-full text-left px-3 py-2 text-sm text-make-muted hover:text-make-text hover:bg-make-surfaceHover rounded-lg transition-colors"
                >
                  "{cmd}"
                </button>
              ))}
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold text-white mb-3">Edit History</h3>
            <div className="space-y-2">
              {jobs?.filter((j) => j.job_type === 'edit').slice(0, 5).map((job) => (
                <div key={job.id} className="flex items-center justify-between p-2 bg-make-bg rounded">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-make-text truncate">{job.prompt}</p>
                    <p className="text-xs text-make-muted">{new Date(job.created_at).toLocaleString()}</p>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs ${job.status === 'completed' ? 'bg-green-400/10 text-green-400' : 'bg-yellow-400/10 text-yellow-400'}`}>
                    {job.status}
                  </span>
                </div>
              ))}
              {!jobs?.some(j => j.job_type === 'edit') && (
                <p className="text-sm text-make-muted">No edits yet</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
