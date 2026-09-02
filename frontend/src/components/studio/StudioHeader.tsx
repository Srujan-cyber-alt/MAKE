import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Film, Loader2, CheckCircle2, AlertCircle, XCircle, Activity, Download, Undo2, Redo2, GitBranch } from 'lucide-react'

interface StudioHeaderProps {
  projectName: string
  currentStage: string
  isProcessing: boolean
  error: string | null
  progress: number
  onNewCommand: () => void
}

export default function StudioHeader({ projectName, currentStage, isProcessing, error, progress, onNewCommand }: StudioHeaderProps) {
  const navigate = useNavigate()

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
    <div className="h-14 border-b border-gray-800 flex items-center justify-between px-4 flex-shrink-0">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(`/projects`)} className="p-2 hover:bg-gray-800 rounded-lg">
          <Film className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-lg font-bold">Studio</h1>
          <p className="text-xs text-gray-400">{projectName || 'Project'}</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${getStageColor(currentStage)} bg-gray-800/50`}>
          <StageIcon className={`w-4 h-4 ${isProcessing ? 'animate-spin' : ''}`} />
          <span className="text-sm font-medium">{currentStage || 'Ready'}</span>
        </div>
        {isProcessing && (
          <div className="w-32 h-2 bg-gray-700 rounded-full">
            <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${progress}%` }} />
          </div>
        )}
        {error && (
          <div className="text-xs text-red-400 max-w-xs truncate">{error}</div>
        )}
        <div className="flex gap-1">
          <button className="p-2 hover:bg-gray-800 rounded-lg" title="Undo">
            <Undo2 className="w-4 h-4" />
          </button>
          <button className="p-2 hover:bg-gray-800 rounded-lg" title="Redo">
            <Redo2 className="w-4 h-4" />
          </button>
          <button className="p-2 hover:bg-gray-800 rounded-lg" title="Versions">
            <GitBranch className="w-4 h-4" />
          </button>
        </div>
        {!isProcessing && currentStage && (
          <button onClick={onNewCommand} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm">
            New
          </button>
        )}
      </div>
    </div>
  )
}
