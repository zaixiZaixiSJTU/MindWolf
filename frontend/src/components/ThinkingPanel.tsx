import { useRef, useEffect, useState } from 'react';
import { Brain, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  chunks: Map<number, string>;
}

export default function ThinkingPanel({ chunks }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [chunks]);

  const entries = Array.from(chunks.entries());

  const toggle = (pid: number) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(pid)) next.delete(pid); else next.add(pid);
      return next;
    });
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 flex flex-col flex-1 min-h-0">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700 shrink-0">
        <Brain size={16} className="text-purple-400" />
        <span className="text-sm font-medium">Thinking Chain</span>
        <span className="text-xs text-slate-500 ml-auto">{entries.length} agents</span>
      </div>
      <div ref={containerRef} className="flex-1 overflow-y-auto p-2 space-y-2">
        {entries.map(([pid, text]) => {
          const open = expanded.has(pid);
          const hasContent = text && text !== 'Waiting...';
          return (
            <div key={pid} className="bg-slate-900 rounded p-2 text-xs">
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => hasContent && toggle(pid)}
              >
                <div className="text-purple-400 font-bold">Player {pid}</div>
                {hasContent && (
                  <span className="text-slate-600">
                    {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  </span>
                )}
              </div>
              <div
                className={`text-slate-400 whitespace-pre-wrap leading-relaxed mt-1 ${open ? '' : 'max-h-32 overflow-y-auto'}`}
              >
                {text || 'Waiting...'}
                {text && !open && <span className="animate-flicker">▌</span>}
              </div>
            </div>
          );
        })}
        {entries.length === 0 && (
          <div className="text-xs text-slate-500 text-center py-4">
            Thinking will appear here when agents are reasoning...
          </div>
        )}
      </div>
    </div>
  );
}
