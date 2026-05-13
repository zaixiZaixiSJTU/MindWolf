import { Clock } from 'lucide-react';
import type { MemoryEvent } from '../types';

interface Props {
  memories: MemoryEvent[];
}

const TYPE_LABELS: Record<string, string> = {
  claim_role: 'Claim',
  check_result: 'Check',
  accuse: 'Accuse',
  defend: 'Defend',
  retract: 'Retract',
};

const TYPE_COLORS: Record<string, string> = {
  claim_role: 'text-cyan-400',
  check_result: 'text-amber-400',
  accuse: 'text-red-400',
  defend: 'text-green-400',
  retract: 'text-slate-400',
};

export default function MemoryPanel({ memories }: Props) {
  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 flex flex-col h-1/2">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700">
        <Clock size={16} className="text-cyan-400" />
        <span className="text-sm font-medium">Memory Events</span>
        <span className="text-xs text-slate-500 ml-auto">{memories.length} events</span>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {memories.map(m => (
          <div
            key={m.id}
            className={`bg-slate-900 rounded p-1.5 text-xs ${m.is_contradicted ? 'opacity-30 line-through' : ''}`}
          >
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500">R{m.round}</span>
              <span className={TYPE_COLORS[m.event_type] || 'text-slate-400'}>
                {TYPE_LABELS[m.event_type] || m.event_type}
              </span>
              <span className="text-slate-600">#{m.speaker_id}</span>
              {m.target_id && <span className="text-slate-600">→ #{m.target_id}</span>}
              <span className="ml-auto text-[10px] text-slate-600">
                w: {m.current_weight.toFixed(2)}
              </span>
            </div>
            <div className="text-slate-500 mt-0.5 truncate">{m.content}</div>
          </div>
        ))}
        {memories.length === 0 && (
          <div className="text-xs text-slate-500 text-center py-4">
            No memory events yet...
          </div>
        )}
      </div>
    </div>
  );
}
