'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Mic,
  MicOff,
  PhoneOff,
  Radio,
  ExternalLink,
  Volume2,
  AlertCircle,
  Copy,
  Check,
  ShieldAlert,
} from 'lucide-react';
import { Room, RoomEvent, Track, RemoteTrack, RemoteParticipant } from 'livekit-client';
import { fetchCall } from '@/lib/api';
import type { Call, Turn, TranscriptDelta } from '@/types';
import Transcript from '@/components/Transcript';
import AudioVisualizer from '@/components/AudioVisualizer';

export default function CustomerCallPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [call, setCall] = useState<Call | null>(null);
  const [room, setRoom] = useState<Room | null>(null);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(true);
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Transcripts
  const [turns, setTurns] = useState<Turn[]>([]);
  const [liveDeltas, setLiveDeltas] = useState<TranscriptDelta[]>([]);

  // Remote audio element
  const audioContainerRef = useRef<HTMLDivElement>(null);
  const [remoteAudioAttached, setRemoteAudioAttached] = useState(false);

  // Copied operator link state
  const [copied, setCopied] = useState(false);

  // Duration timer
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (connected) {
      timer = setInterval(() => setElapsed((prev) => prev + 1), 1000);
    }
    return () => clearInterval(timer);
  }, [connected]);

  // Connect to LiveKit
  useEffect(() => {
    let lkRoom: Room | null = null;

    async function init() {
      try {
        setConnecting(true);
        setError(null);

        // 1. Fetch Call details
        const callData = await fetchCall(id);
        setCall(callData);

        const token = callData.token;
        const wsUrl =
          process.env.NEXT_PUBLIC_LIVEKIT_URL || callData.livekit_url || 'ws://localhost:7880';

        if (!token) {
          throw new Error('Call session token missing.');
        }

        // 2. Initialize LiveKit Client Room
        lkRoom = new Room({
          adaptiveStream: true,
          dynacast: true,
          audioCaptureDefaults: {
            autoGainControl: true,
            echoCancellation: true,
            noiseSuppression: true,
          },
        });

        // 3. Audio track subscription
        lkRoom.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => {
          if (track.kind === Track.Kind.Audio) {
            const audioElement = track.attach();
            audioElement.autoplay = true;
            if (audioContainerRef.current) {
              audioContainerRef.current.appendChild(audioElement);
            }
            setRemoteAudioAttached(true);
          }
        });

        // 4. Data channel handling for live transcripts
        lkRoom.on(RoomEvent.DataReceived, (payload: Uint8Array, participant, kind, topic) => {
          if (topic === 'transcript') {
            try {
              const decoded = new TextDecoder().decode(payload);
              const data = JSON.parse(decoded) as TranscriptDelta;
              setLiveDeltas((prev) => [...prev, data]);
            } catch (e) {
              console.error('Failed to parse transcript packet:', e);
            }
          }
        });

        // 5. Connect room
        await lkRoom.connect(wsUrl, token);

        // 6. Resume browser audio context for crystal-clear output
        try {
          await lkRoom.startAudio();
        } catch {
          // Auto-resumes on first user gesture if browser policy requires it
        }

        // 7. Publish customer microphone track
        await lkRoom.localParticipant.setMicrophoneEnabled(true);

        setRoom(lkRoom);
        setConnected(true);
      } catch (err: any) {
        console.error('LiveKit connection error:', err);
        setError(err.message || 'Failed to connect to LiveKit voice server.');
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

  const toggleMic = async () => {
    if (!room) return;
    const willMute = !muted;
    await room.localParticipant.setMicrophoneEnabled(!willMute);
    setMuted(willMute);
  };

  const handleEndCall = async () => {
    if (room) {
      await room.disconnect();
    }
    router.push('/dashboard');
  };

  const formatSeconds = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const copyOperatorLink = () => {
    const url = `${window.location.origin}/operator/${id}`;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full flex-1 flex flex-col space-y-4">
      {/* Hidden audio element container for incoming agent speech */}
      <div ref={audioContainerRef} className="hidden" />

      {/* Top Header Card */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div
            className={`w-3.5 h-3.5 rounded-full ${
              connected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
            }`}
          />
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="font-bold text-gray-100 text-lg">
                Customer Call — <span className="font-mono text-blue-400">call-{id}</span>
              </h2>
              {connected && (
                <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                  {formatSeconds(elapsed)}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400">
              {connecting
                ? 'Negotiating WebRTC SDP offer/answer...'
                : connected
                ? 'Connected to LiveKit SFU (Opus 48kHz)'
                : 'Disconnected'}
            </p>
          </div>
        </div>

        {/* Share operator link badge */}
        <div className="flex items-center space-x-2">
          <button
            onClick={copyOperatorLink}
            className="flex items-center space-x-1.5 text-xs bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 px-3 py-1.5 rounded-lg transition-all"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied link!' : 'Copy Operator Link'}</span>
          </button>
          <a
            href={`/operator/${id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center space-x-1 text-xs bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 px-3 py-1.5 rounded-lg transition-all"
          >
            <ExternalLink className="w-3.5 h-3.5 text-blue-400" />
            <span>Open Operator in New Tab</span>
          </a>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center space-x-3 text-red-400 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 min-h-[520px]">
        {/* Left Column: Call Controls & Visualizer */}
        <div className="lg:col-span-1 flex flex-col space-y-4">
          <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-5 flex flex-col justify-between flex-1">
            <div className="space-y-4">
              <div className="text-center py-6">
                <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-xl shadow-blue-500/20 mb-3">
                  <Volume2 className="w-9 h-9 text-white animate-pulse" />
                </div>
                <h3 className="font-semibold text-white">Acme Voice Assistant</h3>
                <span className="text-xs text-gray-400">Streaming Live Audio</span>
              </div>

              {/* Audio Visualizer */}
              <div className="py-2">
                <AudioVisualizer isSpeaking={connected && !muted} />
              </div>

              <div className="bg-gray-950/80 rounded-lg p-3 text-xs text-gray-400 space-y-2 border border-gray-800">
                <div className="flex justify-between">
                  <span>Transport:</span>
                  <span className="text-gray-200 font-mono">WebRTC / UDP</span>
                </div>
                <div className="flex justify-between">
                  <span>Signalling:</span>
                  <span className="text-emerald-400 font-mono">Connected</span>
                </div>
                <div className="flex justify-between">
                  <span>Barge-in:</span>
                  <span className="text-blue-400 font-mono">Active (Silero VAD)</span>
                </div>
              </div>
            </div>

            {/* Bottom Controls */}
            <div className="pt-4 border-t border-gray-800 flex items-center justify-center space-x-4">
              <button
                onClick={toggleMic}
                disabled={!connected}
                className={`w-12 h-12 rounded-full flex items-center justify-center transition-all shadow-lg ${
                  muted
                    ? 'bg-amber-500 hover:bg-amber-600 text-white shadow-amber-500/20'
                    : 'bg-gray-800 hover:bg-gray-700 text-gray-200'
                }`}
                title={muted ? 'Unmute microphone' : 'Mute microphone'}
              >
                {muted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>

              <button
                onClick={handleEndCall}
                className="w-12 h-12 rounded-full bg-red-600 hover:bg-red-500 text-white flex items-center justify-center shadow-lg shadow-red-600/30 transition-all"
                title="Hang Up Call"
              >
                <PhoneOff className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Live Transcript */}
        <div className="lg:col-span-3 flex flex-col bg-gray-900/30 border border-gray-800 rounded-xl overflow-hidden shadow-inner">
          <div className="px-5 py-3.5 border-b border-gray-800 bg-gray-950/60 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Radio className="w-4 h-4 text-blue-400" />
              <h3 className="font-semibold text-sm text-gray-200">Real-Time Call Transcript</h3>
            </div>
            <span className="text-[11px] text-gray-500 font-mono">
              Synchronized via LiveKit Data Channel
            </span>
          </div>

          <div className="flex-1 p-4 overflow-hidden flex flex-col">
            <Transcript turns={turns} liveDeltas={liveDeltas} />
          </div>
        </div>
      </div>
    </div>
  );
}
