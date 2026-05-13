import { useRef, useEffect, useState } from 'react';
import { Terminal, Moon, Zap, MessageSquare, Trophy, ChevronDown, ChevronUp } from 'lucide-react';
import type { LogEntry } from '../types';

interface Props {
  logs: LogEntry[];
}

const TYPE_CONFIG: Record<string, { icon: typeof Terminal; color: string; label: string }> = {
  PHASE_CHANGE: { icon: Moon, color: 'text-amber-400', label: 'Phase' },
  NIGHT_RESULT: { icon: Moon, color: 'text-blue-400', label: 'Night' },
  PLAYER_SPEECH: { icon: MessageSquare, color: 'text-green-400', label: 'Speech' },
  LLM_CALL: { icon: Zap, color: 'text-purple-400', label: 'LLM' },
  GAME_OVER: { icon: Trophy, color: 'text-yellow-400', label: 'End' },
};

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString('en-US', { hour12: false });
}

function getBody(entry: LogEntry): string | null {
  if (entry.type === 'LLM_CALL' && entry.response) return entry.response;
  if (entry.type === 'PLAYER_SPEECH' && entry.speech) return entry.speech;
  return null;
}

const PREVIEW_LEN = 60;

export default function LogPanel({ logs }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const toggle = (i: number) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i); else next.add(i);
      return next;
    });
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 flex flex-col flex-1 min-h-0">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700 shrink-0">
        <Terminal size={16} className="text-emerald-400" />
        <span className="text-sm font-medium">Live Logs</span>
        <span className="text-xs text-slate-500 ml-auto">{logs.length} entries</span>
      </div>
      <div ref={containerRef} className="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-[11px] leading-relaxed">
        {logs.map((entry, i) => {
          const cfg = TYPE_CONFIG[entry.type] || { icon: Terminal, color: 'text-slate-400', label: entry.type };
          const Icon = cfg.icon;
          const body = getBody(entry);
          const isLong = body && body.length > PREVIEW_LEN;
          const open = expanded.has(i);

          return (
            <div
              key={i}
              onClick={() => isLong && toggle(i)}
              className={`bg-slate-900/80 rounded px-2 py-1 transition-colors ${isLong ? 'cursor-pointer hover:bg-slate-900' : ''}`}
            >
              <div className="flex items-center gap-1.5">
                <span className="text-slate-600 shrink-0">{formatTime(entry.ts)}</span>
                <Icon size={12} className={cfg.color + ' shrink-0'} />
                <span className={cfg.color + ' font-semibold shrink-0'}>{cfg.label}</span>
                {entry.round != null && <span className="text-slate-600 shrink-0">R{entry.round}</span>}
                {entry.player_id != null && <span className="text-slate-500 shrink-0">P{entry.player_id}</span>}
                {entry.model && <span className="text-slate-600 text-[10px] shrink-0 hidden sm:inline">{entry.model}</span>}
                {entry.elapsed_sec != null && <span className="text-slate-600 text-[10px] ml-auto shrink-0">{entry.elapsed_sec.toFixed(1)}s</span>}
                {isLong && (
                  <span className="text-slate-600 shrink-0">
                    {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                  </span>
                )}
              </div>
              <div className={`text-slate-400 mt-0.5 ${open ? '' : 'truncate'}`}>
                {body ? (
                  <span>{open ? body : body.slice(0, PREVIEW_LEN)}</span>
                ) : entry.type === 'PHASE_CHANGE' && entry.phase ? (
                  <span className="text-amber-400/80">→ {entry.phase}</span>
                ) : entry.type === 'NIGHT_RESULT' && entry.deaths ? (
                  <span className="text-blue-400/80">{entry.deaths}</span>
                ) : entry.type === 'GAME_OVER' && entry.winner ? (
                  <span className="text-yellow-400/80">Winner: {entry.winner}</span>
                ) : null}
              </div>
            </div>
          );
        })}
        {logs.length === 0 && (
          <div className="text-xs text-slate-500 text-center py-4">Waiting for game events...</div>
        )}
      </div>
    </div>
  );
}
