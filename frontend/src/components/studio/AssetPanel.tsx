import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { FolderOpen, Users, Package, Image } from 'lucide-react'
import api from '../../services/api'

type Tab = 'assets' | 'characters' | 'products' | 'references'

interface AssetPanelProps {
  projectId: string
  activeTab: Tab
  selectedAssetId: string | null
  onAssetSelect: (id: string) => void
  onTabChange: (tab: Tab) => void
}

export default function AssetPanel({ projectId, activeTab, selectedAssetId, onAssetSelect, onTabChange }: AssetPanelProps) {
  const { data: assets } = useQuery({
    queryKey: ['assets', projectId],
    queryFn: async () => (await api.get(`/assets/project/${projectId}`)).data,
    enabled: !!projectId && activeTab === 'assets',
  })

  const { data: characters } = useQuery({
    queryKey: ['characters'],
    queryFn: async () => (await api.get('/phase9/characters')).data,
    enabled: activeTab === 'characters',
  })

  const { data: products } = useQuery({
    queryKey: ['products'],
    queryFn: async () => (await api.get('/phase9/products')).data,
    enabled: activeTab === 'products',
  })

  return (
    <div className="h-full flex flex-col">
      <div className="flex border-b border-gray-800">
          {[
            { id: 'assets', label: 'Assets', icon: FolderOpen },
            { id: 'characters', label: 'Characters', icon: Users },
            { id: 'products', label: 'Products', icon: Package },
            { id: 'references', label: 'Refs', icon: Image },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id as Tab)}
              className={`flex-1 py-2 text-xs capitalize flex items-center justify-center gap-1 ${activeTab === tab.id ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white'}`}
            >
              <tab.icon className="w-3 h-3" /> {tab.label}
            </button>
          ))}
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {activeTab === 'assets' && (
          <div className="space-y-1">
            {assets?.map((asset: any) => (
              <button
                key={asset.id}
                onClick={() => onAssetSelect(asset.id)}
                className={`w-full text-left p-2 rounded-lg text-sm ${selectedAssetId === asset.id ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`}
              >
                <div className="flex items-center gap-2">
                  <FolderOpen className="w-4 h-4 flex-shrink-0" />
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
        {activeTab === 'characters' && (
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
        {activeTab === 'products' && (
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
        {activeTab === 'references' && (
          <div className="space-y-1">
            {assets?.filter((a: any) => a.id !== selectedAssetId).map((asset: any) => (
              <button
                key={asset.id}
                onClick={() => onAssetSelect(asset.id)}
                className={`w-full text-left p-2 rounded-lg text-sm ${selectedAssetId === asset.id ? 'bg-yellow-600' : 'bg-gray-800 hover:bg-gray-700'}`}
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
  )
}
