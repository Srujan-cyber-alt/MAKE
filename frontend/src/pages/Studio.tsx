import React, { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../services/api'
import StudioHeader from '../components/studio/StudioHeader'
import AssetPanel from '../components/studio/AssetPanel'
import VideoCanvas from '../components/studio/VideoCanvas'
import CreateBar from '../components/studio/CreateBar'
import Timeline from '../components/studio/Timeline'
import StatusPanel from '../components/studio/StatusPanel'
import VisionPanel from '../components/studio/VisionPanel'
import { ModelExplorer } from '../components/studio/ModelExplorer'
import { RoutingInspector } from '../components/studio/RoutingInspector'

type CreationMode = 'create' | 'edit' | 'transform' | 'animate' | 'extend' | 'remix' | 'auto'
type Tab = 'assets' | 'characters' | 'products' | 'references'
type RightPanelTab = 'status' | 'vision' | 'models' | 'routing'

export default function Studio() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const pid = projectId || ''

  const [mode, setMode] = useState<CreationMode>('auto')
  const [command, setCommand] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentStage, setCurrentStage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('assets')
  const [rightPanelTab, setRightPanelTab] = useState<RightPanelTab>('status')

  const { data: project } = useQuery({
    queryKey: ['project', pid],
    queryFn: async () => (await api.get(`/projects/${pid}`)).data,
    enabled: !!pid,
  })

  const { data: assets } = useQuery({
    queryKey: ['assets', pid],
    queryFn: async () => (await api.get(`/assets/project/${pid}`)).data,
    enabled: !!pid,
  })

  const { data: capabilities } = useQuery({
    queryKey: ['capabilities'],
    queryFn: async () => (await api.get('/phase9/capabilities')).data,
  })

  const executeMutation = useMutation({
    mutationFn: async () => {
      setCurrentStage('Analyzing command...')
      setProgress(5)
      setError(null)
      const res = await api.post(`/studio/projects/${pid}/command`, {
        command,
        mode,
        context: {
          source_asset_id: selectedAssetId,
          source_asset_ids: selectedAssetId ? [selectedAssetId] : [],
        },
      })
      return res.data
    },
    onSuccess: (data) => {
      setCurrentStage('Completed')
      setProgress(100)
      setError(data.error || null)
      setIsProcessing(false)
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    },
    onError: (err: any) => {
      setCurrentStage('Failed')
      setError(err.response?.data?.detail || 'Command execution failed')
      setIsProcessing(false)
    },
  })

  const handleExecute = useCallback(() => {
    if (!command.trim()) return
    setIsProcessing(true)
    executeMutation.mutate()
  }, [command, mode, selectedAssetId])

  const handleCancel = useCallback(() => {
    setIsProcessing(false)
    setCurrentStage('Cancelled')
    setProgress(0)
  }, [])

  const handleNewCommand = useCallback(() => {
    setCommand('')
    setCurrentStage('')
    setProgress(0)
    setError(null)
  }, [])

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white">
      <StudioHeader
        projectName={project?.name || 'Project'}
        currentStage={currentStage}
        isProcessing={isProcessing}
        error={error}
        progress={progress}
        onNewCommand={handleNewCommand}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* LEFT PANEL */}
        <div className="w-64 border-r border-gray-800 flex-shrink-0">
          <AssetPanel
            projectId={pid}
            activeTab={activeTab}
            selectedAssetId={selectedAssetId}
            onAssetSelect={(id) => setSelectedAssetId(selectedAssetId === id ? null : id)}
            onTabChange={setActiveTab}
          />
        </div>

        {/* CENTER */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <VideoCanvas selectedAssetId={selectedAssetId} />
          <CreateBar
            mode={mode}
            command={command}
            isProcessing={isProcessing}
            onModeChange={setMode}
            onCommandChange={setCommand}
            onExecute={handleExecute}
            onCancel={handleCancel}
          />
          <Timeline
            assets={assets}
            onAssetSelect={setSelectedAssetId}
          />
        </div>

        {/* RIGHT PANEL */}
        <div className="w-80 border-l border-gray-800 flex-shrink-0 overflow-y-auto">
          <div className="flex border-b border-gray-800">
            <button onClick={() => setRightPanelTab('status')} className={`flex-1 px-2 py-1 text-xs ${rightPanelTab === 'status' ? 'bg-gray-700 text-white' : 'text-gray-400'}`}>Status</button>
            <button onClick={() => setRightPanelTab('vision')} className={`flex-1 px-2 py-1 text-xs ${rightPanelTab === 'vision' ? 'bg-gray-700 text-white' : 'text-gray-400'}`}>Vision</button>
            <button onClick={() => setRightPanelTab('models')} className={`flex-1 px-2 py-1 text-xs ${rightPanelTab === 'models' ? 'bg-gray-700 text-white' : 'text-gray-400'}`}>Models</button>
            <button onClick={() => setRightPanelTab('routing')} className={`flex-1 px-2 py-1 text-xs ${rightPanelTab === 'routing' ? 'bg-gray-700 text-white' : 'text-gray-400'}`}>Routing</button>
          </div>
          {rightPanelTab === 'status' && (
            <StatusPanel
              currentStage={currentStage}
              isProcessing={isProcessing}
              progress={progress}
              error={error}
              capabilities={capabilities}
            />
          )}
          {rightPanelTab === 'vision' && <VisionPanel assetId={selectedAssetId} />}
          {rightPanelTab === 'models' && <ModelExplorer />}
          {rightPanelTab === 'routing' && <RoutingInspector />}
        </div>
      </div>
    </div>
  )
}
