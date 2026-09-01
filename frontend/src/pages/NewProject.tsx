import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Plus, Loader2 } from 'lucide-react'
import api from '../services/api'

export default function NewProject() {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/projects', { name, description })
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      navigate(`/projects/${data.id}`)
    },
  })

  return (
    <div className="max-w-2xl mx-auto">
      <button
        onClick={() => navigate('/')}
        className="inline-flex items-center gap-2 text-make-muted hover:text-make-text mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to projects
      </button>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">New Project</h1>
        <p className="text-make-muted mt-1">Create a new video project</p>
      </div>

      <div className="card">
        <form onSubmit={(e) => { e.preventDefault(); if (name.trim()) mutation.mutate() }} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-make-text mb-2">Project Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input"
              placeholder="My Video Project"
              required
              maxLength={255}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-make-text mb-2">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input min-h-[120px] resize-y"
              placeholder="Describe your project..."
              maxLength={5000}
            />
          </div>

          {mutation.isError && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3 text-red-400">
              <AlertCircle className="w-5 h-5 mt-0.5" />
              <div>
                <p className="font-medium">Failed to create project</p>
                <p className="text-sm mt-1">{(mutation.error as any)?.response?.data?.detail || 'Unknown error'}</p>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || mutation.isPending}
              className="btn-primary flex items-center gap-2"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Create Project
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
