'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ShieldAlert,
  Mic,
  MicOff,
  Radio,
  Sparkles,
  PhoneCall,
  Volume2,
  AlertCircle,
  EyeOff,
  UserCheck,
  RotateCcw,
} from 'lucide-react';
import { Room, RoomEvent, Track, RemoteTrack } from 'livekit-client';
import { getOperatorToken, fetchCall } from '@/lib/api';
import type { Call, Turn, TranscriptDelta } from '@/types';
import Transcript from '@/components/Transcript';
import WhisperPanel, { WhisperRecord } from '@/components/WhisperPanel';

export default function OperatorPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [call, setCall] = useState<Call | null>(null);
  const [room, setRoom] = useState<Room | null>(null);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Takeover state (Stretch goal)
  const [takeoverActive, setTakeoverActive] = useState(false);
  const [micMuted, setMicMuted] = useState(false);

  // Transcripts
  const [turns, setTurns] = useState<Turn[]>([]);
  const [liveDeltas, setLiveDeltas] = useState<TranscriptDelta[]>([]);

  // Whispers tracking
  const [whispers, setWhispers] = useState<WhisperRecord[]>([]);

  // Remote audio listener
  const audioContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let lkRoom: Room | null = null;

    async function init() {
      try {
        setConnecting(true);
        setError(null);

        // 1. Fetch Call & operator token
        const [callData, tokenData] = await Promise.all([
          fetchCall(id),
          getOperatorToken(id),
        ]);
        setCall(callData);

        // 2. Initialize Room (Operator Mode: hidden, listen-only by default)
        lkRoom = new Room({
          adaptiveStream: true,
          audioCaptureDefaults: {
            autoGainControl: true,
            echoCancellation: true,
            noiseSuppression: true,
          },
        });

        // 3. Audio track subscriptions (hear BOTH agent and customer)
        lkRoom.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => {
          if (track.kind === Track.Kind.Audio) {
            const audioElement = track.attach();
            audioElement.autoplay = true;
            if (audioContainerRef.current) {
              audioContainerRef.current.appendChild(audioElement);
            }
          }
        });

        // 4. Data channel listener (transcripts, whisper acks, agent state)
        lkRoom.on(RoomEvent.DataReceived, (payload: Uint8Array, participant, kind, topic) => {
          const decoded = new TextDecoder().decode(payload);

          if (topic === 'transcript') {
            try {
              const data = JSON.parse(decoded) as TranscriptDelta;
              setLiveDeltas((prev) => [...prev, data]);
            } catch (e) {
              console.error('Error parsing transcript delta:', e);
            }
          } else if (topic === 'whisper_ack') {
            try {
              const ack = JSON.parse(decoded);
              setWhispers((prev) =>
                prev.map((w) =>
                  w.text === ack.text ? { ...w, acknowledged: true } : w
                )
              );
            } catch (e) {
              console.error('Error parsing whisper ack:', e);
            }
          }
        });

        // 5. Connect room
        const wsUrl =
          process.env.NEXT_PUBLIC_LIVEKIT_URL || tokenData.livekit_url || 'ws://localhost:7880';
        await lkRoom.connect(wsUrl, tokenData.token);

        setRoom(lkRoom);
        setConnected(true);
      } catch (err: any) {
        console.error('Operator LiveKit error:', err);
        setError(err.message || 'Failed to connect operator session.');
      } finally {
        setConnecting(false);
      }
    }

    init();

    return () => {
      if (lkRoom) {
        lkRoom.disconnect();
      }
    };
  }, [id]);

  // Send Whisper via data channel
  const handleSendWhisper = async (text: string) => {
    if (!room) return;
    try {
      const whisperId = Math.random().toString(36).substring(7);
      const payload = JSON.stringify({
        text,
        type: 'whisper',
        id: whisperId,
        sent_at: Date.now() / 1000,
      });

      const encoder = new TextEncoder();
      await room.localParticipant.publishData(encoder.encode(payload), {
        topic: 'whisper',
        reliable: true,
      });

      setWhispers((prev) => [
        ...prev,
        {
          id: whisperId,
          text,
          sentAt: Date.now(),
          acknowledged: false,
        },
      ]);
    } catch (err) {
      alert(`Failed to transmit whisper: ${err}`);
    }
  };

  // Toggle Human Takeover (Stretch Goal)
  const handleToggleTakeover = async () => {
    if (!room) return;
    try {
      const willTakeover = !takeoverActive;
      const encoder = new TextEncoder();

      if (willTakeover) {
        // Send takeover signal to agent
        await room.localParticipant.publishData(
          encoder.encode(JSON.stringify({ action: 'start' })),
          { topic: 'takeover', reliable: true }
        );
        // Enable operator mic to speak to customer
        try {
          await room.localParticipant.setMicrophoneEnabled(true);
          setMicMuted(false);
        } catch (micErr) {
          console.warn('Microphone enable warning during takeover:', micErr);
        }
        setTakeoverActive(true);
      } else {
        // Mute mic & return control to agent
        try {
          await room.localParticipant.setMicrophoneEnabled(false);
        } catch {}
        await room.localParticipant.publishData(
          encoder.encode(JSON.stringify({ action: 'stop' })),
          { topic: 'takeover', reliable: true }
        );
        setTakeoverActive(false);
      }
    } catch (err) {
      alert(`Takeover failed: ${err}`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full flex-1 flex flex-col space-y-4">
      {/* Hidden audio element container for incoming speech from customer and agent */}
      <div ref={audioContainerRef} className="hidden" />

      {/* Operator Header Bar */}
      <div className="bg-gradient-to-r from-gray-900 via-gray-900 to-amber-950/30 border border-amber-500/30 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <EyeOff className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="font-bold text-gray-100 text-lg">
                Supervisor Console — <span className="font-mono text-amber-400">call-{id}</span>
              </h2>
              <span className="text-[11px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold uppercase tracking-wider">
                Hidden Observer
              </span>
            </div>
            <p className="text-xs text-gray-400">
              Customer cannot see you in room participants. You can hear both channels in real-time.
            </p>
          </div>
        </div>

        {/* Takeover Control (Stretch Goal) */}
        <div className="flex items-center space-x-3">
          <button
            onClick={handleToggleTakeover}
            disabled={!connected}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-lg ${
              takeoverActive
                ? 'bg-red-600 hover:bg-red-500 text-white animate-pulse shadow-red-600/30'
                : 'bg-amber-600 hover:bg-amber-500 text-white shadow-amber-600/20'
            } disabled:opacity-50`}
          >
            {takeoverActive ? (
              <>
                <RotateCcw className="w-4 h-4" />
                <span>Hand Back to AI Agent</span>
              </>
            ) : (
              <>
                <UserCheck className="w-4 h-4" />
                <span>Take Over Call</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Takeover Warning Banner */}
      {takeoverActive && (
        <div className="bg-red-500/10 border border-red-500/40 rounded-xl p-3 px-4 flex items-center justify-between text-red-300 text-xs font-medium animate-pulse">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-red-400 shrink-0" />
            <span>OPERATOR TAKEOVER ACTIVE: AI agent output is paused. You are speaking directly to the customer.</span>
          </div>
          <span className="font-mono text-[11px] bg-red-950 px-2 py-0.5 rounded border border-red-800">
            Microphone Live
          </span>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center space-x-3 text-red-400 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Grid: Transcript (Left) + Whisper Panel (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-[550px]">
        {/* Transcript Feed (7 cols) */}
        <div className="lg:col-span-7 flex flex-col bg-gray-900/30 border border-gray-800 rounded-xl overflow-hidden shadow-inner">
          <div className="px-5 py-3.5 border-b border-gray-800 bg-gray-950/60 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Radio className="w-4 h-4 text-blue-400" />
              <h3 className="font-semibold text-sm text-gray-200">Live Conversation Feed</h3>
            </div>
            <span className="text-[11px] text-gray-500 font-mono">
              Listening to Customer & Agent
            </span>
          </div>

          <div className="flex-1 p-4 overflow-hidden flex flex-col">
            <Transcript turns={turns} liveDeltas={liveDeltas} />
          </div>
        </div>

        {/* Whisper & Control Panel (5 cols) */}
        <div className="lg:col-span-5 flex flex-col">
          <WhisperPanel
            onSendWhisper={handleSendWhisper}
            whispers={whispers}
            disabled={!connected || takeoverActive}
          />
        </div>
      </div>
    </div>
  );
}
