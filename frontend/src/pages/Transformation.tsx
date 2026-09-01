import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Wand2, Upload, Film, Loader2, AlertCircle,
  PlayCircle, X, Trash2, Sparkles, Image, RefreshCw
} from 'lucide-react'
import api from '../services/api'

interface TransformationOperation {
  type: string
  target?: { type: string; description: string; confidence: number }
  parameters: Record<string, any>
  preserve_identity: boolean
  preserve_background: boolean
  strength: number
}

interface TransformationStatus {
  id: string
  status: string
  progress: number
  current_stage?: string
  error?: string
  result_asset_id?: string
  job_id?: string
}

interface AnalysisResult {
  suggested_operations: TransformationOperation[]
  confidence: number
  requires_clarification: boolean
  clarification_questions: string[]
  missing_capabilities: string[]
  warnings: string[]
}

export default function Transformation() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [prompt, setPrompt] = useState('')
  const [sourceAssetId, setSourceAssetId] = useState('')
  const [operations, setOperations] = useState<TransformationOperation[]>([])
  const [preserveIdentity, setPreserveIdentity] = useState(true)
  const [preserveBackground, setPreserveBackground] = useState(false)
  const [strength, setStrength] = useState(0.8)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [transformationId, setTransformationId] = useState<string | null>(null)

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}`)).data,
  })

  const { data: assets } = useQuery({
    queryKey: ['assets', projectId],
    queryFn: async () => (await api.get(`/assets/project/${projectId}`)).data,
  })

  const { data: transformations } = useQuery({
    queryKey: ['transformations', projectId],
    queryFn: async () => (await api.get(`/transformation/projects/${projectId}`)).data,
    enabled: !!projectId,
    refetchInterval: transformationId ? 2000 : false,
  })

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/transformation/analyze', {
        project_id: projectId,
        source_asset_id: sourceAssetId,
        prompt,
        preserve_identity: preserveIdentity,
        preserve_background: preserveBackground,
        strength,
      })
      return res.data
    },
    onSuccess: (data) => {
      setAnalysis(data)
      setOperations(data.suggested_operations)
    },
  })

  const executeMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/transformation/execute', {
        project_id: projectId,
        source_asset_id: sourceAssetId,
        prompt,
        operations,
        preserve_identity: preserveIdentity,
        preserve_background: preserveBackground,
        strength,
      })
      return res.data
    },
    onSuccess: (data) => {
      setTransformationId(data.transformation_id)
      queryClient.invalidateQueries({ queryKey: ['transformations'] })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: async () => {
      await api.post(`/transformation/${transformationId}/cancel`)
    },
    onSuccess: () => {
      setTransformationId(null)
      queryClient.invalidateQueries({ queryKey: ['transformations'] })
    },
  })

  const handleAnalyze = () => {
    if (!prompt.trim() || !sourceAssetId) return
    setAnalyzing(true)
    analyzeMutation.mutate(undefined, {
      onSettled: () => setAnalyzing(false),
    })
  }

  const handleExecute = () => {
    if (operations.length === 0) return
    executeMutation.mutate()
  }

  const activeTransformation = transformations?.find((t: TransformationStatus) => t.id === transformationId)

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate(`/projects/${projectId}`)} className="p-2 hover:bg-gray-800 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-3xl font-bold">Transformation Engine</h1>
            <p className="text-gray-400">AI-powered video transformation and VFX</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div className="bg-gray-800 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Film className="w-5 h-5" />
                Source Video
              </h2>
              <select
                value={sourceAssetId}
                onChange={(e) => setSourceAssetId(e.target.value)}
                className="w-full bg-gray-700 rounded-lg px-4 py-3 mb-4"
              >
                <option value="">Select a video asset</option>
                {assets?.map((asset: any) => (
                  <option key={asset.id} value={asset.id}>{asset.filename}</option>
                ))}
              </select>
              {sourceAssetId && (
                <div className="bg-gray-700 rounded-lg p-4">
                  <video
                    src={api.getUri && api.getUri({ url: `/files/${sourceAssetId}` })}
                    className="w-full rounded-lg"
                    controls
                  />
                </div>
              )}
            </div>

            <div className="bg-gray-800 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Wand2 className="w-5 h-5" />
                Transformation Prompt
              </h2>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe what you want to change... e.g., 'Remove the person in the background and replace with rain'"
                className="w-full bg-gray-700 rounded-lg px-4 py-3 h-32 resize-none"
              />
              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing || !prompt.trim() || !sourceAssetId}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 py-3 rounded-lg font-medium flex items-center justify-center gap-2"
                >
                  {analyzing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                  Analyze
                </button>
                <button
                  onClick={handleExecute}
                  disabled={operations.length === 0 || !!activeTransformation}
                  className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 py-3 rounded-lg font-medium flex items-center justify-center gap-2"
                >
                  <PlayCircle className="w-5 h-5" />
                  Execute
                </button>
              </div>
            </div>

            <div className="bg-gray-800 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Settings</h2>
              <div className="space-y-4">
                <label className="flex items-center justify-between">
                  <span>Preserve Identity</span>
                  <input type="checkbox" checked={preserveIdentity} onChange={(e) => setPreserveIdentity(e.target.checked)} />
                </label>
                <label className="flex items-center justify-between">
                  <span>Preserve Background</span>
                  <input type="checkbox" checked={preserveBackground} onChange={(e) => setPreserveBackground(e.target.checked)} />
                </label>
                <div>
                  <label className="block mb-2">Strength: {strength}</label>
                  <input type="range" min="0" max="1" step="0.1" value={strength} onChange={(e) => setStrength(parseFloat(e.target.value))} className="w-full" />
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {analysis && (
              <div className="bg-gray-800 rounded-xl p-6">
                <h2 className="text-xl font-semibold mb-4">Analysis Result</h2>
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="text-sm text-gray-400">Confidence:</div>
                    <div className="w-32 bg-gray-700 rounded-full h-2">
                      <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${analysis.confidence * 100}%` }} />
                    </div>
                    <span className="text-sm">{Math.round(analysis.confidence * 100)}%</span>
                  </div>
                </div>
                {analysis.warnings.length > 0 && (
                  <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-3 mb-4">
                    <div className="flex items-center gap-2 text-yellow-400">
                      <AlertCircle className="w-4 h-4" />
                      <span className="font-medium">Warnings</span>
                    </div>
                    <ul className="mt-2 text-sm text-yellow-300 list-disc list-inside">
                      {analysis.warnings.map((w, i) => <li key={i}>{w}</li>)}
                    </ul>
                  </div>
                )}
                {analysis.missing_capabilities.length > 0 && (
                  <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4">
                    <div className="flex items-center gap-2 text-red-400">
                      <AlertCircle className="w-4 h-4" />
                      <span className="font-medium">Missing Capabilities</span>
                    </div>
                    <ul className="mt-2 text-sm text-red-300 list-disc list-inside">
                      {analysis.missing_capabilities.map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                )}
                <div className="space-y-3">
                  <h3 className="font-medium">Suggested Operations</h3>
                  {analysis.suggested_operations.map((op, i) => (
                    <div key={i} className="bg-gray-700 rounded-lg p-3 flex items-center justify-between">
                      <div>
                        <div className="font-medium">{op.type.replace(/_/g, ' ')}</div>
                        {op.target && <div className="text-sm text-gray-400">{op.target.description}</div>}
                      </div>
                      <button
                        onClick={() => setOperations([op])}
                        className="text-sm bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded"
                      >
                        Select
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTransformation && (
              <div className="bg-gray-800 rounded-xl p-6">
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Transformation Progress
                </h2>
                <div className="mb-4">
                  <div className="flex justify-between text-sm mb-1">
                    <span>{activeTransformation.current_stage || 'Processing'}</span>
                    <span>{Math.round(activeTransformation.progress)}%</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-3">
                    <div
                      className="bg-green-600 h-3 rounded-full transition-all"
                      style={{ width: `${activeTransformation.progress}%` }}
                    />
                  </div>
                </div>
                {activeTransformation.error && (
                  <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4">
                    <div className="text-red-400">{activeTransformation.error}</div>
                  </div>
                )}
                <button
                  onClick={() => cancelMutation.mutate()}
                  disabled={cancelMutation.isPending}
                  className="w-full bg-red-600 hover:bg-red-700 py-2 rounded-lg flex items-center justify-center gap-2"
                >
                  <X className="w-4 h-4" />
                  Cancel
                </button>
              </div>
            )}

            <div className="bg-gray-800 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Active Operations</h2>
              {operations.length === 0 ? (
                <p className="text-gray-400 text-sm">No operations selected. Analyze a prompt to get suggestions.</p>
              ) : (
                <div className="space-y-2">
                  {operations.map((op, i) => (
                    <div key={i} className="bg-gray-700 rounded-lg p-3 flex items-center justify-between">
                      <div>
                        <div className="font-medium">{op.type.replace(/_/g, ' ')}</div>
                        {op.target && <div className="text-sm text-gray-400">{op.target.description}</div>}
                        <div className="text-sm text-gray-500">Strength: {op.strength}</div>
                      </div>
                      <button
                        onClick={() => setOperations(operations.filter((_, idx) => idx !== i))}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}