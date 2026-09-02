/**
 * Model Explorer for MAKE AI Video Phase 16.
 * Advanced view of all models, providers, capabilities, health, and cost.
 */

import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../services/api';

interface Model {
  id: string;
  provider: string;
  display_name: string;
  family: string;
  version: string;
  modality: string;
  capabilities: string[];
  status: string;
  availability: string;
  supported_formats: string[];
  supported_resolutions: string[];
  supported_aspect_ratios: string[];
  supported_durations: number[];
  seed: boolean;
  negative_prompt: boolean;
  i2v: boolean;
  t2v: boolean;
  v2v: boolean;
  extension: boolean;
  motion_control: boolean;
  camera_control: boolean;
  audio_support: boolean;
  image_support: boolean;
  video_support: boolean;
  reference_limits: Record<string, any>;
  quality_profile: Record<string, any> | null;
  cost_profile: Record<string, any>;
  speed_profile: Record<string, any>;
}

interface Provider {
  id: string;
  name: string;
  provider_type: string;
  authentication_status: string;
  api_status: string;
  supported_models: string[];
  rate_limits: Record<string, any>;
  concurrency_limits: Record<string, any>;
  region: string | null;
  health: Record<string, any>;
  latency: number | null;
  error_rate: number;
  cost_information: Record<string, any>;
}

export const ModelExplorer: React.FC = () => {
  const [search, setSearch] = useState('');
  const [modalityFilter, setModalityFilter] = useState<string>('all');
  const [capabilityFilter, setCapabilityFilter] = useState<string>('all');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ['universal-models'],
    queryFn: async () => {
      const response = await api.get('/universal-models/models');
      return response.data as { models: Model[]; total: number };
    },
  });

  const { data: providersData, isLoading: providersLoading } = useQuery({
    queryKey: ['universal-providers'],
    queryFn: async () => {
      const response = await api.get('/universal-models/providers');
      return response.data as Record<string, Provider>;
    },
  });

  const { data: auditData } = useQuery({
    queryKey: ['routing-audit'],
    queryFn: async () => {
      const response = await api.get('/universal-models/routing/audit');
      return response.data as { audit_log: any[] };
    },
  });

  const models = modelsData?.models || [];
  const providers = providersData || {};

  const filteredModels = useMemo(() => {
    let result = models;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(m =>
        m.display_name.toLowerCase().includes(q) ||
        m.provider.toLowerCase().includes(q) ||
        m.family.toLowerCase().includes(q)
      );
    }
    if (modalityFilter !== 'all') {
      result = result.filter(m => m.modality === modalityFilter);
    }
    if (capabilityFilter !== 'all') {
      result = result.filter(m => m.capabilities.includes(capabilityFilter));
    }
    return result;
  }, [models, search, modalityFilter, capabilityFilter]);

  const modalities = useMemo(() => Array.from(new Set(models.map(m => m.modality))).filter(Boolean), [models]);
  const capabilities = useMemo(() => Array.from(new Set(models.flatMap(m => m.capabilities))).filter(Boolean), [models]);

  if (modelsLoading || providersLoading) {
    return <div className="p-4 text-sm text-gray-400">Loading model explorer...</div>;
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-200">Model Explorer</h3>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-xs text-gray-400 hover:text-white"
        >
          {showAdvanced ? 'Simple' : 'Advanced'}
        </button>
      </div>

      <div className="flex gap-2 flex-wrap">
        <input
          type="text"
          placeholder="Search models..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded text-white"
        />
        <select
          value={modalityFilter}
          onChange={(e) => setModalityFilter(e.target.value)}
          className="px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded text-white"
        >
          <option value="all">All Modalities</option>
          {modalities.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <select
          value={capabilityFilter}
          onChange={(e) => setCapabilityFilter(e.target.value)}
          className="px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded text-white"
        >
          <option value="all">All Capabilities</option>
          {capabilities.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredModels.length === 0 && (
          <div className="text-xs text-gray-500">No models match filters.</div>
        )}
        {filteredModels.map(model => {
          const provider = providers[model.provider];
          return (
            <div key={model.id} className="p-3 bg-gray-800 rounded border border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-white font-medium">{model.display_name}</div>
                  <div className="text-xs text-gray-400">{model.provider} · {model.family} · {model.version}</div>
                </div>
                <span className={`px-2 py-0.5 text-xs rounded ${
                  model.status === 'available' ? 'bg-green-900 text-green-300' :
                  model.status === 'optional' ? 'bg-yellow-900 text-yellow-300' :
                  'bg-gray-700 text-gray-300'
                }`}>
                  {model.status}
                </span>
              </div>
              <div className="mt-2 flex gap-2 flex-wrap">
                {model.capabilities.slice(0, 6).map(c => (
                  <span key={c} className="px-1.5 py-0.5 text-xs bg-gray-700 text-gray-300 rounded">{c}</span>
                ))}
                {model.capabilities.length > 6 && (
                  <span className="text-xs text-gray-500">+{model.capabilities.length - 6} more</span>
                )}
              </div>
              {showAdvanced && (
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-400">
                  <div>Resolutions: {model.supported_resolutions.join(', ')}</div>
                  <div>Aspect Ratios: {model.supported_aspect_ratios.join(', ')}</div>
                  <div>Durations: {model.supported_durations.join(', ')}s</div>
                  <div>Formats: {model.supported_formats.join(', ')}</div>
                  <div>Seed: {model.seed ? 'Yes' : 'No'}</div>
                  <div>Negative Prompt: {model.negative_prompt ? 'Yes' : 'No'}</div>
                  <div>I2V: {model.i2v ? 'Yes' : 'No'}</div>
                  <div>V2V: {model.v2v ? 'Yes' : 'No'}</div>
                  <div>Camera: {model.camera_control ? 'Yes' : 'No'}</div>
                  <div>Motion: {model.motion_control ? 'Yes' : 'No'}</div>
                  {model.quality_profile && (
                    <>
                      <div>Quality: {model.quality_profile.quality_score?.toFixed(2)}</div>
                      <div>Speed: {model.quality_profile.speed_score?.toFixed(2)}</div>
                      <div>Cost: {model.quality_profile.cost_score?.toFixed(2)}</div>
                      <div>Cinematic: {model.quality_profile.cinematic_score?.toFixed(2)}</div>
                    </>
                  )}
                </div>
              )}
              {provider && showAdvanced && (
                <div className="mt-2 text-xs text-gray-500">
                  Provider health: {provider.health?.status || 'unknown'} · Latency: {provider.latency ?? 'N/A'}ms · Error rate: {(provider.error_rate * 100).toFixed(1)}%
                </div>
              )}
            </div>
          );
        })}
      </div>

      {showAdvanced && auditData && (
        <div className="mt-4">
          <h4 className="text-xs font-medium text-gray-400 mb-2">Recent Routing Decisions</h4>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {auditData.audit_log?.slice(0, 10).map((audit: any, i: number) => (
              <div key={i} className="text-xs text-gray-500 p-2 bg-gray-800 rounded">
                <div className="text-gray-400">{audit.timestamp}</div>
                <div>Selected: {audit.selected_model?.model_id || 'none'}</div>
                <div>Mode: {audit.routing_mode}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
