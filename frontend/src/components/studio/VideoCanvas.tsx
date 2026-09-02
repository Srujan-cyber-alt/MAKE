import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Monitor, AlertCircle, CheckCircle2, Loader2, Activity } from 'lucide-react'
import api from '../../services/api'

interface VideoCanvasProps {
  selectedAssetId: string | null
}

export default function VideoCanvas({ selectedAssetId }: VideoCanvasProps) {
  return (
    <div className="flex-1 flex items-center justify-center p-6 bg-black min-h-0">
      {selectedAssetId ? (
        <video
          src={`/api/v1/files/${selectedAssetId}`}
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
  )
}
