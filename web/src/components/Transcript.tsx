'use client';

import React, { useRef, useEffect, useMemo } from 'react';
import { Bot, User, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';
import type { Turn, TranscriptDelta } from '@/types';

/* ---- Props ---- */
export interface TranscriptProps {
  /** Finalized / persisted turns (from the REST API) */
  turns: Turn[];
  /** Streaming deltas arriving via the LiveKit data channel */
  liveDeltas: TranscriptDelta[];
}

/* ---- Helpers ---- */
function formatTime(iso?: string): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '';
  }
}

/* ---- Component ---- */
export default function Transcript({ turns, liveDeltas }: TranscriptProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  /* Merge finalized turns with live streaming deltas.
     Live deltas whose turn_idx already exists in `turns` (i.e. finalized)
     are ignored.  Only deltas for new turn indices are shown. */
  const merged = useMemo(() => {
    const finalizedSet = new Set(turns.map((t) => t.idx));

    // Group live deltas by turn_idx, keeping latest
    const liveMap = new Map<number, TranscriptDelta>();
    for (const d of liveDeltas) {
      if (!finalizedSet.has(d.turn_idx)) {
        const existing = liveMap.get(d.turn_idx);
        if (!existing || d.timestamp >= existing.timestamp) {
          liveMap.set(d.turn_idx, d);
        }
      }
    }

    const liveTurns: { delta: TranscriptDelta; isFinal: boolean }[] = Array.from(liveMap.values())
      .sort((a, b) => a.turn_idx - b.turn_idx)
      .map((d) => ({ delta: d, isFinal: d.is_final }));

    return { finalizedTurns: turns, liveTurns };
  }, [turns, liveDeltas]);

  // Auto‑scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [merged]);

  const empty = merged.finalizedTurns.length === 0 && merged.liveTurns.length === 0;

  return (
    <div className="flex flex-col gap-3 overflow-y-auto max-h-[60vh] p-4 scrollbar-thin">
      {empty && (
        <p className="text-center text-gray-500 py-12 text-sm">
          Waiting for conversation to begin…
        </p>
      )}

      {/* ---- Finalized turns ---- */}
      {merged.finalizedTurns.map((turn) => (
        <TurnBubble
          key={`final-${turn.idx}`}
          speaker={turn.speaker}
          text={turn.text}
          interrupted={turn.interrupted}
          time={formatTime(turn.started_at)}
          isFinal
        />
      ))}

      {/* ---- Live / streaming turns ---- */}
      {merged.liveTurns.map(({ delta, isFinal }) => (
        <TurnBubble
          key={`live-${delta.turn_idx}`}
          speaker={delta.speaker}
          text={delta.text}
          interrupted={delta.interrupted}
          isFinal={isFinal}
          streaming={!isFinal}
        />
      ))}

      <div ref={bottomRef} />
    </div>
  );
}

/* ---- Single chat bubble ---- */
interface TurnBubbleProps {
  speaker: 'agent' | 'user';
  text: string;
  interrupted: boolean;
  time?: string;
  isFinal: boolean;
  streaming?: boolean;
}

function TurnBubble({ speaker, text, interrupted, time, isFinal, streaming }: TurnBubbleProps) {
  const isUser = speaker === 'user';

  return (
    <div
      className={clsx(
        'flex items-end gap-2 animate-fade-in max-w-[85%]',
        isUser ? 'self-end flex-row-reverse' : 'self-start',
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center',
          isUser ? 'bg-blue-600/20 text-blue-400' : 'bg-gray-700/60 text-gray-400',
        )}
      >
        {isUser ? <User size={14} /> : <Bot size={14} />}
      </div>

      {/* Bubble */}
      <div
        className={clsx(
          'rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
          isUser
            ? 'bg-blue-600 text-white rounded-br-md'
            : 'bg-gray-800 text-gray-100 rounded-bl-md',
          streaming && 'opacity-60',
        )}
      >
        {/* Speaker label */}
        <span
          className={clsx(
            'block text-[10px] font-semibold uppercase tracking-wider mb-0.5',
            isUser ? 'text-blue-200' : 'text-gray-400',
          )}
        >
          {isUser ? 'Customer' : 'Agent'}
          {streaming && (
            <span className="ml-1.5 inline-flex gap-0.5">
              <span className="animate-pulse">●</span>
            </span>
          )}
        </span>

        {/* Text */}
        <span className={clsx(interrupted && isFinal && 'line-through decoration-red-400/60')}>
          {text}
        </span>

        {/* Interrupted badge */}
        {interrupted && isFinal && (
          <span className="flex items-center gap-1 mt-1 text-[10px] text-yellow-400">
            <AlertTriangle size={10} />
            Interrupted
          </span>
        )}

        {/* Time */}
        {time && (
          <span className="block text-[10px] mt-1 opacity-40">{time}</span>
        )}
      </div>
    </div>
  );
}
