import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Skull, X } from 'lucide-react';
import type { PlayerInfo } from '../types';

interface Props {
  players: PlayerInfo[];
  isNight: boolean;
  speeches: { pid: number; text: string }[];
}

const TOTAL = 12;
const RADIUS = 160;

function getPosition(index: number, total: number) {
  const angle = (index / total) * 2 * Math.PI - Math.PI / 2;
  return {
    x: Math.cos(angle) * RADIUS,
    y: Math.sin(angle) * RADIUS,
  };
}

export default function GameTable({ players, isNight, speeches }: Props) {
  const [expandedPid, setExpandedPid] = useState<number | null>(null);

  const expandedSpeech = expandedPid !== null
    ? speeches.find(s => s.pid === expandedPid)
    : null;

  return (
    <div className="relative" style={{ width: RADIUS * 2 + 120, height: RADIUS * 2 + 120 }}>
      {/* Center */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
        <div className={`w-20 h-20 rounded-full border-4 flex items-center justify-center text-2xl font-bold transition-all duration-1000 ${
          isNight
            ? 'bg-indigo-900 border-indigo-500 text-indigo-300 shadow-[0_0_30px_rgba(99,102,241,0.5)]'
            : 'bg-amber-900 border-amber-500 text-amber-300 shadow-[0_0_30px_rgba(245,158,11,0.5)]'
        }`}>
          {isNight ? '🌙' : '☀️'}
        </div>
      </div>

      {/* Players */}
      {Array.from({ length: TOTAL }, (_, i) => {
        const player = players.find(p => p.id === i + 1);
        const pos = getPosition(i, TOTAL);
        const speaking = speeches.some(s => s.pid === i + 1);

        return (
          <motion.div
            key={i + 1}
            initial={false}
            animate={{
              x: pos.x,
              y: pos.y,
              scale: speaking ? 1.15 : 1,
            }}
            transition={{ type: 'spring', stiffness: 200, damping: 20 }}
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20"
          >
            <div className="flex flex-col items-center gap-1">
              <motion.div
                className={`w-14 h-14 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors duration-1000 ${
                  player
                    ? player.is_alive
                      ? speaking
                        ? 'bg-amber-500 border-amber-300 text-black ring-4 ring-amber-400/50'
                        : 'bg-slate-700 border-slate-500 text-slate-200'
                      : 'bg-red-900/50 border-red-700 text-red-400 line-through'
                    : 'bg-slate-800 border-slate-600 text-slate-500'
                }`}
                animate={speaking ? { scale: [1, 1.05, 1] } : {}}
                transition={{ repeat: Infinity, duration: 1 }}
              >
                {player && !player.is_alive ? <Skull size={16} /> : (i + 1)}
              </motion.div>
              <span className="text-[10px] text-slate-400 w-16 text-center truncate">
                {player?.name || `P${i + 1}`}
              </span>
              {player?.revealed_role && (
                <span className="text-[9px] text-amber-400/70">{player.revealed_role}</span>
              )}
              {player && !player.is_alive && player.role && (
                <span className="text-[9px] text-red-400/70">{player.role}</span>
              )}
            </div>
          </motion.div>
        );
      })}

      {/* Speech bubbles */}
      {speeches.map(s => {
        const idx = players.findIndex(p => p.id === s.pid);
        if (idx < 0) return null;
        const pos = getPosition(idx, TOTAL);
        const truncated = s.text.length > 50 ? s.text.slice(0, 50) + '...' : s.text;

        return (
          <motion.div
            key={`${s.pid}-${s.text.slice(0, 8)}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            onClick={() => setExpandedPid(s.pid)}
            className="absolute z-30 bg-slate-800 border border-slate-600 rounded-lg px-2 py-1 text-xs max-w-[140px] shadow-lg cursor-pointer hover:border-amber-500/50 transition-colors"
            style={{
              top: `calc(50% + ${pos.y + 35}px)`,
              left: `calc(50% + ${pos.x - 70}px)`,
            }}
          >
            <span className="text-amber-400 font-bold mr-1">#{s.pid}</span>
            <span className="text-slate-300">{truncated}</span>
          </motion.div>
        );
      })}

      {/* Expanded speech overlay */}
      <AnimatePresence>
        {expandedSpeech && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-40 flex items-center justify-center"
            style={{ width: RADIUS * 2 + 120, height: RADIUS * 2 + 120 }}
            onClick={() => setExpandedPid(null)}
          >
            <div className="absolute inset-0 bg-black/60 rounded-full" />
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="relative z-10 bg-slate-800 border border-amber-500/50 rounded-xl p-4 max-w-[320px] w-full mx-4 shadow-2xl"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-amber-400 font-bold text-sm">Player {expandedSpeech.pid}</span>
                <button
                  onClick={() => setExpandedPid(null)}
                  className="text-slate-500 hover:text-slate-300 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>
              <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">{expandedSpeech.text}</p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
