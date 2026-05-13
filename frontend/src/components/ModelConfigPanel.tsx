import { useState, useEffect } from 'react';
import { Cpu, Key, Eye, EyeOff, Zap } from 'lucide-react';

interface ProviderMap {
  [key: string]: {
    name: string;
    base_url: string;
    models: string[];
  };
}

const ROLES = ['WEREWOLF', 'WEREWOLF', 'WEREWOLF', 'WEREWOLF',
               'SEER', 'WITCH', 'HUNTER', 'IDIOT',
               'VILLAGER', 'VILLAGER', 'VILLAGER', 'VILLAGER'];

const ROLE_LABELS: Record<string, string> = {
  WEREWOLF: '狼人', SEER: '预言家', WITCH: '女巫',
  HUNTER: '猎人', IDIOT: '白痴', VILLAGER: '村民',
};

function loadKeys(): Record<string, string> {
  try {
    const raw = localStorage.getItem('werewolf_apikeys');
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}
function saveKeys(keys: Record<string, string>) {
  try { localStorage.setItem('werewolf_apikeys', JSON.stringify(keys)); } catch {}
}

export default function ModelConfigPanel({ onStartGame }: {
  onStartGame: (configs: any[], providerKeys: Record<string, string>) => void;
}) {
  const [providers, setProviders] = useState<ProviderMap>({});
  const [apiKeys, setApiKeys] = useState<Record<string, string>>(loadKeys);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

  const [globalProvider, setGlobalProvider] = useState('deepseek');
  const [globalModel, setGlobalModel] = useState('deepseek-chat');
  const [globalTemp, setGlobalTemp] = useState(0.8);

  const [players, setPlayers] = useState(
    Array.from({ length: 12 }, (_, i) => ({
      player_id: i + 1,
      provider: 'deepseek',
      model: 'deepseek-chat',
      temperature: 0.8,
    }))
  );

  useEffect(() => {
    fetch('http://localhost:8765/providers')
      .then(r => r.json())
      .then(d => {
        if (d.providers) {
          setProviders(d.providers);
          const first = Object.keys(d.providers)[0] || 'mock';
          setGlobalProvider(first);
          const firstModel = d.providers[first]?.models?.[0] || 'mock';
          setGlobalModel(firstModel);
          setPlayers(prev => prev.map(p => ({
            ...p, provider: first, model: firstModel,
          })));
        }
      })
      .catch(() => {
        setProviders({ mock: { name: 'Mock', base_url: '', models: ['mock'] } });
      });
  }, []);

  const providerList = Object.entries(providers);

  const applyGlobal = (prov: string, model: string, temp: number) => {
    setGlobalProvider(prov);
    setGlobalModel(model);
    setGlobalTemp(temp);
    setPlayers(prev => prev.map(p => ({ ...p, provider: prov, model, temperature: temp })));
  };

  const updatePlayer = (id: number, field: string, value: string | number) => {
    setPlayers(prev => prev.map(p => {
      if (p.player_id !== id) return p;
      const updated = { ...p, [field]: value };
      if (field === 'provider' && typeof value === 'string') {
        const firstModel = providers[value]?.models?.[0] || 'mock';
        updated.model = firstModel;
      }
      return updated;
    }));
  };

  const toggleShowKey = (prov: string) => {
    setShowKeys(prev => ({ ...prev, [prov]: !prev[prov] }));
  };

  const handleSaveKeys = () => {
    saveKeys(apiKeys);
  };

  const handleStart = () => {
    const playerConfigs = players.map(p => ({
      player_id: p.player_id,
      provider: p.provider,
      model: p.model,
      temperature: p.temperature,
    }));
    onStartGame(playerConfigs, apiKeys);
  };

  const roleBadge = (idx: number) => {
    const r = ROLES[idx];
    const cls = r === 'WEREWOLF' ? 'bg-red-800/40 text-red-400'
      : r === 'VILLAGER' ? 'bg-slate-700 text-slate-400'
      : 'bg-amber-800/30 text-amber-400';
    return <span className={`text-[10px] px-1 rounded ${cls}`}>{ROLE_LABELS[r]}</span>;
  };

  return (
    <div className="flex gap-4 max-w-3xl mx-auto">
      {/* Left: Player config */}
      <div className="flex-1 bg-slate-800 rounded-xl border border-slate-700 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Cpu size={18} className="text-cyan-400" />
          <h2 className="text-sm font-bold">Game Setup</h2>
        </div>

        {/* Global quick-apply */}
        <div className="flex items-center gap-2 mb-3 p-2 bg-slate-900 rounded-lg text-xs">
          <Zap size={14} className="text-amber-400 shrink-0" />
          <span className="text-slate-400 shrink-0">全部:</span>
          <select value={globalProvider} onChange={e => {
            const p = e.target.value;
            const m = providers[p]?.models?.[0] || 'mock';
            applyGlobal(p, m, globalTemp);
          }} className="bg-slate-700 text-slate-200 rounded px-1 py-0.5 border border-slate-600 w-28">
            {providerList.map(([k, v]) => <option key={k} value={k}>{v.name}</option>)}
          </select>
          <select value={globalModel} onChange={e => applyGlobal(globalProvider, e.target.value, globalTemp)}
            className="bg-slate-700 text-slate-200 rounded px-1 py-0.5 border border-slate-600 flex-1">
            {(providers[globalProvider]?.models || []).map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          <input type="range" min="0" max="1.5" step="0.1" value={globalTemp}
            onChange={e => applyGlobal(globalProvider, globalModel, parseFloat(e.target.value))}
            className="w-12" />
          <span className="text-cyan-400 w-5 text-right">{globalTemp.toFixed(1)}</span>
        </div>

        {/* Per-player rows */}
        <div className="space-y-0.5 max-h-72 overflow-y-auto">
          {players.map((p, i) => (
            <div key={p.player_id} className="flex items-center gap-1.5 text-[11px] bg-slate-900 rounded px-1.5 py-1">
              <span className="w-5 text-slate-500 text-right">#{p.player_id}</span>
              <span className="w-10">{roleBadge(i)}</span>
              <select value={p.provider} onChange={e => updatePlayer(p.player_id, 'provider', e.target.value)}
                className="bg-slate-700 text-slate-200 rounded px-1 py-0.5 border border-slate-600 w-24">
                {providerList.map(([k, v]) => <option key={k} value={k}>{v.name}</option>)}
              </select>
              <select value={p.model} onChange={e => updatePlayer(p.player_id, 'model', e.target.value)}
                className="bg-slate-700 text-slate-200 rounded px-1 py-0.5 border border-slate-600 flex-1">
                {(providers[p.provider]?.models || []).map(m => <option key={m} value={m}>{m}</option>)}
              </select>
              <input type="range" min="0" max="1.5" step="0.1" value={p.temperature}
                onChange={e => updatePlayer(p.player_id, 'temperature', parseFloat(e.target.value))}
                className="w-10" />
              <span className="text-cyan-400 w-5 text-right">{p.temperature.toFixed(1)}</span>
            </div>
          ))}
        </div>

        <button onClick={handleStart}
          className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-500 text-black rounded-lg font-bold hover:bg-amber-400 transition text-sm">
          <Cpu size={16} /> Start Game
        </button>
      </div>

      {/* Right: API Keys */}
      <div className="w-60 bg-slate-800 rounded-xl border border-slate-700 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Key size={16} className="text-amber-400" />
          <h2 className="text-sm font-bold">API Keys</h2>
        </div>
        <div className="space-y-2.5">
          {providerList.filter(([k]) => k !== 'mock').map(([key, val]) => (
            <div key={key}>
              <div className="text-[10px] text-slate-400 mb-0.5">{val.name}</div>
              <div className="flex gap-1">
                <input
                  type={showKeys[key] ? 'text' : 'password'}
                  value={apiKeys[key] || ''}
                  onChange={e => setApiKeys(prev => ({ ...prev, [key]: e.target.value }))}
                  placeholder="sk-..."
                  className="flex-1 bg-slate-900 text-slate-200 text-[11px] rounded px-2 py-1 border border-slate-600 outline-none focus:border-cyan-500"
                />
                <button onClick={() => toggleShowKey(key)}
                  className="text-slate-500 hover:text-slate-300 shrink-0">
                  {showKeys[key] ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>
          ))}
        </div>
        <button onClick={handleSaveKeys}
          className="mt-3 w-full text-[11px] bg-slate-700 hover:bg-slate-600 text-slate-300 rounded py-1 transition">
          Save keys locally
        </button>
        <p className="text-[9px] text-slate-500 mt-1.5 leading-relaxed">
          Keys stored in browser localStorage. Sent to backend in memory only, never written to disk.
        </p>
      </div>
    </div>
  );
}
