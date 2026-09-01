import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Wand2, Upload, Film, Loader2, AlertCircle,
  PlayCircle, X, Trash2, Sparkles, Image, RefreshCw,
  Eye, Target, ShieldCheck, FlaskConical
} from 'lucide-react'
import api from '../services/api'

interface MagicEditorState {
  stage: 'idle' | 'analyzing' | 'targeting' | 'tracking' | 'planning' | 'generating' | 'compositing' | 'validating' | 'completed' | 'failed'
  progress: number
  currentStage: string
  transformationId?: string
  error?: string
  analysis?: any
  targets?: any[]
  selectedTarget?: any
  qualityResult?: any
  versionHistory?: any[]
}

export default function MagicEditor() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [prompt, setPrompt] = useState('')
  const [sourceAssetId, setSourceAssetId] = useState('')
  const [editorState, setEditorState] = useState<MagicEditorState>({
    stage: 'idle',
    progress: 0,
    currentStage: '',
  })

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}`)).data,
  })

  const { data: assets } = useQuery({
    queryKey: ['assets', projectId],
    queryFn: async () => (await api.get(`/assets/project/${projectId}`)).data,
  })

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      setEditorState(s => ({ ...s, stage: 'analyzing', progress: 10, currentStage: 'analyzing' }))
      const res = await api.get(`/phase7/visual-analysis/${sourceAssetId}?project_id=${projectId}`)
      return res.data
    },
    onSuccess: (data) => {
      setEditorState(s => ({ ...s, analysis: data, stage: 'targeting', progress: 20, currentStage: 'targeting' }))
    },
    onError: () => {
      setEditorState(s => ({ ...s, stage: 'failed', error: 'Visual analysis failed' }))
    },
  })

  const targetMutation = useMutation({
    mutationFn: async () => {
      setEditorState(s => ({ ...s, stage: 'targeting', progress: 30, currentStage: 'selecting target' }))
      const res = await api.get(`/phase7/smart-target/${sourceAssetId}?project_id=${projectId}&prompt=${encodeURIComponent(prompt)}`)
      return res.data
    },
    onSuccess: (data) => {
      setEditorState(s => ({ ...s, targets: data.matches, selectedTarget: data.primary_target, stage: 'planning', progress: 40, currentStage: 'planning' }))
    },
  })

  const executeMutation = useMutation({
    mutationFn: async () => {
      setEditorState(s => ({ ...s, stage: 'generating', progress: 50, currentStage: 'generating' }))
      const res = await api.post('/transformation/execute', {
        project_id: projectId,
        source_asset_id: sourceAssetId,
        prompt,
        operations: editorState.selectedTarget ? [{
          type: 'style_transfer',
          target: { type: editorState.selectedTarget.category, description: editorState.selectedTarget.label },
          strength: 0.8,
        }] : [],
        preserve_identity: true,
      })
      return res.data
    },
    onSuccess: (data) => {
      setEditorState(s => ({ ...s, stage: 'validating', progress: 80, currentStage: 'validating', transformationId: data.id }))
      queryClient.invalidateQueries({ queryKey: ['transformations'] })
    },
    onError: (err: any) => {
      setEditorState(s => ({ ...s, stage: 'failed', error: err?.response?.data?.detail || 'Execution failed' }))
    },
  })

  const validateMutation = useMutation({
    mutationFn: async (transformationId: string) => {
      const res = await api.post(`/phase7/quality-gate/${sourceAssetId}`, {}, { params: { identity_required: true } })
      return res.data
    },
    onSuccess: (data) => {
      setEditorState(s => ({ ...s, qualityResult: data, stage: data.passed ? 'completed' : 'failed', progress: 100, currentStage: 'completed' }))
    },
  })

  const handleAnalyze = () => {
    if (!prompt.trim() || !sourceAssetId) return
    analyzeMutation.mutate()
  }

  const handleTarget = () => {
    if (!prompt.trim() || !sourceAssetId) return
    targetMutation.mutate()
  }

  const handleExecute = () => {
    if (!prompt.trim() || !sourceAssetId) return
    executeMutation.mutate()
  }

  useEffect(() => {
    if (editorState.transformationId && editorState.stage === 'validating') {
      const interval = setInterval(() => {
        validateMutation.mutate(editorState.transformationId!)
      }, 2000)
      return () => clearInterval(interval)
    }
  }, [editorState.stage, editorState.transformationId])

  const stageLabels: Record<string, { label: string; icon: any }> = {
    idle: { label: 'Ready', icon: Sparkles },
    analyzing: { label: 'ANALYZING', icon: Eye },
    targeting: { label: 'TARGETING', icon: Target },
    tracking: { label: 'TRACKING', icon: RefreshCw },
    planning: { label: 'PLANNING', icon: FlaskConical },
    generating: { label: 'GENERATING', icon: Wand2 },
    compositing: { label: 'COMPOSITING', icon: PlayCircle },
    validating: { label: 'VALIDATING', icon: ShieldCheck },
    completed: { label: 'COMPLETED', icon: Sparkles },
    failed: { label: 'FAILED', icon: AlertCircle },
  }

  const currentStageInfo = stageLabels[editorState.stage] || stageLabels.idle
  const StageIcon = currentStageInfo.icon

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate(`/projects/${projectId}`)} className="p-2 hover:bg-gray-800 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-3xl font-bold">Magic Editor</h1>
            <p className="text-gray-400">Imagine it. Describe it. MAKE does it.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
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
                Magic Prompt
              </h2>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe what you want to change... e.g., 'Remove the person in the background' or 'Make the car red'"
                className="w-full bg-gray-700 rounded-lg px-4 py-3 h-32 resize-none"
              />
              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleAnalyze}
                  disabled={analyzeMutation.isPending || !prompt.trim() || !sourceAssetId}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 py-3 rounded-lg font-medium flex items-center justify-center gap-2"
                >
                  {analyzeMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Eye className="w-5 h-5" />}
                  Analyze
                </button>
                <button
                  onClick={handleTarget}
                  disabled={targetMutation.isPending || !prompt.trim() || !sourceAssetId || !editorState.analysis}
                  className="flex-1 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 py-3 rounded-lg font-medium flex items-center justify-center gap-2"
                >
                  {targetMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Target className="w-5 h-5" />}
                  Target
                </button>
                <button
                  onClick={handleExecute}
                  disabled={executeMutation.isPending || !prompt.trim() || !sourceAssetId}
                  className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 py-3 rounded-lg font-medium flex items-center justify-center gap-2"
                >
                  {executeMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : <PlayCircle className="w-5 h-5" />}
                  Execute
                </button>
              </div>
            </div>

            {editorState.analysis && (
              <div className="bg-gray-800 rounded-xl p-6">
                <h2 className="text-xl font-semibold mb-4">Analysis Result</h2>
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="text-sm text-gray-400">Objects detected:</div>
                    <span className="text-sm">{editorState.analysis.objects?.length || 0}</span>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="text-sm text-gray-400">Faces detected:</div>
                    <span className="text-sm">{editorState.analysis.faces?.length || 0}</span>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="text-sm text-gray-400">Scene changes:</div>
                    <span className="text-sm">{editorState.analysis.scenes?.length || 0}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-sm text-gray-400">ML Available:</div>
                    <span className="text-sm">{Object.values(editorState.analysis.ml_available || {}).filter(Boolean).length} backends</span>
                  </div>
                </div>
              </div>
            )}

            {editorState.targets && editorState.targets.length > 0 && (
              <div className="bg-gray-800 rounded-xl p-6">
                <h2 className="text-xl font-semibold mb-4">Detected Targets</h2>
                <div className="space-y-2">
                  {editorState.targets.map((target: any, i: number) => (
                    <div key={i} className="bg-gray-700 rounded-lg p-3 flex items-center justify-between">
                      <div>
                        <div className="font-medium">{target.label}</div>
                        <div className="text-sm text-gray-400">{target.category} - confidence: {Math.round(target.confidence * 100)}%</div>
                      </div>
                      <button
                        onClick={() => setEditorState(s => ({ ...s, selectedTarget: target }))}
                        className={`text-sm px-3 py-1 rounded ${editorState.selectedTarget?.target_id === target.target_id ? 'bg-blue-600' : 'bg-gray-600 hover:bg-gray-500'}`}
                      >
                        Select
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="space-y-6">
            <div className="bg-gray-800 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <StageIcon className="w-5 h-5" />
                Status: {currentStageInfo.label}
              </h2>
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-1">
                  <span>{editorState.currentStage || 'Idle'}</span>
                  <span>{Math.round(editorState.progress)}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-3">
                  <div
                    className="bg-green-600 h-3 rounded-full transition-all"
                    style={{ width: `${editorState.progress}%` }}
                  />
                </div>
              </div>
              {editorState.error && (
                <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4">
                  <div className="text-red-400">{editorState.error}</div>
                </div>
              )}
              {editorState.qualityResult && (
                <div className="bg-gray-700 rounded-lg p-3 mb-4">
                  <div className="text-sm text-gray-400 mb-2">Quality Score</div>
                  <div className="text-2xl font-bold">{Math.round(editorState.qualityResult.score.overall * 100)}%</div>
                  <div className="text-sm text-gray-400">Passed: {editorState.qualityResult.passed ? 'Yes' : 'No'}</div>
                </div>
              )}
            </div>

            <div className="bg-gray-800 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">How to use</h2>
              <div className="space-y-3 text-sm text-gray-300">
                <p>1. Select a video asset from your project.</p>
                <p>2. Type a natural language description of what you want to change.</p>
                <p>3. Click <strong>Analyze</strong> to understand the video content.</p>
                <p>4. Click <strong>Target</strong> to identify the specific object or person.</p>
                <p>5. Click <strong>Execute</strong> to apply the transformation.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
