import React, { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Film, Sparkles, Wand2, PlayCircle, PauseCircle, XCircle, CheckCircle2,
  AlertCircle, Loader2, Download, Undo2, Redo2, Copy, Trash2, Scissors,
  PlusCircle, RefreshCw, Settings2, Command, Zap, ShieldCheck, Layers,
  Volume2, Type, Palette, Camera, Users, Package, Image, FolderOpen,
  ChevronRight, ChevronDown, Maximize, Minimize, History, GitBranch,
  Monitor, Smartphone, Tv, Globe, Hash, Clock, Gauge, Activity
} from 'lucide-react'
import api from '../services/api'

type CreationMode = 'create' | 'edit' | 'transform' | 'animate' | 'extend' | 'remix' | 'auto'

interface StudioState {
  mode: CreationMode
  command: string
  isProcessing: boolean
  progress: number
  currentStage: string
  result: any
  error: string | null
  selectedAssetId: string | null
  activeLeftTab: 'assets' | 'characters' | 'products' | 'references'
  showShotInspector: boolean
  timelineZoom: number
  selectedShotId: string | null
}

const EXAMPLE_COMMANDS = [
  "Create a cinematic 30-second luxury watch commercial",
  "Remove the person in the background",
  "Make the camera orbit around the product",
  "Turn this image into a cinematic video",
  "Extend this scene by 5 seconds",
  "Make this look like a Hollywood trailer",
  "Replace the background with a futuristic city",
  "Create 4 different versions",
]

export default function Studio() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [state, setState] = useState<StudioState>({
    mode: 'auto',
    command: '',
    isProcessing: false,
    progress: 0,
    currentStage: '',
    result: null,
    error: null,
    selectedAssetId: null,
    activeLeftTab: 'assets',
    showShotInspector: false,
    timelineZoom: 1,
    selectedShotId: null,
  })

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}`)).data,
    enabled: !!projectId,
  })

  const { data: assets } = useQuery({
    queryKey: ['assets', projectId],
    queryFn: async () => (await api.get(`/assets/project/${projectId}`)).data,
    enabled: !!projectId,
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

  const executeMutation = useMutation({
    mutationFn: async () => {
      setState(s => ({ ...s, isProcessing: true, progress: 5, currentStage: 'Analyzing command...', error: null }))
      const res = await api.post(`/studio/projects/${projectId}/command`, {
        command: state.command,
        mode: state.mode,
        context: {
          source_asset_id: state.selectedAssetId,
          source_asset_ids: state.selectedAssetId ? [state.selectedAssetId] : [],
        },
      })
      return res.data
    },
    onSuccess: (data) => {
      setState(s => ({
        ...s,
        result: data,
        isProcessing: false,
        progress: 100,
        currentStage: 'Completed',
        error: data.error || null,
      }))
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    },
    onError: (err: any) => {
      setState(s => ({
        ...s,
        isProcessing: false,
        error: err.response?.data?.detail || 'Command execution failed',
        currentStage: 'Failed',
      }))
    },
  })

  const handleExecute = useCallback(() => {
    if (!state.command.trim()) return
    executeMutation.mutate()
  }, [state.command, state.mode, state.selectedAssetId])

  const handleCancel = useCallback(() => {
    setState(s => ({
      ...s,
      isProcessing: false,
      currentStage: 'Cancelled',
      progress: 0,
    }))
  }, [])

  const handleModeChange = useCallback((mode: CreationMode) => {
    setState(s => ({ ...s, mode }))
  }, [])

  const handleAssetSelect = useCallback((assetId: string) => {
    setState(s => ({ ...s, selectedAssetId: s.selectedAssetId === assetId ? null : assetId }))
  }, [])

  const handleExampleClick = useCallback((example: string) => {
    setState(s => ({ ...s, command: example }))
  }, [])

  const getStageColor = (stage: string) => {
    if (stage.includes('Completed') || stage.includes('completed')) return 'text-green-400'
    if (stage.includes('Failed') || stage.includes('error')) return 'text-red-400'
    if (stage.includes('Cancelled')) return 'text-gray-400'
    return 'text-blue-400'
  }

  const getStageIcon = (stage: string) => {
    if (stage.includes('Completed') || stage.includes('completed')) return CheckCircle2
    if (stage.includes('Failed') || stage.includes('error')) return AlertCircle
    if (stage.includes('Cancelled')) return XCircle
    if (state.isProcessing) return Loader2
    return Sparkles
  }

  const StageIcon = getStageIcon(state.currentStage)

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white">
      {/* TOP BAR */}
      <div className="h-14 border-b border-gray-800 flex items-center justify-between px-4 flex-shrink-0">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(`/projects/${projectId}`)} className="p-2 hover:bg-gray-800 rounded-lg">
            <Film className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-bold">Studio</h1>
            <p className="text-xs text-gray-400">{project?.name || 'Project'}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${getStageColor(state.currentStage)} bg-gray-800/50`}>
            <StageIcon className={`w-4 h-4 ${state.isProcessing ? 'animate-spin' : ''}`} />
            <span className="text-sm font-medium">{state.currentStage || 'Ready'}</span>
          </div>
          {state.isProcessing && (
            <button onClick={handleCancel} className="px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded-lg text-sm flex items-center gap-1">
              <XCircle className="w-4 h-4" /> Cancel
            </button>
          )}
          {state.result && !state.error && (
            <button onClick={() => setState(s => ({ ...s, result: null, progress: 0, currentStage: '' }))} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm">
              New Command
            </button>
          )}
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT PANEL */}
        <div className="w-64 border-r border-gray-800 flex flex-col flex-shrink-0">
          <div className="flex border-b border-gray-800">
            {([
              { id: 'assets', label: 'Assets', icon: FolderOpen },
              { id: 'characters', label: 'Characters', icon: Users },
              { id: 'products', label: 'Products', icon: Package },
              { id: 'references', label: 'Refs', icon: Image },
            ] as const).map(tab => (
              <button
                key={tab.id}
                onClick={() => setState(s => ({ ...s, activeLeftTab: tab.id }))}
                className={`flex-1 py-2 text-xs capitalize flex items-center justify-center gap-1 ${state.activeLeftTab === tab.id ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white'}`}
              >
                <tab.icon className="w-3 h-3" /> {tab.label}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {state.activeLeftTab === 'assets' && (
              <div className="space-y-1">
                {assets?.map((asset: any) => (
                  <button
                    key={asset.id}
                    onClick={() => handleAssetSelect(asset.id)}
                    className={`w-full text-left p-2 rounded-lg text-sm ${state.selectedAssetId === asset.id ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`}
                  >
                    <div className="flex items-center gap-2">
                      <Film className="w-4 h-4 flex-shrink-0" />
                      <span className="truncate">{asset.filename}</span>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {asset.asset_type} • {asset.duration_seconds ? `${asset.duration_seconds.toFixed(1)}s` : ''}
                    </div>
                  </button>
                ))}
                {(!assets || assets.length === 0) && (
                  <p className="text-xs text-gray-500 text-center py-4">No assets yet</p>
                )}
              </div>
            )}
            {state.activeLeftTab === 'characters' && (
              <div className="space-y-1">
                {characters?.map((char: any) => (
                  <button key={char.id} className="w-full text-left p-2 rounded-lg text-sm bg-gray-800 hover:bg-gray-700">
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4" />
                      <span>{char.name}</span>
                    </div>
                  </button>
                ))}
                {(!characters || characters.length === 0) && (
                  <p className="text-xs text-gray-500 text-center py-4">No characters yet</p>
                )}
              </div>
            )}
            {state.activeLeftTab === 'products' && (
              <div className="space-y-1">
                {products?.map((prod: any) => (
                  <button key={prod.id} className="w-full text-left p-2 rounded-lg text-sm bg-gray-800 hover:bg-gray-700">
                    <div className="flex items-center gap-2">
                      <Package className="w-4 h-4" />
                      <span>{prod.name}</span>
                    </div>
                  </button>
                ))}
                {(!products || products.length === 0) && (
                  <p className="text-xs text-gray-500 text-center py-4">No products yet</p>
                )}
              </div>
            )}
            {state.activeLeftTab === 'references' && (
              <div className="space-y-1">
                {assets?.filter((a: any) => a.id !== state.selectedAssetId).map((asset: any) => (
                  <button
                    key={asset.id}
                    onClick={() => handleAssetSelect(asset.id)}
                    className={`w-full text-left p-2 rounded-lg text-sm ${state.selectedAssetId === asset.id ? 'bg-yellow-600' : 'bg-gray-800 hover:bg-gray-700'}`}
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

        {/* CENTER - Canvas + Create Bar */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Video Canvas */}
          <div className="flex-1 flex items-center justify-center p-6 bg-black min-h-0">
            {state.selectedAssetId ? (
              <video
                src={`/api/v1/files/${state.selectedAssetId}`}
                className="max-w-full max-h-full rounded-lg"
                controls
              />
            ) : (
              <div className="text-center">
                <Monitor className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-500">Select an asset or enter a command to begin</p>
              </div>
            )}
          </div>

          {/* Create Bar */}
          <div className="border-t border-gray-800 p-4 flex-shrink-0">
            {/* Mode Selector */}
            <div className="flex gap-2 mb-3">
              {([
                { id: 'auto', label: 'Auto', icon: Wand2 },
                { id: 'create', label: 'Create', icon: Sparkles },
                { id: 'edit', label: 'Edit', icon: Scissors },
                { id: 'transform', label: 'Transform', icon: RefreshCw },
                { id: 'animate', label: 'Animate', icon: PlayCircle },
                { id: 'extend', label: 'Extend', icon: PlusCircle },
                { id: 'remix', label: 'Remix', icon: Copy },
              ] as const).map(mode => (
                <button
                  key={mode.id}
                  onClick={() => handleModeChange(mode.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1 ${state.mode === mode.id ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}
                >
                  <mode.icon className="w-3 h-3" /> {mode.label}
                </button>
              ))}
            </div>

            {/* Command Input */}
            <div className="relative">
              <Command className="absolute left-3 top-3 w-4 h-4 text-gray-500" />
              <textarea
                value={state.command}
                onChange={(e) => setState(s => ({ ...s, command: e.target.value }))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault()
                    handleExecute()
                  }
                }}
                placeholder="Describe what you want to create or edit... (Cmd+Enter to execute)"
                className="w-full bg-gray-800 rounded-lg pl-10 pr-4 py-3 h-20 resize-none border border-gray-700 focus:border-purple-500 focus:outline-none text-sm"
              />
            </div>

            {/* Example Commands + Execute */}
            <div className="flex items-center justify-between mt-3">
              <div className="flex flex-wrap gap-1">
                {EXAMPLE_COMMANDS.slice(0, 4).map(example => (
                  <button
                    key={example}
                    onClick={() => handleExampleClick(example)}
                    className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded-full text-gray-300"
                  >
                    {example}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                {state.isProcessing && (
                  <button onClick={handleCancel} className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm flex items-center gap-1">
                    <XCircle className="w-4 h-4" /> Cancel
                  </button>
                )}
                <button
                  onClick={handleExecute}
                  disabled={!state.command.trim() || executeMutation.isPending}
                  className="px-6 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-sm font-medium flex items-center gap-2"
                >
                  {executeMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  {executeMutation.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </div>
          </div>

          {/* Timeline */}
          <div className="h-32 border-t border-gray-800 flex-shrink-0 bg-gray-900/50">
            <div className="h-full flex items-center px-4 gap-2">
              <div className="text-xs text-gray-500 mr-2">Timeline</div>
              <div className="flex-1 h-16 bg-gray-800/50 rounded-lg border border-gray-700/50 flex items-center px-4 gap-2 overflow-x-auto">
                {assets?.slice(0, 5).map((asset: any) => (
                  <div
                    key={asset.id}
                    className="w-24 h-10 bg-purple-600/20 border border-purple-600/40 rounded flex items-center justify-center flex-shrink-0"
                  >
                    <span className="text-xs text-purple-400 truncate px-1">{asset.filename}</span>
                  </div>
                ))}
                {(!assets || assets.length === 0) && (
                  <span className="text-xs text-gray-600">Add assets to see timeline</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="w-80 border-l border-gray-800 flex flex-col flex-shrink-0 overflow-y-auto">
          {/* Status */}
          <div className="p-4 border-b border-gray-800">
            <h3 className="font-medium mb-2 flex items-center gap-2">
              <Activity className="w-4 h-4" /> Status
            </h3>
            <div className={`flex items-center gap-2 mb-2 ${getStageColor(state.currentStage)}`}>
              <StageIcon className={`w-5 h-5 ${state.isProcessing ? 'animate-spin' : ''}`} />
              <span className="font-medium">{state.currentStage || 'Ready'}</span>
            </div>
            {state.isProcessing && (
              <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
                <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${state.progress}%` }} />
              </div>
            )}
            {state.error && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mt-2">
                <div className="text-red-400 font-medium text-sm">Error</div>
                <div className="text-red-300 text-xs mt-1">{state.error}</div>
              </div>
            )}
          </div>

          {/* Capabilities */}
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
                  <span>Providers</span>
                  <span className={capabilities.providers?.any_available ? 'text-green-400' : 'text-red-400'}>
                    {Object.keys(capabilities.providers?.providers || {}).filter((k: string) => capabilities.providers?.providers[k]?.available).length} active
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Quick Actions */}
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
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
