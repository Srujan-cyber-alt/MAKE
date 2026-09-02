import React from 'react'
import { Camera, Gauge, Type, Palette, Users, Package } from 'lucide-react'

interface ShotInspectorProps {
  shot: any
  onUpdate: (field: string, value: any) => void
}

export default function ShotInspector({ shot, onUpdate }: ShotInspectorProps) {
  if (!shot) {
    return (
      <div className="p-4">
        <h3 className="font-medium mb-2">Shot Inspector</h3>
        <p className="text-xs text-gray-500">Select a shot to inspect</p>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      <h3 className="font-medium mb-2">Shot Inspector</h3>

      <div>
        <label className="text-xs text-gray-400 mb-1 block">Prompt</label>
        <textarea
          value={shot.prompt || ''}
          onChange={(e) => onUpdate('prompt', e.target.value)}
          className="w-full bg-gray-800 rounded p-2 text-xs border border-gray-700 focus:border-purple-500 focus:outline-none"
          rows={3}
        />
      </div>

      <div>
        <label className="text-xs text-gray-400 mb-1 block">Negative Prompt</label>
        <textarea
          value={shot.negative_prompt || ''}
          onChange={(e) => onUpdate('negative_prompt', e.target.value)}
          className="w-full bg-gray-800 rounded p-2 text-xs border border-gray-700 focus:border-purple-500 focus:outline-none"
          rows={2}
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Duration (s)</label>
          <input
            type="number"
            value={shot.duration_seconds || 5}
            onChange={(e) => onUpdate('duration_seconds', parseFloat(e.target.value))}
            className="w-full bg-gray-800 rounded p-2 text-xs border border-gray-700 focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Aspect Ratio</label>
          <select
            value={shot.aspect_ratio || '16:9'}
            onChange={(e) => onUpdate('aspect_ratio', e.target.value)}
            className="w-full bg-gray-800 rounded p-2 text-xs border border-gray-700 focus:border-purple-500 focus:outline-none"
          >
            <option value="16:9">16:9</option>
            <option value="9:16">9:16</option>
            <option value="1:1">1:1</option>
            <option value="4:5">4:5</option>
          </select>
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-400 mb-1 block flex items-center gap-1">
          <Camera className="w-3 h-3" /> Camera Movement
        </label>
        <select
          value={shot.camera_movement || 'static'}
          onChange={(e) => onUpdate('camera_movement', e.target.value)}
          className="w-full bg-gray-800 rounded p-2 text-xs border border-gray-700 focus:border-purple-500 focus:outline-none"
        >
          <option value="static">Static</option>
          <option value="pan">Pan</option>
          <option value="tilt">Tilt</option>
          <option value="zoom">Zoom</option>
          <option value="dolly">Dolly</option>
          <option value="track">Tracking</option>
          <option value="orbit">Orbit</option>
          <option value="crane">Crane</option>
          <option value="handheld">Handheld</option>
        </select>
      </div>

      <div>
        <label className="text-xs text-gray-400 mb-1 block flex items-center gap-1">
          <Gauge className="w-3 h-3" /> Motion Intensity
        </label>
        <input
          type="range"
          min="0"
          max="100"
          value={shot.motion_intensity || 50}
          onChange={(e) => onUpdate('motion_intensity', parseInt(e.target.value))}
          className="w-full"
        />
      </div>

      <div>
        <label className="text-xs text-gray-400 mb-1 block flex items-center gap-1">
          <Palette className="w-3 h-3" /> Style
        </label>
        <select
          value={shot.style || 'cinematic'}
          onChange={(e) => onUpdate('style', e.target.value)}
          className="w-full bg-gray-800 rounded p-2 text-xs border border-gray-700 focus:border-purple-500 focus:outline-none"
        >
          <option value="cinematic">Cinematic</option>
          <option value="commercial">Commercial</option>
          <option value="documentary">Documentary</option>
          <option value="music_video">Music Video</option>
          <option value="social">Social Media</option>
        </select>
      </div>
    </div>
  )
}
