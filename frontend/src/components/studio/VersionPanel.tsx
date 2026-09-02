import React from 'react'
import { GitBranch, RotateCcw, Copy, Trash2, Eye, EyeOff, CheckCircle2, AlertCircle } from 'lucide-react'

interface Version {
  id: string
  version_number: string
  name: string
  description: string
  created_at: string
}

interface VersionPanelProps {
  versions: Version[]
  onRestore: (id: string) => void
  onCompare: (id: string) => void
}

export default function VersionPanel({ versions, onRestore, onCompare }: VersionPanelProps) {
  return (
    <div className="p-4">
      <h3 className="font-medium mb-3 flex items-center gap-2">
        <GitBranch className="w-4 h-4" /> Versions
      </h3>
      <div className="space-y-2">
        {versions?.length > 0 ? (
          versions.map((v) => (
            <div key={v.id} className="bg-gray-800 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">{v.name}</div>
                  <div className="text-xs text-gray-400">v{v.version_number} • {new Date(v.created_at).toLocaleDateString()}</div>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => onCompare(v.id)} className="p-1 hover:bg-gray-700 rounded" title="Compare">
                    <Eye className="w-3 h-3" />
                  </button>
                  <button onClick={() => onRestore(v.id)} className="p-1 hover:bg-gray-700 rounded" title="Restore">
                    <RotateCcw className="w-3 h-3" />
                  </button>
                </div>
              </div>
              {v.description && <div className="text-xs text-gray-500 mt-1">{v.description}</div>}
            </div>
          ))
        ) : (
          <p className="text-xs text-gray-500 text-center py-4">No versions yet</p>
        )}
      </div>
    </div>
  )
}
