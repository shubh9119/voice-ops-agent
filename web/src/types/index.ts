/* ---- Types ---- */

export interface Agent {
  id: string;
  name: string;
  system_prompt: string;
  greeting: string;
  voice: string;
  model: string;
  created_at: string;
}

export interface Turn {
  idx: number;
  speaker: 'agent' | 'user';
  text: string;
  started_at: string;
  interrupted: boolean;
}

export interface TurnMetric {
  turn_idx: number;
  transcription_delay_ms: number;
  end_of_turn_delay_ms: number;
  llm_ttft_ms: number;
  tts_ttfb_ms: number;
  e2e_ms: number;
}

export interface ComplianceResult {
  rule: string;
  method: string;
  status: 'pass' | 'fail' | 'inconclusive';
  offending_line: string | null;
  detail: string;
}

export interface Call {
  id: string;
  agent_id: string;
  room_name: string;
  status: 'waiting' | 'active' | 'ended';
  started_at: string | null;
  ended_at: string | null;
  transcript?: Turn[];
  compliance?: ComplianceResult[];
  metrics?: TurnMetric[];
  token?: string;
  livekit_url?: string;
}

export interface TranscriptDelta {
  type: 'transcript';
  turn_idx: number;
  speaker: 'agent' | 'user';
  text: string;
  is_final: boolean;
  interrupted: boolean;
  timestamp: number;
}

export interface CreateAgentPayload {
  name: string;
  system_prompt: string;
  greeting: string;
  voice: string;
  model: string;
}
