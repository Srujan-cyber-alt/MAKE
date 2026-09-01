import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Wand2, Upload, Image, Film, Loader2, AlertCircle,
  ChevronDown, Settings, Plus, X
} from 'lucide-react'
import api from '../services/api'

type Mode = 'text' | 'image' | 'multi'

interface Provider {
  name: string
  capabilities: string[]
  models: Array<{
    id: string
    name: string
    description: string
    capabilities: string[]
    limits: {
      max_duration_seconds: number
      supported_aspect_ratios: string[]
      max_input_images: number
      max_reference_images: number
      supports_seed: boolean
      supports_negative_prompt: boolean
    }
  }>
}

export default function Generate() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [prompt, setPrompt] = useState('')
  const [negativePrompt, setNegativePrompt] = useState('')
  const [mode, setMode] = useState<Mode>('text')
  const [selectedProvider, setSelectedProvider] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [aspectRatio, setAspectRatio] = useState('16:9')
  const [duration, setDuration] = useState(4)
  const [seed, setSeed] = useState<number | undefined>()
  const [inputFiles, setInputFiles] = useState<File[]>([])
  const [referenceFiles, setReferenceFiles] = useState<{ file: File, role: string }[]>([])

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => {
      const response = await api.get(`/projects/${projectId}`)
      return response.data
    },
  })

  const { data: providers } = useQuery({
    queryKey: ['providers'],
    queryFn: async () => {
      const response = await api.get('/providers')
      return response.data as Provider[]
    },
  })

  const { data: assets } = useQuery({
    queryKey: ['assets', projectId],
    queryFn: async () => {
      const response = await api.get(`/assets/project/${projectId}`)
      return response.data
    },
  })

  useEffect(() => {
    if (providers && providers.length > 0 && !selectedProvider) {
      setSelectedProvider(providers[0].name)
    }
  }, [providers])

  useEffect(() => {
    if (selectedProvider && providers) {
      const provider = providers.find(p => p.name === selectedProvider)
      if (provider && provider.models.length > 0 && !selectedModel) {
        setSelectedModel(provider.models[0].id)
      }
    }
  }, [selectedProvider, providers])

  const selectedProviderData = providers?.find(p => p.name === selectedProvider)
  const selectedModelData = selectedProviderData?.models.find(m => m.id === selectedModel)
  const supportedAspectRatios = selectedModelData?.limits.supported_aspect_ratios || ['16:9']
  const maxDuration = selectedModelData?.limits.max_duration_seconds || 4
  const maxInputImages = selectedModelData?.limits.max_input_images || 1
  const maxReferenceImages = selectedModelData?.limits.max_reference_images || 0
  const supportsSeed = selectedModelData?.limits.supports_seed || false
  const supportsNegativePrompt = selectedModelData?.limits.supports_negative_prompt || false

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData()
      form.append('file', file)
      form.append('project_id', projectId!)
      form.append('asset_type', mode === 'text' ? 'reference' : 'image')
      const response = await api.post('/assets/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
  })

  const generationMutation = useMutation({
    mutationFn: async () => {
      const uploadedInputs = await Promise.all(inputFiles.map(f => uploadMutation.mutateAsync(f)))

      let referenceImages: Array<{ url: string, role: string }> = []
      if (mode === 'multi') {
        const uploadedRefs = await Promise.all(referenceFiles.map(f => uploadMutation.mutateAsync(f.file)))
        referenceImages = uploadedRefs.map((asset, i) => ({
          url: asset.storage_url || `/api/v1/files/${asset.storage_path}`,
          role: referenceFiles[i].role,
        }))
      }

      const payload: any = {
        prompt,
        negative_prompt: supportsNegativePrompt ? negativePrompt : undefined,
        job_type: mode === 'image' ? 'image_to_video' : 'text_to_video',
        provider: selectedProvider,
        model: selectedModel,
        project_id: projectId,
        duration_seconds: Math.min(duration, maxDuration),
        aspect_ratio: aspectRatio,
        input_asset_ids: uploadedInputs.map((a) => a.id),
        reference_images: referenceImages.length > 0 ? referenceImages : undefined,
        parameters: {
          width: aspectRatio === '9:16' ? 720 : aspectRatio === '1:1' ? 1024 : 1280,
          height: aspectRatio === '9:16' ? 1280 : aspectRatio === '1:1' ? 1024 : 720,
          fps: 24,
        },
      }
      if (supportsSeed && seed !== undefined) {
        payload.seed = seed
      }
      const response = await api.post('/generation', payload)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs', projectId] })
      navigate(`/projects/${projectId}`)
    },
  })

  const handleFileDrop = (e: React.DragEvent, type: 'input' | 'reference') => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/') || f.type.startsWith('video/'))
    if (type === 'input') {
      setInputFiles(prev => [...prev, ...files].slice(0, maxInputImages))
    } else {
      const newRefs = files.map(f => ({ file: f, role: 'reference' }))
      setReferenceFiles(prev => [...prev, ...newRefs].slice(0, maxReferenceImages))
    }
  }

  const canSubmit = prompt.trim() && selectedProvider && selectedModel &&
    (mode === 'text' || inputFiles.length > 0 || referenceFiles.length > 0)

  return (
    <div className="max-w-5xl mx-auto">
      <Link to={`/projects/${projectId}`} className="inline-flex items-center gap-2 text-make-muted hover:text-make-text mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to project
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Generate Video</h1>
        <p className="text-make-muted mt-1">Create AI-generated video in {project?.name}</p>
      </div>

      <div className="flex gap-2 mb-6">
        {[
          { key: 'text', label: 'Text to Video', icon: Wand2 },
          { key: 'image', label: 'Image to Video', icon: Image },
          { key: 'multi', label: 'Multi-Reference', icon: Film },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => { setMode(key as Mode); setInputFiles([]); setReferenceFiles([]) }}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              mode === key ? 'bg-make-accent text-white' : 'bg-make-surface text-make-muted hover:text-make-text border border-make-border'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <label className="block text-sm font-medium text-make-text mb-2">Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="input min-h-[120px] resize-y"
              placeholder="Describe your video. Include subject, action, environment, camera movement, lighting, and style."
              required
            />
          </div>

          {mode !== 'text' && (
            <div className="card">
              <label className="block text-sm font-medium text-make-text mb-2">
                {mode === 'image' ? 'Reference Image' : 'Reference Assets'}
              </label>
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => handleFileDrop(e, 'input')}
                className="border-2 border-dashed border-make-border rounded-lg p-6 text-center hover:border-make-accent transition-colors cursor-pointer"
              >
                <Upload className="w-8 h-8 text-make-muted mx-auto mb-2" />
                <p className="text-make-text font-medium">Drop files here or click to upload</p>
                <p className="text-sm text-make-muted mt-1">PNG, JPG, MP4 up to 50MB</p>
              </div>
              {inputFiles.length > 0 && (
                <div className="mt-4 flex gap-2">
                  {inputFiles.map((file, i) => (
                    <div key={i} className="relative">
                      <div className="w-20 h-20 bg-make-border rounded-lg flex items-center justify-center">
                        <Image className="w-8 h-8 text-make-muted" />
                      </div>
                      <button
                        type="button"
                        onClick={() => setInputFiles(prev => prev.filter((_, idx) => idx !== i))}
                        className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center"
                      >
                        <X className="w-3 h-3 text-white" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {mode === 'multi' && maxReferenceImages > 0 && (
            <div className="card">
              <label className="block text-sm font-medium text-make-text mb-2">Multi-Reference Images</label>
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => handleFileDrop(e, 'reference')}
                className="border-2 border-dashed border-make-border rounded-lg p-6 text-center hover:border-make-accent transition-colors cursor-pointer"
              >
                <Upload className="w-8 h-8 text-make-muted mx-auto mb-2" />
                <p className="text-make-text font-medium">Drop reference images</p>
                <p className="text-sm text-make-muted mt-1">Assign roles: character, product, location, style, etc.</p>
              </div>
              {referenceFiles.length > 0 && (
                <div className="mt-4 space-y-2">
                  {referenceFiles.map((ref, i) => (
                    <div key={i} className="flex items-center gap-3 p-2 bg-make-bg rounded-lg">
                      <div className="w-12 h-12 bg-make-border rounded flex items-center justify-center">
                        <Image className="w-6 h-6 text-make-muted" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm text-make-text">{ref.file.name}</p>
                        <select
                          value={ref.role}
                          onChange={(e) => {
                            const newRefs = [...referenceFiles]
                            newRefs[i].role = e.target.value
                            setReferenceFiles(newRefs)
                          }}
                          className="input text-xs py-1 mt-1"
                        >
                          <option value="character">Character</option>
                          <option value="product">Product</option>
                          <option value="location">Location</option>
                          <option value="style">Style</option>
                          <option value="object">Object</option>
                          <option value="environment">Environment</option>
                          <option value="reference">Reference</option>
                        </select>
                      </div>
                      <button
                        type="button"
                        onClick={() => setReferenceFiles(prev => prev.filter((_, idx) => idx !== i))}
                        className="text-make-muted hover:text-red-400"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {supportsNegativePrompt && (
            <div className="card">
              <label className="block text-sm font-medium text-make-text mb-2">Negative Prompt</label>
              <textarea
                value={negativePrompt}
                onChange={(e) => setNegativePrompt(e.target.value)}
                className="input min-h-[80px] resize-y"
                placeholder="Describe what you don't want in the video..."
              />
            </div>
          )}

          {generationMutation.isError && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3 text-red-400">
              <AlertCircle className="w-5 h-5 mt-0.5" />
              <div>
                <p className="font-medium">Generation failed</p>
                <p className="text-sm mt-1">{(generationMutation.error as any)?.response?.data?.detail || 'Unknown error'}</p>
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={() => generationMutation.mutate()}
            disabled={!canSubmit || generationMutation.isPending}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3"
          >
            {generationMutation.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Wand2 className="w-5 h-5" />
                Generate Video
              </>
            )}
          </button>
        </div>

        <div className="space-y-6">
          <div className="card">
            <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
              <Settings className="w-4 h-4" />
              Generation Settings
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-make-text mb-1">Provider</label>
                <select
                  value={selectedProvider}
                  onChange={(e) => { setSelectedProvider(e.target.value); setSelectedModel('') }}
                  className="input"
                >
                  {providers?.map(p => (
                    <option key={p.name} value={p.name}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-make-text mb-1">Model</label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="input"
                >
                  {selectedProviderData?.models.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
                {selectedModelData && (
                  <p className="text-xs text-make-muted mt-1">{selectedModelData.description}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-make-text mb-1">Aspect Ratio</label>
                <select
                  value={aspectRatio}
                  onChange={(e) => setAspectRatio(e.target.value)}
                  className="input"
                >
                  {supportedAspectRatios.map(ar => (
                    <option key={ar} value={ar}>{ar}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-make-text mb-1">
                  Duration: {duration}s (max {maxDuration}s)
                </label>
                <input
                  type="range"
                  min="1"
                  max={maxDuration}
                  step="0.5"
                  value={duration}
                  onChange={(e) => setDuration(parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>

              {supportsSeed && (
                <div>
                  <label className="block text-sm font-medium text-make-text mb-1">Seed (optional)</label>
                  <input
                    type="number"
                    value={seed ?? ''}
                    onChange={(e) => setSeed(e.target.value ? parseInt(e.target.value) : undefined)}
                    className="input"
                    placeholder="Random"
                  />
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold text-white mb-3">Recent Generations</h3>
            <div className="space-y-2">
              {assets?.filter((a: any) => a.asset_type === 'generated').slice(0, 3).map((asset: any) => (
                <div key={asset.id} className="flex items-center gap-3 p-2 bg-make-bg rounded">
                  <div className="w-10 h-10 bg-make-border rounded flex items-center justify-center">
                    <Film className="w-5 h-5 text-make-muted" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-make-text truncate">{asset.filename}</p>
                    <p className="text-xs text-make-muted">{new Date(asset.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
              {!assets?.some((a: any) => a.asset_type === 'generated') && (
                <p className="text-sm text-make-muted">No generations yet</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
