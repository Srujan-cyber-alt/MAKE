import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Film, Sparkles, CheckCircle, XCircle, RotateCcw, ChevronDown, ChevronRight, AlertCircle } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

interface SceneData {
  id: string
  order: number
  title: string
  purpose: string
  description: string
  duration_seconds: number
  shots: any[]
}

interface PlanData {
  id: string
  title: string
  creative_concept: string
  objective: string
  content_type: string
  tone: string
  style?: string
  duration: number
  aspect_ratio: string
  resolution: string
  platform?: string
  scenes: SceneData[]
  asset_requirements: any[]
  continuity_requirements: any[]
  audio_requirements: any[]
  export_requirements: any
  generation_requirements: any[]
  status: string
}

export default function Director() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [prompt, setPrompt] = useState('')
  const [selectedPlan, setSelectedPlan] = useState<PlanData | null>(null)
  const [expandedScenes, setExpandedScenes] = useState<Set<number>>(new Set())
  const [error, setError] = useState<string | null>(null)

  const token = localStorage.getItem('token')

  const createPlanMutation = useMutation({
    mutationFn: async (promptText: string) => {
      const response = await axios.post(
        `${API_BASE}/director/plan`,
        {
          prompt: promptText,
          project_id: projectId,
          reference_asset_ids: [],
          preferences: {},
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      )
      return response.data
    },
    onSuccess: (data) => {
      setSelectedPlan(data)
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['director-plans'] })
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to create plan')
    },
  })

  const approveMutation = useMutation({
    mutationFn: async (planId: string) => {
      const response = await axios.post(
        `${API_BASE}/director/plans/${planId}/approve`,
        {},
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      )
      return response.data
    },
    onSuccess: (data) => {
      setSelectedPlan(data)
      queryClient.invalidateQueries({ queryKey: ['director-plans'] })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: async (planId: string) => {
      const response = await axios.post(
        `${API_BASE}/director/plans/${planId}/reject`,
        {},
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      )
      return response.data
    },
    onSuccess: (data) => {
      setSelectedPlan(data)
      queryClient.invalidateQueries({ queryKey: ['director-plans'] })
    },
  })

  const { data: plans, isLoading: plansLoading } = useQuery({
    queryKey: ['director-plans', projectId],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE}/director/projects/${projectId}/plans`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      return response.data
    },
    enabled: !!projectId,
  })

  const handleCreatePlan = () => {
    if (!prompt.trim()) return
    createPlanMutation.mutate(prompt)
  }

  const toggleScene = (index: number) => {
    const newExpanded = new Set(expandedScenes)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedScenes(newExpanded)
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'text-green-400 bg-green-400/10'
      case 'rejected':
        return 'text-red-400 bg-red-400/10'
      case 'draft':
        return 'text-yellow-400 bg-yellow-400/10'
      default:
        return 'text-gray-400 bg-gray-400/10'
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-3">
          <Film className="w-10 h-10 text-purple-400" />
          <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            MAKE DIRECTOR
          </h1>
        </div>
        <p className="text-gray-400 text-lg">
          Describe your video idea and I'll create a production plan
        </p>
      </div>

      <div className="bg-gray-800/50 rounded-2xl p-8 border border-gray-700/50">
        <label className="block text-sm font-medium text-gray-300 mb-3">
          What do you want to create?
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Create a 30 second cinematic luxury watch advertisement. Start with an extreme macro shot of the watch, show water droplets moving across it, orbit around the product, transition to a man wearing it in a rainy city at night, then finish with the watch and logo. Make it premium and cinematic."
          className="w-full h-32 bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
        />
        <div className="mt-4 flex justify-between items-center">
          <div className="text-sm text-gray-500">
            Be descriptive. Include duration, style, platform, and key visual elements.
          </div>
          <button
            onClick={handleCreatePlan}
            disabled={!prompt.trim() || createPlanMutation.isPending}
            className="flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-colors"
          >
            <Sparkles className="w-5 h-5" />
            {createPlanMutation.isPending ? 'Creating Plan...' : 'Create Plan'}
          </button>
        </div>
        {error && (
          <div className="mt-4 p-4 bg-red-900/20 border border-red-700/50 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
            <div>
              <div className="text-red-400 font-medium">Error</div>
              <div className="text-red-300 text-sm mt-1">{error}</div>
            </div>
          </div>
        )}
      </div>

      {selectedPlan && (
        <div className="bg-gray-800/50 rounded-2xl border border-gray-700/50 overflow-hidden">
          <div className="p-6 border-b border-gray-700/50">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">{selectedPlan.title}</h2>
                <p className="text-gray-400 mt-1">{selectedPlan.creative_concept}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(selectedPlan.status)}`}>
                {selectedPlan.status}
              </span>
            </div>
            <div className="flex flex-wrap gap-4 mt-4 text-sm">
              <div className="px-3 py-1 bg-gray-700/50 rounded-lg">
                <span className="text-gray-400">Type:</span>
                <span className="text-white ml-2 capitalize">{selectedPlan.content_type}</span>
              </div>
              <div className="px-3 py-1 bg-gray-700/50 rounded-lg">
                <span className="text-gray-400">Duration:</span>
                <span className="text-white ml-2">{formatDuration(selectedPlan.duration)}</span>
              </div>
              <div className="px-3 py-1 bg-gray-700/50 rounded-lg">
                <span className="text-gray-400">Aspect:</span>
                <span className="text-white ml-2">{selectedPlan.aspect_ratio}</span>
              </div>
              <div className="px-3 py-1 bg-gray-700/50 rounded-lg">
                <span className="text-gray-400">Resolution:</span>
                <span className="text-white ml-2">{selectedPlan.resolution}</span>
              </div>
              {selectedPlan.platform && (
                <div className="px-3 py-1 bg-gray-700/50 rounded-lg">
                  <span className="text-gray-400">Platform:</span>
                  <span className="text-white ml-2 capitalize">{selectedPlan.platform}</span>
                </div>
              )}
              {selectedPlan.style && (
                <div className="px-3 py-1 bg-gray-700/50 rounded-lg">
                  <span className="text-gray-400">Style:</span>
                  <span className="text-white ml-2 capitalize">{selectedPlan.style}</span>
                </div>
              )}
            </div>
          </div>

          <div className="p-6 border-b border-gray-700/50">
            <h3 className="text-lg font-semibold text-white mb-4">Scenes</h3>
            <div className="space-y-3">
              {selectedPlan.scenes.map((scene, idx) => (
                <div key={scene.id} className="bg-gray-900/50 rounded-xl border border-gray-700/50 overflow-hidden">
                  <button
                    onClick={() => toggleScene(idx)}
                    className="w-full p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {expandedScenes.has(idx) ? (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-gray-400" />
                      )}
                      <div className="text-left">
                        <div className="font-medium text-white">{scene.title}</div>
                        <div className="text-sm text-gray-400">{scene.purpose}</div>
                      </div>
                    </div>
                    <div className="text-sm text-gray-400">{formatDuration(scene.duration_seconds)}</div>
                  </button>
                  {expandedScenes.has(idx) && (
                    <div className="px-4 pb-4 space-y-2">
                      {scene.shots.map((shot) => (
                        <div key={shot.id} className="bg-gray-800/50 rounded-lg p-3">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="text-sm font-medium text-white">{shot.description}</div>
                              <div className="text-xs text-gray-400 mt-1">
                                {shot.camera.movement} / {shot.camera.lens}
                              </div>
                              {shot.lighting && (
                                <div className="text-xs text-gray-500 mt-1">Lighting: {shot.lighting}</div>
                              )}
                            </div>
                            <div className="text-xs text-gray-500">{formatDuration(shot.duration_seconds)}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {selectedPlan.asset_requirements.length > 0 && (
            <div className="p-6 border-b border-gray-700/50">
              <h3 className="text-lg font-semibold text-white mb-4">Assets Needed</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {selectedPlan.asset_requirements.map((asset) => (
                  <div key={asset.id} className="bg-gray-900/50 rounded-lg p-3 border border-gray-700/50">
                    <div className="text-sm font-medium text-white capitalize">{asset.type}</div>
                    <div className="text-xs text-gray-400 mt-1">{asset.description}</div>
                    {asset.required && (
                      <div className="text-xs text-orange-400 mt-2">Required</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {selectedPlan.audio_requirements.length > 0 && (
            <div className="p-6 border-b border-gray-700/50">
              <h3 className="text-lg font-semibold text-white mb-4">Audio</h3>
              <div className="flex flex-wrap gap-2">
                {selectedPlan.audio_requirements.map((audio) => (
                  <span key={audio.id} className="px-3 py-1 bg-gray-700/50 rounded-full text-sm text-gray-300 capitalize">
                    {audio.type}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="p-6 flex items-center justify-between">
            <div className="flex gap-3">
              <button
                onClick={() => selectedPlan && approveMutation.mutate(selectedPlan.id)}
                disabled={selectedPlan.status === 'approved' || approveMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
              >
                <CheckCircle className="w-4 h-4" />
                {approveMutation.isPending ? 'Approving...' : 'Approve Plan'}
              </button>
              <button
                onClick={() => selectedPlan && rejectMutation.mutate(selectedPlan.id)}
                disabled={selectedPlan.status === 'rejected' || rejectMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
              >
                <XCircle className="w-4 h-4" />
                {rejectMutation.isPending ? 'Rejecting...' : 'Reject Plan'}
              </button>
            </div>
            <button
              onClick={() => createPlanMutation.mutate(prompt)}
              disabled={!prompt.trim() || createPlanMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              Regenerate Plan
            </button>
          </div>
        </div>
      )}

      {plans && plans.length > 0 && !selectedPlan && (
        <div className="bg-gray-800/50 rounded-2xl p-6 border border-gray-700/50">
          <h3 className="text-lg font-semibold text-white mb-4">Previous Plans</h3>
          <div className="space-y-3">
            {plans.map((plan: PlanData) => (
              <div
                key={plan.id}
                onClick={() => setSelectedPlan(plan)}
                className="bg-gray-900/50 rounded-xl p-4 border border-gray-700/50 cursor-pointer hover:border-purple-500/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-white">{plan.title}</div>
                    <div className="text-sm text-gray-400 mt-1">{plan.creative_concept}</div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(plan.status)}`}>
                    {plan.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
