import React from 'react'
import { Activity, CheckCircle2, AlertCircle, XCircle, Loader2, ShieldCheck, Layers } from 'lucide-react'

interface StatusPanelProps {
  currentStage: string
  isProcessing: boolean
  progress: number
  error: string | null
  capabilities: any
}

export default function StatusPanel({ currentStage, isProcessing, progress, error, capabilities }: StatusPanelProps) {
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
    if (isProcessing) return Loader2
    return Activity
  }

  const StageIcon = getStageIcon(currentStage)

  return (
    <div className="h-full flex flex-col">
      {/* Status */}
      <div className="p-4 border-b border-gray-800">
        <h3 className="font-medium mb-2 flex items-center gap-2">
          <Activity className="w-4 h-4" /> Status
        </h3>
        <div className={`flex items-center gap-2 mb-2 ${getStageColor(currentStage)}`}>
          <StageIcon className={`w-5 h-5 ${isProcessing ? 'animate-spin' : ''}`} />
          <span className="font-medium">{currentStage || 'Ready'}</span>
        </div>
        {isProcessing && (
          <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
            <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${progress}%` }} />
          </div>
        )}
        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mt-2">
            <div className="text-red-400 font-medium text-sm">Error</div>
            <div className="text-red-300 text-xs mt-1">{error}</div>
          </div>
        )}
      </div>

      {/* Capabilities */}
      {capabilities && (
        <div className="p-4 border-b border-gray-800">
          <h3 className="font-medium mb-2 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" /> System
          </h3>
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
        <h3 className="font-medium mb-2 flex items-center gap-2">
          <Layers className="w-4 h-4" /> Tools
        </h3>
        <div className="space-y-1">
          <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">Camera Controls</button>
          <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">Audio</button>
          <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">Captions</button>
          <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">Color / Look</button>
          <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">VFX</button>
          <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">Quality Check</button>
          <button className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">Export</button>
        </div>
      </div>
    </div>
  )
}
