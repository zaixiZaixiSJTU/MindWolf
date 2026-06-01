import { useRef, useEffect, useState } from 'react';
import { Brain, ChevronDown, ChevronUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

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
      if (next.has(pid)) next.delete(pid);
      else next.add(pid);
      return next;
    });
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 flex flex-col flex-1 min-h-0">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700 shrink-0">
        <div className="w-6 h-6 rounded-md bg-purple-500/15 flex items-center justify-center">
          <Brain size={14} className="text-purple-400" />
        </div>
        <span className="text-sm font-medium">Thinking Chain</span>
        <span className="text-[10px] text-slate-500 ml-auto bg-slate-900/50 px-1.5 py-0.5 rounded-full">
          {entries.length}
        </span>
      </div>

      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-2 space-y-2"
      >
        <AnimatePresence>
          {entries.map(([pid, text]) => {
            const open = expanded.has(pid);
            const hasContent = text && text !== 'Waiting...';
            return (
              <motion.div
                key={pid}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-slate-900/80 rounded-lg p-2.5 text-xs border border-slate-700/50"
              >
                <div
                  className="flex items-center justify-between cursor-pointer select-none"
                  onClick={() => hasContent && toggle(pid)}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-[10px] font-bold text-purple-400">
                      {pid}
                    </span>
                    <span className="text-purple-400 font-semibold text-xs">
                      Player {pid}
                    </span>
                    {text && text !== 'Waiting...' && !open && (
                      <span className="text-[10px] text-slate-500">
                        {text.length} chars
                      </span>
                    )}
                  </div>
                  {hasContent && (
                    <span className="text-slate-600">
                      {open ? (
                        <ChevronUp size={12} />
                      ) : (
                        <ChevronDown size={12} />
                      )}
                    </span>
                  )}
                </div>
                <div
                  className={`text-slate-400 whitespace-pre-wrap leading-relaxed mt-1.5 font-mono ${
                    open ? '' : 'max-h-28 overflow-y-auto'
                  }`}
                >
                  {text || (
                    <span className="text-slate-600 italic">
                      Waiting...
                    </span>
                  )}
                  {text && !open && (
                    <span className="animate-flicker text-purple-400">
                      ▌
                    </span>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {entries.length === 0 && (
          <div className="text-xs text-slate-500 text-center py-6 italic">
            Thinking chains will appear here…
          </div>
        )}
      </div>
    </div>
  );
}
