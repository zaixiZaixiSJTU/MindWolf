export interface PlayerInfo {
  id: number;
  name: string;
  is_alive: boolean;
  revealed_role: string | null;
  role?: string;
  faction?: string;
}

export interface GameState {
  phase: string;
  round: number;
  players: PlayerInfo[];
  winner: string | null;
}

export interface WSMessage {
  type: string;
  payload: Record<string, unknown>;
}

export interface LogEntry {
  ts: number;
  type: string;
  player_id?: number;
  phase?: string;
  round?: number;
  model?: string;
  response?: string;
  elapsed_sec?: number;
  speech?: string;
  deaths?: string;
  winner?: string;
}

export interface MemoryEvent {
  id: string;
  round: number;
  speaker_id: number;
  target_id: number | null;
  event_type: string;
  content: string;
  current_weight: number;
  is_contradicted: boolean;
}
