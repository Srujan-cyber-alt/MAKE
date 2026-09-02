import React from 'react'
import { Play, Pause } from 'lucide-react'

interface TimelineProps {
  assets: any[]
  onAssetSelect: (id: string) => void
}

export default function Timeline({ assets, onAssetSelect }: TimelineProps) {
  return (
    <div className="h-32 border-t border-gray-800 flex-shrink-0 bg-gray-900/50">
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between px-4 py-1 border-b border-gray-800">
          <div className="text-xs text-gray-500 font-medium">TIMELINE</div>
          <div className="flex gap-1">
            <button className="p-1 hover:bg-gray-800 rounded">
              <Play className="w-3 h-3" />
            </button>
            <button className="p-1 hover:bg-gray-800 rounded">
              <Pause className="w-3 h-3" />
            </button>
          </div>
        </div>
        <div className="flex-1 flex items-center px-4 gap-2 overflow-x-auto">
          {assets?.slice(0, 10).map((asset: any) => (
            <div
              key={asset.id}
              onClick={() => onAssetSelect(asset.id)}
              className="w-32 h-16 bg-purple-600/20 border border-purple-600/40 rounded flex items-center justify-center flex-shrink-0 cursor-pointer hover:bg-purple-600/30"
            >
              <span className="text-xs text-purple-400 truncate px-2 text-center">{asset.filename}</span>
            </div>
          ))}
          {(!assets || assets.length === 0) && (
            <span className="text-xs text-gray-600">Add assets to see timeline</span>
          )}
        </div>
      </div>
    </div>
  )
}
