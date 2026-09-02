/**
 * Routing Inspector for MAKE AI Video Phase 16.
 * Shows request requirements, candidates, eliminated models, and selected model.
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../services/api';

interface Candidate {
  model_id: string;
  provider_id: string;
  score: number;
  reasons: string[];
}

interface AuditEntry {
  timestamp: string;
  request_requirements: Record<string, any>;
  candidate_models: Candidate[];
  eliminated_candidates: any[];
  selected_model: any;
  fallback_chain: any[];
  routing_mode: string;
}

export const RoutingInspector: React.FC = () => {
  const [limit] = useState(20);

  const { data, isLoading } = useQuery({
    queryKey: ['routing-inspector', limit],
    queryFn: async () => {
      const response = await api.get('/universal-models/routing/audit', { params: { limit } });
      return response.data as { audit_log: AuditEntry[] };
    },
    refetchInterval: 30000,
  });

  const audits = data?.audit_log || [];

  if (isLoading) {
    return <div className="p-4 text-sm text-gray-400">Loading routing inspector...</div>;
  }

  return (
    <div className="p-4 space-y-4">
      <h3 className="text-sm font-medium text-gray-200">Routing Inspector</h3>
      <p className="text-xs text-gray-500">
        Every routing decision is logged below. Advanced users can inspect model selection logic.
      </p>

      <div className="space-y-3 max-h-[600px] overflow-y-auto">
        {audits.length === 0 && (
          <div className="text-xs text-gray-500">No routing decisions recorded yet.</div>
        )}
        {audits.map((audit, i) => (
          <div key={i} className="p-3 bg-gray-800 rounded border border-gray-700 space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs text-gray-400">{audit.timestamp}</div>
              <span className="px-2 py-0.5 text-xs bg-blue-900 text-blue-300 rounded">{audit.routing_mode}</span>
            </div>

            <div>
              <div className="text-xs font-medium text-gray-300 mb-1">Request Requirements</div>
              <div className="text-xs text-gray-500">
                {JSON.stringify(audit.request_requirements, null, 2)}
              </div>
            </div>

            <div>
              <div className="text-xs font-medium text-gray-300 mb-1">Candidates</div>
              <div className="space-y-1">
                {audit.candidate_models?.map((c, ci) => (
                  <div key={ci} className={`p-2 rounded text-xs ${ci === 0 ? 'bg-green-900 border border-green-700' : 'bg-gray-700'}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-white">{c.model_id}</span>
                      <span className="text-gray-400">score: {c.score.toFixed(1)}</span>
                    </div>
                    <div className="text-gray-400">{c.provider_id}</div>
                    {c.reasons && c.reasons.length > 0 && (
                      <div className="text-gray-500 mt-1">{c.reasons.slice(0, 3).join('; ')}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {audit.eliminated_candidates?.length > 0 && (
              <div>
                <div className="text-xs font-medium text-gray-300 mb-1">Eliminated</div>
                <div className="space-y-1">
                  {audit.eliminated_candidates.slice(0, 5).map((ec, ei) => (
                    <div key={ei} className="p-2 bg-red-900/30 rounded text-xs text-red-300">
                      <div>{ec.model_id || ec}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div>
              <div className="text-xs font-medium text-gray-300 mb-1">Selected</div>
              <div className="p-2 bg-green-900/30 rounded text-xs text-green-300">
                <div className="font-medium">{audit.selected_model?.model_id || 'none'}</div>
                <div className="text-gray-400">{audit.selected_model?.reasons?.join('; ') || ''}</div>
              </div>
            </div>

            {audit.fallback_chain?.length > 0 && (
              <div>
                <div className="text-xs font-medium text-gray-300 mb-1">Fallback Chain</div>
                <div className="space-y-1">
                  {audit.fallback_chain.map((fb, fi) => (
                    <div key={fi} className="p-2 bg-gray-700 rounded text-xs text-gray-300">
                      <div className="flex items-center justify-between">
                        <span>{fb.model_id}</span>
                        <span className="text-gray-400">score: {fb.score?.toFixed(1)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
