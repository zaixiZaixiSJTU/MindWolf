import { useState, useEffect, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Moon, Sun, Play, Skull } from 'lucide-react';
import GameTable from './components/GameTable';
import ThinkingPanel from './components/ThinkingPanel';
import LogPanel from './components/LogPanel';
import ModelConfigPanel from './components/ModelConfigPanel';
import { useWebSocket } from './useWebSocket';
import type { PlayerInfo, WSMessage, GameState, LogEntry } from './types';

const WS_URL = 'ws://localhost:8765/ws/spectator';

export default function App() {
  const { connected, on } = useWebSocket(WS_URL);
  const [gameState, setGameState] = useState<GameState>({
    phase: 'PRE_GAME', round: 0, players: [], winner: null,
  });
  const [speeches, setSpeeches] = useState<{pid: number; text: string; ts: number}[]>([]);
  const [thinkingChunks, setThinkingChunks] = useState<Map<number, string>>(new Map());
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    const unsubs: (() => void)[] = [];

    unsubs.push(on('PHASE_CHANGE', (msg: WSMessage) => {
      const p = msg.payload as Record<string, unknown>;
      setGameState(prev => ({
        ...prev,
        phase: p.phase as string,
        round: p.round as number,
      }));
      setLogs(prev => [...prev.slice(-199), {
        ts: Date.now(), type: 'PHASE_CHANGE',
        phase: p.phase as string,
        round: p.round as number,
      }]);
    }));

    unsubs.push(on('NIGHT_RESULT', (msg: WSMessage) => {
      const p = msg.payload as Record<string, unknown>;
      const deaths = p.deaths as [number, string][] | undefined;
      const deathInfo = p.death_info as string | undefined;
      if (deaths) {
        setGameState(prev => ({
          ...prev,
          players: prev.players.map(pl => {
            const dead = deaths.find(d => d[0] === pl.id);
            return dead ? { ...pl, is_alive: false } : pl;
          }),
        }));
      }
      setLogs(prev => [...prev.slice(-199), {
        ts: Date.now(), type: 'NIGHT_RESULT',
        deaths: deathInfo || (deaths?.length ? `${deaths.length} dead` : 'Peaceful night'),
      }]);
    }));

    unsubs.push(on('PLAYER_SPEECH', (msg: WSMessage) => {
      const p = msg.payload as Record<string, unknown>;
      setSpeeches(prev => [...prev.slice(-5), {
        pid: p.player_id as number,
        text: p.speech as string,
        ts: Date.now(),
      }]);
      setLogs(prev => [...prev.slice(-199), {
        ts: Date.now(), type: 'PLAYER_SPEECH',
        player_id: p.player_id as number,
        speech: p.speech as string,
      }]);
    }));

    unsubs.push(on('THINKING_CHUNK', (msg: WSMessage) => {
      const p = msg.payload as Record<string, unknown>;
      setThinkingChunks(prev => {
        const next = new Map(prev);
        const pid = p.player_id as number;
        const chunk = p.chunk as string;
        next.set(pid, chunk);
        return next;
      });
      setLogs(prev => [...prev.slice(-199), {
        ts: Date.now(), type: 'LLM_CALL',
        player_id: p.player_id as number,
        response: (p.chunk as string) || '',
      }]);
    }));

    unsubs.push(on('LLM_CALL', (msg: WSMessage) => {
      const p = msg.payload as Record<string, unknown>;
      setLogs(prev => [...prev.slice(-199), {
        ts: Date.now(), type: 'LLM_CALL',
        player_id: p.player_id as number,
        round: p.round as number,
        phase: p.phase as string,
        model: p.model as string,
        response: (p.response as string) || '',
        elapsed_sec: p.elapsed_sec as number,
      }]);
    }));

    unsubs.push(on('GAME_OVER', (msg: WSMessage) => {
      const p = msg.payload as Record<string, unknown>;
      const players = p.players as PlayerInfo[] | undefined;
      setGameState(prev => ({
        ...prev,
        phase: 'GAME_OVER',
        winner: p.winner as string,
        players: players || prev.players,
      }));
      setLogs(prev => [...prev.slice(-199), {
        ts: Date.now(), type: 'GAME_OVER',
        winner: p.winner as string,
      }]);
    }));

    return () => { unsubs.forEach(fn => fn()); };
  }, [on]);

  const startGame = useCallback(async (playerConfigs?: any[], providerKeys?: Record<string, string>) => {
    try {
      if (playerConfigs && playerConfigs.length > 0) {
        const providers: Record<string, { api_key: string }> = {};
        if (providerKeys) {
          for (const [k, v] of Object.entries(providerKeys)) {
            if (v) providers[k] = { api_key: v };
          }
        }
        await fetch('http://localhost:8765/game/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            default_provider: playerConfigs[0]?.provider || 'deepseek',
            default_model: playerConfigs[0]?.model || 'deepseek-chat',
            default_temperature: playerConfigs[0]?.temperature || 0.8,
            providers,
            players: playerConfigs,
          }),
        });
      }
      const startResp = await fetch('http://localhost:8765/game/start', { method: 'POST' });
      const startData = await startResp.json();
      if (startData.error) {
        console.warn('Game start failed:', startData.error);
        const resp = await fetch('http://localhost:8765/game/state');
        const state: GameState = await resp.json();
        if (state.players && state.players.length > 0) setGameState(state);
        return;
      }
      const resp = await fetch('http://localhost:8765/game/state');
      const state: GameState = await resp.json();
      setGameState(state);
    } catch {
      const mockPlayers: PlayerInfo[] = Array.from({ length: 12 }, (_, i) => ({
        id: i + 1,
        name: `Player ${i + 1}`,
        is_alive: true,
        revealed_role: null,
        role: ['WEREWOLF', 'VILLAGER', 'SEER', 'WITCH', 'HUNTER', 'IDIOT',
               'WEREWOLF', 'VILLAGER', 'WEREWOLF', 'VILLAGER', 'WEREWOLF', 'VILLAGER'][i],
      }));
      setGameState({
        phase: 'DAY_DISCUSS', round: 1, players: mockPlayers, winner: null,
      });
    }
  }, []);

  const isNightPhase = gameState.phase.startsWith('NIGHT');

  return (
    <div className={`min-h-screen transition-colors duration-1000 ${
      isNightPhase ? 'bg-slate-950' : 'bg-slate-900'
    }`}>
      <header className="flex items-center justify-between px-6 py-3 border-b border-slate-700">
        <h1 className="text-xl font-bold tracking-tight">
          <span className="text-amber-400">🐺 SJM-Werewolf</span>
        </h1>
        <div className="flex items-center gap-4 text-sm text-slate-400">
          <span>Round {gameState.round}</span>
          <span className="px-2 py-0.5 rounded bg-slate-800">{gameState.phase}</span>
          <AnimatePresence mode="wait">
            {isNightPhase ? (
              <motion.span key="night" initial={{ rotate: -90 }} animate={{ rotate: 0 }}>
                <Moon size={18} className="text-blue-400" />
              </motion.span>
            ) : (
              <motion.span key="day" initial={{ rotate: 90 }} animate={{ rotate: 0 }}>
                <Sun size={18} className="text-amber-400" />
              </motion.span>
            )}
          </AnimatePresence>
          <span className={connected ? 'text-green-400' : 'text-red-400'}>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </header>

      <div className="flex gap-4 p-4 h-[calc(100vh-60px)]">
        <div className="flex-1 flex flex-col items-center justify-center relative">
          {gameState.players.length === 0 ? (
            <ModelConfigPanel onStartGame={startGame} />
          ) : (
            <GameTable
              players={gameState.players}
              isNight={isNightPhase}
              speeches={speeches.slice(-3)}
            />
          )}
        </div>

        <div className="w-80 flex flex-col gap-4 overflow-hidden">
          <ThinkingPanel chunks={thinkingChunks} />
          <LogPanel logs={logs} />
        </div>
      </div>

      <AnimatePresence>
        {gameState.phase === 'GAME_OVER' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
          >
            <div className="bg-slate-800 rounded-xl p-8 text-center max-w-md">
              <Skull size={48} className="mx-auto mb-4 text-amber-400" />
              <h2 className="text-2xl font-bold mb-2">Game Over</h2>
              <p className="text-lg mb-4">
                Winner: <span className="text-amber-400 font-bold">{gameState.winner}</span>
              </p>
              <div className="text-sm text-slate-400 space-y-1">
                {gameState.players.map(p => (
                  <div key={p.id} className="flex justify-between">
                    <span>{p.name || `Player ${p.id}`}</span>
                    <span>{p.role || '?'}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
