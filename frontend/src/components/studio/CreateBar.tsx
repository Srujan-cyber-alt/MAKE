import React, { useCallback } from 'react'
import { Sparkles, Wand2, PlayCircle, Scissors, RefreshCw, PlusCircle, Copy, XCircle, Loader2, Command } from 'lucide-react'

type CreationMode = 'create' | 'edit' | 'transform' | 'animate' | 'extend' | 'remix' | 'auto'

interface CreateBarProps {
  mode: CreationMode
  command: string
  isProcessing: boolean
  onModeChange: (mode: CreationMode) => void
  onCommandChange: (cmd: string) => void
  onExecute: () => void
  onCancel: () => void
}

const MODES = [
  { id: 'auto', label: 'Auto', icon: Wand2 },
  { id: 'create', label: 'Create', icon: Sparkles },
  { id: 'edit', label: 'Edit', icon: Scissors },
  { id: 'transform', label: 'Transform', icon: RefreshCw },
  { id: 'animate', label: 'Animate', icon: PlayCircle },
  { id: 'extend', label: 'Extend', icon: PlusCircle },
  { id: 'remix', label: 'Remix', icon: Copy },
] as const

const EXAMPLE_COMMANDS = [
  "Create a cinematic 30-second luxury watch commercial",
  "Remove the person in the background",
  "Make the camera orbit around the product",
  "Turn this image into a cinematic video",
  "Extend this scene by 5 seconds",
  "Make this look like a Hollywood trailer",
  "Replace the background with a futuristic city",
  "Create 4 different versions",
]

export default function CreateBar({
  mode, command, isProcessing,
  onModeChange, onCommandChange, onExecute, onCancel
}: CreateBarProps) {
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      onExecute()
    }
  }, [onExecute])

  return (
    <div className="border-t border-gray-800 p-4 flex-shrink-0">
      {/* Mode Selector */}
      <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
        {MODES.map(m => (
          <button
            key={m.id}
            onClick={() => onModeChange(m.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1 whitespace-nowrap ${mode === m.id ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}
          >
            <m.icon className="w-3 h-3" /> {m.label}
          </button>
        ))}
      </div>

      {/* Command Input */}
      <div className="relative">
        <Command className="absolute left-3 top-3 w-4 h-4 text-gray-500" />
        <textarea
          value={command}
          onChange={(e) => onCommandChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe what you want to create or edit... (Cmd+Enter to execute)"
          className="w-full bg-gray-800 rounded-lg pl-10 pr-4 py-3 h-20 resize-none border border-gray-700 focus:border-purple-500 focus:outline-none text-sm"
        />
      </div>

      {/* Example Commands + Execute */}
      <div className="flex items-center justify-between mt-3">
        <div className="flex flex-wrap gap-1">
          {EXAMPLE_COMMANDS.slice(0, 4).map(example => (
            <button
              key={example}
              onClick={() => onCommandChange(example)}
              className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded-full text-gray-300"
            >
              {example}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          {isProcessing && (
            <button onClick={onCancel} className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm flex items-center gap-1">
              <XCircle className="w-4 h-4" /> Cancel
            </button>
          )}
          <button
            onClick={onExecute}
            disabled={!command.trim() || isProcessing}
            className="px-6 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-sm font-medium flex items-center gap-2"
          >
            {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {isProcessing ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}
