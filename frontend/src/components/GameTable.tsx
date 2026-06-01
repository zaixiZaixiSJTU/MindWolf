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
const CONTAINER_PAD = 110;
const CONTAINER_SIZE = RADIUS * 2 + CONTAINER_PAD * 2;
const CX = CONTAINER_SIZE / 2; // precise pixel center

/** Angle in radians for seat at `index` (0 = top, clockwise). */
function getAngle(index: number, total: number): number {
  return (index / total) * 2 * Math.PI - Math.PI / 2;
}

/** Center-relative (x, y) for a seat avatar. */
function getPosition(index: number, total: number) {
  const angle = getAngle(index, total);
  return {
    x: Math.cos(angle) * RADIUS,
    y: Math.sin(angle) * RADIUS,
  };
}

/** Center-relative (x, y) where a speech bubble should be anchored. */
function getBubbleOrigin(index: number, total: number) {
  const angle = getAngle(index, total);
  const r = RADIUS + 48;
  return {
    x: Math.cos(angle) * r,
    y: Math.sin(angle) * r,
  };
}

/** Whether the seat is in the top half of the circle → label goes above avatar. */
function isTopHalf(index: number, total: number): boolean {
  return Math.sin(getAngle(index, total)) < -0.01;
}

export default function GameTable({ players, isNight, speeches }: Props) {
  const [expandedPid, setExpandedPid] = useState<number | null>(null);

  const expandedSpeech =
    expandedPid !== null ? speeches.find(s => s.pid === expandedPid) : null;

  return (
    <div
      className="relative"
      style={{ width: CONTAINER_SIZE, height: CONTAINER_SIZE }}
    >
      {/* ── Orbit ring (dashed, reinforces circular symmetry) ── */}
      <div
        className="absolute rounded-full border border-dashed transition-colors duration-1000"
        style={{
          left: CX,
          top: CX,
          width: RADIUS * 2,
          height: RADIUS * 2,
          transform: 'translate(-50%, -50%)',
          borderColor: isNight
            ? 'rgba(99,102,241,0.12)'
            : 'rgba(245,158,11,0.10)',
        }}
      />

      {/* ── Inner accent ring ── */}
      <div
        className="absolute rounded-full border transition-colors duration-1000"
        style={{
          left: CX,
          top: CX,
          width: 50,
          height: 50,
          transform: 'translate(-50%, -50%)',
          borderColor: isNight
            ? 'rgba(99,102,241,0.06)'
            : 'rgba(245,158,11,0.05)',
        }}
      />

      {/* ── Center ornament (sun / moon) ── */}
      <div
        className="absolute z-10"
        style={{ left: CX, top: CX, transform: 'translate(-50%, -50%)' }}
      >
        <motion.div
          className={`w-24 h-24 rounded-full border-4 flex items-center justify-center
                     text-3xl transition-all duration-1000 ${
            isNight
              ? 'bg-indigo-950 border-indigo-500/60 text-indigo-300'
              : 'bg-amber-950 border-amber-500/60 text-amber-300'
          }`}
          animate={{
            boxShadow: isNight
              ? [
                  '0 0 30px rgba(99,102,241,0.35)',
                  '0 0 60px rgba(99,102,241,0.55)',
                  '0 0 30px rgba(99,102,241,0.35)',
                ]
              : [
                  '0 0 30px rgba(245,158,11,0.35)',
                  '0 0 60px rgba(245,158,11,0.55)',
                  '0 0 30px rgba(245,158,11,0.35)',
                ],
          }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        >
          <motion.span
            animate={{ rotate: [0, 360] }}
            transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
          >
            {isNight ? '🌙' : '☀️'}
          </motion.span>
        </motion.div>
      </div>

      {/* ── Player seats ── */}
      {Array.from({ length: TOTAL }, (_, i) => {
        const player = players.find(p => p.id === i + 1);
        const pos = getPosition(i, TOTAL);
        const speaking = speeches.some(s => s.pid === i + 1);
        const topHalf = isTopHalf(i, TOTAL);
        const isDead = player && !player.is_alive;

        return (
          <motion.div
            key={i + 1}
            initial={false}
            animate={{ x: pos.x - 28, y: pos.y - 28, scale: speaking ? 1.15 : 1 }}
            transition={{ type: 'spring', stiffness: 200, damping: 20 }}
            className="absolute z-20"
            style={{ left: CX, top: CX }}
          >
            {/* Labels flow outward: above avatar in top half, below otherwise */}
            <div
              className={`flex items-center gap-1 ${
                topHalf ? 'flex-col-reverse' : 'flex-col'
              }`}
            >
              {/* Avatar circle */}
              <motion.div
                className={`w-14 h-14 rounded-full flex items-center justify-center
                           text-sm font-bold border-2 transition-all duration-700 ${
                  player
                    ? isDead
                      ? 'bg-red-950/60 border-red-700/50 text-red-400 grayscale'
                      : speaking
                        ? 'bg-amber-500 border-amber-300 text-black ring-4 ring-amber-400/50 shadow-lg shadow-amber-500/30'
                        : 'bg-slate-700/80 border-slate-600 text-slate-200'
                    : 'bg-slate-800/50 border-slate-700 text-slate-500'
                }`}
                animate={speaking ? { scale: [1, 1.05, 1] } : {}}
                transition={
                  speaking
                    ? { repeat: Infinity, duration: 1, ease: 'easeInOut' }
                    : {}
                }
              >
                {isDead ? <Skull size={16} /> : i + 1}
              </motion.div>

              {/* Labels group (name + role badges) */}
              <div className="flex flex-col items-center gap-0.5">
                <span
                  className={`text-[10px] w-16 text-center truncate leading-tight ${
                    isDead
                      ? 'text-red-400/80 line-through'
                      : 'text-slate-400'
                  }`}
                >
                  {player?.name || `P${i + 1}`}
                </span>
                {player?.revealed_role && (
                  <span className="text-[9px] text-amber-400/70 leading-none">
                    {player.revealed_role}
                  </span>
                )}
                {isDead && player?.role && (
                  <span className="text-[9px] text-red-400/70 leading-none">
                    {player.role}
                  </span>
                )}
              </div>
            </div>
          </motion.div>
        );
      })}

      {/* ── Speech bubbles (positioned radially outward from speaker) ── */}
      <AnimatePresence>
        {speeches.map(s => {
          const idx = s.pid - 1; // seat index (0‑11)
          if (idx < 0 || idx >= TOTAL) return null;
          const origin = getBubbleOrigin(idx, TOTAL);
          const truncated =
            s.text.length > 50 ? s.text.slice(0, 50) + '...' : s.text;

          return (
            <motion.div
              key={`${s.pid}-${s.text.slice(0, 8)}`}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              onClick={() => setExpandedPid(s.pid)}
              className="absolute z-30 bg-slate-800/95 backdrop-blur-sm
                         border border-slate-600 rounded-lg px-2.5 py-1.5
                         text-xs max-w-[150px] shadow-xl cursor-pointer
                         hover:border-amber-500/50 transition-colors"
              style={{
                top: CX + origin.y,
                left: CX + origin.x,
                transform: 'translate(-50%, -50%)',
              }}
            >
              <span className="text-amber-400 font-bold mr-1">
                #{s.pid}
              </span>
              <span className="text-slate-300">{truncated}</span>
            </motion.div>
          );
        })}
      </AnimatePresence>

      {/* ── Expanded speech overlay ── */}
      <AnimatePresence>
        {expandedSpeech && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-40 flex items-center justify-center"
            style={{
              width: CONTAINER_SIZE,
              height: CONTAINER_SIZE,
            }}
            onClick={() => setExpandedPid(null)}
          >
            <div className="absolute inset-0 bg-black/70 rounded-full" />
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="relative z-10 bg-slate-800 border border-amber-500/50
                         rounded-xl p-5 max-w-[340px] w-full mx-4 shadow-2xl"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <span
                    className="w-9 h-9 rounded-full bg-amber-500/20
                               border border-amber-500/40 flex items-center
                               justify-center text-sm font-bold text-amber-400"
                  >
                    {expandedSpeech.pid}
                  </span>
                  <span className="text-amber-400 font-bold text-sm">
                    Player {expandedSpeech.pid}
                  </span>
                </div>
                <button
                  onClick={() => setExpandedPid(null)}
                  className="text-slate-500 hover:text-slate-300 transition-colors
                             p-1.5 rounded-lg hover:bg-slate-700/50"
                >
                  <X size={16} />
                </button>
              </div>
              <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
                {expandedSpeech.text}
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
