import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Wand2, Upload, Film, Loader2, AlertCircle,
  PlayCircle, X, Trash2, Sparkles, Image, RefreshCw,
  Eye, Target, ShieldCheck, FlaskConical, Users, Package,
  Camera, Volume2, Type, Palette, Scissors, Layers,
  Undo2, Redo2, Download, RefreshCcw, Zap, CheckCircle2,
  HelpCircle, Command, Settings2
} from 'lucide-react'
import api from '../services/api'

interface MagicEditorState {
  stage: 'idle' | 'analyzing' | 'targeting' | 'planning' | 'generating' | 'compositing' | 'validating' | 'repairing' | 'completed' | 'failed' | 'cancelled'
  progress: number
  currentStage: string
  transformationId?: string
  pipelineId?: string
  error?: string
  analysis?: any
  targets?: any[]
  selectedTarget?: any
  qualityResult?: any
  versionHistory?: any[]
  capabilities?: any
  activeTab: 'assets' | 'characters' | 'products' | 'references'
}

const EXAMPLE_PROMPTS = [
  "Remove the person in the background",
  "Keep the woman exactly the same but change her clothes",
  "Make him run",
  "Make her turn around",
  "Change the car to a Ferrari",
  "Replace the background with Tokyo at night",
  "Make the camera orbit around the subject",
  "Add rain",
  "Add fire behind the car",
  "Make this cinematic",
  "Keep the face identical",
  "Make the movement realistic",
  "Extend this shot by 5 seconds",
  "Change this shot to vertical 9:16",
  "Create three variations",
]

export default function MagicEditor() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [prompt, setPrompt] = useState('')
  const [sourceAssetId, setSourceAssetId] = useState('')
  const [selectedCharacter, setSelectedCharacter] = useState<any>(null)
  const [selectedProduct, setSelectedProduct] = useState<any>(null)
  const [selectedReference, setSelectedReference] = useState<any>(null)
  const [editorState, setEditorState] = useState<MagicEditorState>({
    stage: 'idle',
    progress: 0,
    currentStage: '',
    activeTab: 'assets',
  })

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}`)).data,
  })

  const { data: assets } = useQuery({
    queryKey: ['assets', projectId],
    queryFn: async () => (await api.get(`/assets/project/${projectId}`)).data,
  })

  const { data: capabilities } = useQuery({
    queryKey: ['capabilities'],
    queryFn: async () => (await api.get('/phase9/capabilities')).data,
  })

  const { data: characters } = useQuery({
    queryKey: ['characters'],
    queryFn: async () => (await api.get('/phase9/characters')).data,
  })

  const { data: products } = useQuery({
    queryKey: ['products'],
    queryFn: async () => (await api.get('/phase9/products')).data,
  })

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      setEditorState(s => ({ ...s, stage: 'analyzing', progress: 10, currentStage: 'Analyzing video content...' }))
      const res = await api.get(`/phase7/visual-analysis/${sourceAssetId}?project_id=${projectId}`)
      return res.data
    },
    onSuccess: (data) => {
      setEditorState(s => ({ ...s, analysis: data, stage: 'targeting', progress: 20, currentStage: 'Identifying targets...' }))
    },
    onError: (err: any) => {
      setEditorState(s => ({ ...s, stage: 'failed', error: err?.response?.data?.detail || 'Visual analysis failed' }))
    },
  })

  const targetMutation = useMutation({
    mutationFn: async () => {
      setEditorState(s => ({ ...s, stage: 'targeting', progress: 30, currentStage: 'Selecting target...' }))
      const res = await api.get(`/phase7/smart-target/${sourceAssetId}?project_id=${projectId}&prompt=${encodeURIComponent(prompt)}`)
      return res.data
    },
    onSuccess: (data) => {
      setEditorState(s => ({ ...s, targets: data.matches, selectedTarget: data.primary_target, stage: 'planning', progress: 40, currentStage: 'Planning transformation...' }))
    },
  })

  const executeMutation = useMutation({
    mutationFn: async () => {
      setEditorState(s => ({ ...s, stage: 'generating', progress: 50, currentStage: 'Generating...' }))
      const res = await api.post('/phase9/pipeline/execute', {
        project_id: projectId,
        source_asset_id: sourceAssetId,
        prompt,
        operations: [],
        preserve_identity: true,
      })
      return res.data
    },
    onSuccess: (data) => {
      setEditorState(s => ({ 
        ...s, 
        stage: 'validating', 
        progress: 80, 
        currentStage: 'Validating quality...',
        pipelineId: data.pipeline_id,
        transformationId: data.output?.transformation_id,
      }))
      queryClient.invalidateQueries({ queryKey: ['transformations'] })
    },
    onError: (err: any) => {
      setEditorState(s => ({ ...s, stage: 'failed', error: err?.response?.data?.detail || 'Execution failed' }))
    },
  })

  const repairMutation = useMutation({
    mutationFn: async () => {
      setEditorState(s => ({ ...s, stage: 'repairing', progress: 60, currentStage: 'Repairing shot...' }))
      const res = await api.post('/phase9/repair', {
        shot_id: editorState.transformationId,
        repair_type: 'temporal',
      })
      return res.data
    },
    onSuccess: (data) => {
      setEditorState(s => ({ ...s, stage: 'completed', progress: 100, currentStage: 'Repair completed' }))
    },
  })

  const exportMutation = useMutation({
    mutationFn: async () => {
      setEditorState(s => ({ ...s, currentStage: 'Exporting...' }))
      const res = await api.post('/phase9/export', {
        source_path: `/tmp/${sourceAssetId}.mp4`,
        output_path: `/tmp/${sourceAssetId}_export.mp4`,
        platform: 'youtube',
      })
      return res.data
    },
    onSuccess: (data) => {
      setEditorState(s => ({ ...s, currentStage: 'Export completed', progress: 100 }))
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

  const handleRepair = () => {
    if (!editorState.transformationId) return
    repairMutation.mutate()
  }

  const handleExport = () => {
    exportMutation.mutate()
  }

  const handleCancel = () => {
    setEditorState(s => ({ ...s, stage: 'cancelled', currentStage: 'Cancelled', progress: 0 }))
  }

  const stageLabels: Record<string, { label: string; icon: any; color: string }> = {
    idle: { label: 'Ready', icon: Sparkles, color: 'text-gray-400' },
    analyzing: { label: 'ANALYZING', icon: Eye, color: 'text-blue-400' },
    targeting: { label: 'TARGETING', icon: Target, color: 'text-purple-400' },
    planning: { label: 'PLANNING', icon: FlaskConical, color: 'text-yellow-400' },
    generating: { label: 'GENERATING', icon: Wand2, color: 'text-green-400' },
    compositing: { label: 'COMPOSITING', icon: Layers, color: 'text-pink-400' },
    validating: { label: 'VALIDATING', icon: ShieldCheck, color: 'text-orange-400' },
    repairing: { label: 'REPAIRING', icon: RefreshCcw, color: 'text-red-400' },
    completed: { label: 'COMPLETED', icon: CheckCircle2, color: 'text-green-400' },
    failed: { label: 'FAILED', icon: AlertCircle, color: 'text-red-400' },
    cancelled: { label: 'CANCELLED', icon: X, color: 'text-gray-400' },
  }

  const currentStageInfo = stageLabels[editorState.stage] || stageLabels.idle
  const StageIcon = currentStageInfo.icon

  const isProcessing = ['analyzing', 'targeting', 'planning', 'generating', 'compositing', 'validating', 'repairing'].includes(editorState.stage)

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white">
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(`/projects/${projectId}`)} className="p-2 hover:bg-gray-800 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold">Magic Editor</h1>
            <p className="text-sm text-gray-400">Imagine it. Describe it. MAKE does it.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isProcessing && (
            <button onClick={handleCancel} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm">
              Cancel
            </button>
          )}
          {editorState.stage === 'completed' && (
            <>
              <button onClick={handleExport} className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm flex items-center gap-1">
                <Download className="w-4 h-4" /> Export
              </button>
              <button onClick={() => setEditorState(s => ({ ...s, stage: 'idle', progress: 0, transformationId: undefined }))} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm">
                New Edit
              </button>
            </>
          )}
          {editorState.stage === 'failed' && (
            <button onClick={() => setEditorState(s => ({ ...s, stage: 'idle', progress: 0, error: undefined }))} className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm">
              Retry
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-64 border-r border-gray-800 flex flex-col">
          <div className="flex border-b border-gray-800">
            {(['assets', 'characters', 'products', 'references'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setEditorState(s => ({ ...s, activeTab: tab }))}
                className={`flex-1 py-2 text-xs capitalize ${editorState.activeTab === tab ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white'}`}
              >
                {tab}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {editorState.activeTab === 'assets' && (
              <div className="space-y-1">
                {assets?.map((asset: any) => (
                  <button
                    key={asset.id}
                    onClick={() => setSourceAssetId(asset.id)}
                    className={`w-full text-left p-2 rounded-lg text-sm ${sourceAssetId === asset.id ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`}
                  >
                    <div className="flex items-center gap-2">
                      <Film className="w-4 h-4" />
                      <span className="truncate">{asset.filename}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
            {editorState.activeTab === 'characters' && (
              <div className="space-y-1">
                {characters?.map((char: any) => (
                  <button
                    key={char.id}
                    onClick={() => setSelectedCharacter(char)}
                    className={`w-full text-left p-2 rounded-lg text-sm ${selectedCharacter?.id === char.id ? 'bg-purple-600' : 'bg-gray-800 hover:bg-gray-700'}`}
                  >
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4" />
                      <span>{char.name}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
            {editorState.activeTab === 'products' && (
              <div className="space-y-1">
                {products?.map((prod: any) => (
                  <button
                    key={prod.id}
                    onClick={() => setSelectedProduct(prod)}
                    className={`w-full text-left p-2 rounded-lg text-sm ${selectedProduct?.id === prod.id ? 'bg-green-600' : 'bg-gray-800 hover:bg-gray-700'}`}
                  >
                    <div className="flex items-center gap-2">
                      <Package className="w-4 h-4" />
                      <span>{prod.name}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
            {editorState.activeTab === 'references' && (
              <div className="space-y-1">
                {assets?.filter((a: any) => a.id !== sourceAssetId).map((asset: any) => (
                  <button
                    key={asset.id}
                    onClick={() => setSelectedReference(asset)}
                    className={`w-full text-left p-2 rounded-lg text-sm ${selectedReference?.id === asset.id ? 'bg-yellow-600' : 'bg-gray-800 hover:bg-gray-700'}`}
                  >
                    <div className="flex items-center gap-2">
                      <Image className="w-4 h-4" />
                      <span className="truncate">{asset.filename}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 flex items-center justify-center p-6 bg-black">
            {sourceAssetId ? (
              <video
                src={sourceAssetId ? `/api/v1/files/${sourceAssetId}` : undefined}
                className="max-w-full max-h-full rounded-lg"
                controls
              />
            ) : (
              <div className="text-gray-500 text-center">
                <Film className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>Select a video asset to begin</p>
              </div>
            )}
          </div>

          <div className="border-t border-gray-800 p-4">
            <div className="mb-3">
              <label className="block text-sm text-gray-400 mb-1">Describe what you want to change</label>
              <div className="relative">
                <Command className="absolute left-3 top-3 w-4 h-4 text-gray-500" />
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Tell MAKE what you want to change... e.g., 'Remove the person in the background' or 'Make the car red'"
                  className="w-full bg-gray-800 rounded-lg pl-10 pr-4 py-3 h-20 resize-none border border-gray-700 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {EXAMPLE_PROMPTS.slice(0, 5).map(example => (
                  <button
                    key={example}
                    onClick={() => setPrompt(example)}
                    className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded-full text-gray-300"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleAnalyze}
                disabled={analyzeMutation.isPending || !prompt.trim() || !sourceAssetId}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 py-2.5 rounded-lg font-medium flex items-center justify-center gap-2"
              >
                {analyzeMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
                Analyze
              </button>
              <button
                onClick={handleTarget}
                disabled={targetMutation.isPending || !prompt.trim() || !sourceAssetId || !editorState.analysis}
                className="flex-1 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 py-2.5 rounded-lg font-medium flex items-center justify-center gap-2"
              >
                {targetMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Target className="w-4 h-4" />}
                Target
              </button>
              <button
                onClick={handleExecute}
                disabled={executeMutation.isPending || !prompt.trim() || !sourceAssetId}
                className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 py-2.5 rounded-lg font-medium flex items-center justify-center gap-2"
              >
                {executeMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
                Generate
              </button>
              {editorState.stage === 'completed' && (
                <>
                  <button onClick={handleRepair} className="bg-red-600 hover:bg-red-700 py-2.5 px-4 rounded-lg font-medium flex items-center gap-1">
                    <RefreshCcw className="w-4 h-4" /> Repair
                  </button>
                  <button onClick={handleExport} className="bg-yellow-600 hover:bg-yellow-700 py-2.5 px-4 rounded-lg font-medium flex items-center gap-1">
                    <Download className="w-4 h-4" /> Export
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="w-80 border-l border-gray-800 flex flex-col overflow-y-auto">
          <div className="p-4 border-b border-gray-800">
            <h2 className="font-semibold mb-3 flex items-center gap-2">
              <Settings2 className="w-4 h-4" />
              AI Command Center
            </h2>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Mode</label>
                <select className="w-full bg-gray-800 rounded px-2 py-1.5 text-sm">
                  <option>Auto</option>
                  <option>Fast</option>
                  <option>Quality</option>
                  <option>Cinematic</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Strength</label>
                <input type="range" min="0" max="1" step="0.1" defaultValue="0.8" className="w-full" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="preserve-identity" defaultChecked className="rounded" />
                <label htmlFor="preserve-identity" className="text-sm">Preserve identity</label>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="auto-repair" defaultChecked className="rounded" />
                <label htmlFor="auto-repair" className="text-sm">Auto-repair on failure</label>
              </div>
            </div>
          </div>

          <div className="p-4 border-b border-gray-800">
            <h3 className="font-medium mb-2">Status</h3>
            <div className={`flex items-center gap-2 mb-3 ${currentStageInfo.color}`}>
              <StageIcon className="w-5 h-5" />
              <span className="font-medium">{currentStageInfo.label}</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${editorState.progress}%` }}
              />
            </div>
            <div className="text-xs text-gray-400">{editorState.currentStage || 'Idle'} — {Math.round(editorState.progress)}%</div>
          </div>

          {editorState.error && (
            <div className="p-4 border-b border-gray-800">
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-3">
                <div className="text-red-400 font-medium mb-1">Error</div>
                <div className="text-sm text-red-300 mb-2">{editorState.error}</div>
                <div className="text-xs text-gray-400">
                  <p className="font-medium mb-1">What you can do:</p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>Retry with a different prompt</li>
                    <li>Change the target selection</li>
                    <li>Switch to a different model</li>
                    <li>Check capabilities below</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {editorState.qualityResult && (
            <div className="p-4 border-b border-gray-800">
              <h3 className="font-medium mb-2">Quality Score</h3>
              <div className="text-3xl font-bold mb-1">{Math.round((editorState.qualityResult.overall || 0) * 100)}%</div>
              <div className="text-sm text-gray-400 mb-2">Passed: {editorState.qualityResult.passed ? 'Yes' : 'No'}</div>
              {editorState.qualityResult.issues?.length > 0 && (
                <div className="text-xs text-red-400 space-y-1">
                  {editorState.qualityResult.issues.slice(0, 5).map((issue: string, i: number) => (
                    <div key={i}>• {issue}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {capabilities && (
            <div className="p-4 border-b border-gray-800">
              <h3 className="font-medium mb-2">System Capabilities</h3>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span>FFmpeg</span>
                  <span className={capabilities.ffmpeg?.available ? 'text-green-400' : 'text-red-400'}>
                    {capabilities.ffmpeg?.available ? 'Available' : 'Unavailable'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>GPU</span>
                  <span className={capabilities.gpu?.available ? 'text-green-400' : 'text-yellow-400'}>
                    {capabilities.gpu?.available ? 'Available' : 'Not detected'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Segmentation</span>
                  <span className={capabilities.segmentation?.any_available ? 'text-green-400' : 'text-red-400'}>
                    {capabilities.segmentation?.any_available ? 'Available' : 'Unavailable'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Providers</span>
                  <span className={capabilities.providers?.any_available ? 'text-green-400' : 'text-red-400'}>
                    {Object.keys(capabilities.providers?.providers || {}).filter((k: string) => capabilities.providers?.providers[k]?.available).length} active
                  </span>
                </div>
              </div>
            </div>
          )}

          <div className="p-4">
            <h3 className="font-medium mb-2">Quick Actions</h3>
            <div className="space-y-1">
              <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-2">
                <Camera className="w-4 h-4" /> Camera Controls
              </button>
              <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-2">
                <Volume2 className="w-4 h-4" /> Audio
              </button>
              <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-2">
                <Type className="w-4 h-4" /> Captions
              </button>
              <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-2">
                <Palette className="w-4 h-4" /> Color / Look
              </button>
              <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-2">
                <Scissors className="w-4 h-4" /> Keyframes
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
