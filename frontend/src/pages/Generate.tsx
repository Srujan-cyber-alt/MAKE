import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, Wand2, Upload, Image, Film, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import api from '../services/api'

type Mode = 'text' | 'image' | 'multi'

export default function Generate() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [prompt, setPrompt] = useState('')
  const [negativePrompt, setNegativePrompt] = useState('')
  const [mode, setMode] = useState<Mode>('text')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => {
      const response = await api.get(`/projects/${projectId}`)
      return response.data
    },
  })

  const generationMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.post('/generation', data)
      return response.data
    },
    onSuccess: (data) => {
      navigate(`/projects/${projectId}`)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    generationMutation.mutate({
      prompt,
      negative_prompt: negativePrompt,
      job_type: mode === 'image' ? 'image_to_video' : 'text_to_video',
      project_id: projectId,
      parameters: {
        duration_seconds: 4,
        width: 1280,
        height: 720,
      },
    })
  }

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files).filter((f) =>
      f.type.startsWith('image/') || f.type.startsWith('video/')
    )
    setSelectedFiles((prev) => [...prev, ...files])
  }

  return (
    <div className="max-w-4xl mx-auto">
      <Link to={`/projects/${projectId}`} className="inline-flex items-center gap-2 text-make-muted hover:text-make-text mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to project
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Generate Video</h1>
        <p className="text-make-muted mt-1">
          Create AI-generated video from text or images in project: {project?.name}
        </p>
      </div>

      <div className="flex gap-2 mb-6">
        {[
          { key: 'text', label: 'Text to Video', icon: Wand2 },
          { key: 'image', label: 'Image to Video', icon: Image },
          { key: 'multi', label: 'Multi-Reference', icon: Film },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setMode(key as Mode)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              mode === key
                ? 'bg-make-accent text-white'
                : 'bg-make-surface text-make-muted hover:text-make-text border border-make-border'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {mode === 'text' && (
          <div className="card">
            <label className="block text-sm font-medium text-make-text mb-2">Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="input min-h-[120px] resize-y"
              placeholder="Describe your video scene. Be specific about subject, environment, action, camera movement, lighting, and style."
              required
            />
          </div>
        )}

        {mode === 'image' && (
          <div className="card">
            <label className="block text-sm font-medium text-make-text mb-2">Reference Image</label>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              className="border-2 border-dashed border-make-border rounded-lg p-8 text-center hover:border-make-accent transition-colors cursor-pointer"
            >
              <Upload className="w-8 h-8 text-make-muted mx-auto mb-2" />
              <p className="text-make-text font-medium">Drop an image here or click to upload</p>
              <p className="text-sm text-make-muted mt-1">PNG, JPG up to 10MB</p>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => e.target.files && setSelectedFiles(Array.from(e.target.files))}
                className="hidden"
              />
            </div>
            {selectedFiles.length > 0 && (
              <div className="mt-4 flex gap-2">
                {selectedFiles.map((file, i) => (
                  <div key={i} className="w-20 h-20 bg-make-border rounded-lg flex items-center justify-center">
                    <Image className="w-8 h-8 text-make-muted" />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="card">
          <label className="block text-sm font-medium text-make-text mb-2">Negative Prompt</label>
          <textarea
            value={negativePrompt}
            onChange={(e) => setNegativePrompt(e.target.value)}
            className="input min-h-[80px] resize-y"
            placeholder="Describe what you don't want in the video..."
          />
        </div>

        {generationMutation.isError && (
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3 text-red-400">
            <AlertCircle className="w-5 h-5" />
            <div>
              <p className="font-medium">Generation failed</p>
              <p className="text-sm">{(generationMutation.error as any)?.response?.data?.detail || 'Unknown error'}</p>
            </div>
          </div>
        )}

        <div className="flex gap-3">
          <button type="submit" disabled={generationMutation.isPending} className="btn-primary flex items-center gap-2">
            {generationMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Wand2 className="w-4 h-4" />
                Generate Video
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
