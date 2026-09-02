import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Eye, Activity } from 'lucide-react'
import api from '../../services/api'

interface VisionPanelProps {
  assetId: string | null
}

export default function VisionPanel({ assetId }: VisionPanelProps) {
  const { data: runtime } = useQuery({
    queryKey: ['vision-runtime'],
    queryFn: async () => (await api.get('/vision/runtime')).data,
  })

  const { data: analysis } = useQuery({
    queryKey: ['vision-analysis', assetId],
    queryFn: async () => {
      if (!assetId) return null
      const res = await api.get(`/vision/assets/${assetId}/analysis`)
      return res.data
    },
    enabled: !!assetId,
  })

  if (!runtime) {
    return (
      <div className="p-4">
        <h3 className="font-medium mb-2 flex items-center gap-2">
          <Eye className="w-4 h-4" /> Vision
        </h3>
        <p className="text-xs text-gray-500">Loading vision capabilities...</p>
      </div>
    )
  }

  const capabilities = runtime.capabilities || {}
  const availableCount = Object.values(capabilities).filter((v: any) => String(v) === 'available').length

  return (
    <div className="p-4">
      <h3 className="font-medium mb-2 flex items-center gap-2">
        <Eye className="w-4 h-4" /> Vision
      </h3>
      <div className="space-y-1 text-xs mb-3">
        {Object.entries(capabilities).slice(0, 6).map(([key, value]) => (
          <div key={key} className="flex justify-between">
            <span className="capitalize">{key.replace(/_/g, ' ')}</span>
            <span className={String(value) === 'available' ? 'text-green-400' : 'text-red-400'}>
              {String(value)}
            </span>
          </div>
        ))}
      </div>
      {analysis && (
        <div className="mt-3 p-2 bg-gray-800 rounded text-xs">
          <div className="flex items-center gap-1 mb-1">
            <Activity className="w-3 h-3" />
            <span className="font-medium">Analysis</span>
          </div>
          <div className="text-gray-400">
            Status: {analysis.status}
          </div>
        </div>
      )}
    </div>
  )
}
