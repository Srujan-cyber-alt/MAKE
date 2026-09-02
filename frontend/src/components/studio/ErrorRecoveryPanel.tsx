import React from 'react'
import { AlertTriangle, RefreshCw, Copy, Wrench, Lightbulb } from 'lucide-react'

interface ErrorRecoveryPanelProps {
  error: string | null
  onRetry: () => void
  onRetryModel: () => void
  onRepair: () => void
}

export default function ErrorRecoveryPanel({ error, onRetry, onRetryModel, onRepair }: ErrorRecoveryPanelProps) {
  if (!error) return null

  return (
    <div className="p-4 border-t border-gray-800">
      <h3 className="font-medium mb-2 flex items-center gap-2 text-red-400">
        <AlertTriangle className="w-4 h-4" /> Error Recovery
      </h3>
      <div className="bg-red-900/20 border border-red-800 rounded-lg p-3 mb-3">
        <p className="text-sm text-red-300">{error}</p>
      </div>
      <div className="space-y-2">
        <button onClick={onRetry} className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-2">
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
        <button onClick={onRetryModel} className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-2">
          <Copy className="w-4 h-4" /> Retry with different model
        </button>
        <button onClick={onRepair} className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-2">
          <Wrench className="w-4 h-4" /> Auto Repair
        </button>
      </div>
    </div>
  )
}
