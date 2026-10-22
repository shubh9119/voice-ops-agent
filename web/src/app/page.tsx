'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  PhoneCall,
  UserCheck,
  Plus,
  Radio,
  Cpu,
  Volume2,
  Shield,
  ArrowRight,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import { fetchAgents, createCall, fetchCalls, createAgent } from '@/lib/api';
import type { Agent, Call } from '@/types';
import ComplianceBadge from '@/components/ComplianceBadge';

export default function HomePage() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingCall, setStartingCall] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Form state
  const [name, setName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState(
    'You are a friendly customer service representative for Acme Corp. Be concise, polite, and helpful.'
  );
  const [greeting, setGreeting] = useState(
    'Hello! Thanks for calling Acme Support. Please note that this call is recorded for quality assurance. How can I help you today?'
  );
  const [voice, setVoice] = useState('aura-2-thalia-en');
  const [model, setModel] = useState('llama-3.3-70b-versatile');

  const loadData = async () => {
    try {
      setLoading(true);
      const [agentList, callList] = await Promise.all([fetchAgents(), fetchCalls()]);
      setAgents(agentList);
      setCalls(callList.slice(0, 6)); // latest 6
    } catch (err) {
      console.error('Failed to load initial data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleStartCall = async (agentId: string) => {
    try {
      setStartingCall(agentId);
      const newCall = await createCall(agentId);
      router.push(`/call/${newCall.id}`);
    } catch (err) {
      alert(`Could not initiate call: ${err}`);
      setStartingCall(null);
    }
  };

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createAgent({
        name,
        system_prompt: systemPrompt,
        greeting,
        voice,
        model,
      });
      setShowCreateModal(false);
      setName('');
      loadData();
    } catch (err) {
      alert(`Failed to create agent: ${err}`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-10">
      {/* Hero section */}
      <div className="relative rounded-2xl bg-gradient-to-b from-gray-900 via-gray-900/60 to-gray-950 border border-gray-800 p-8 overflow-hidden shadow-2xl">
        <div className="absolute -right-16 -top-16 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            <span>Self-Hosted LiveKit WebRTC</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Operator-Guided Voice AI Agent
          </h1>
          <p className="text-gray-400 text-base leading-relaxed">
            Ultra low-latency speech pipeline with Silero VAD, Deepgram STT, Groq LLaMA 3.3, and Deepgram TTS. Includes real-time hidden operator whisper, human takeover, and automated post-call compliance audits.
          </p>
          <div className="flex flex-wrap gap-4 pt-2">
            <div className="flex items-center space-x-2 text-xs text-gray-400 bg-gray-950/80 px-3 py-1.5 rounded-lg border border-gray-800">
              <Cpu className="w-3.5 h-3.5 text-blue-400" />
              <span>Groq LLM ~95ms TTFT</span>
            </div>
            <div className="flex items-center space-x-2 text-xs text-gray-400 bg-gray-950/80 px-3 py-1.5 rounded-lg border border-gray-800">
              <Volume2 className="w-3.5 h-3.5 text-purple-400" />
              <span>Deepgram Nova-3 + Aura</span>
            </div>
            <div className="flex items-center space-x-2 text-xs text-gray-400 bg-gray-950/80 px-3 py-1.5 rounded-lg border border-gray-800">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span>Automated Compliance Auditing</span>
            </div>
          </div>
        </div>
      </div>

      {/* Agents Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-100">Select Voice Agent</h2>
            <p className="text-xs text-gray-400">Launch a live WebRTC audio call session</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center space-x-1.5 bg-gray-900 hover:bg-gray-800 text-gray-200 border border-gray-700 px-3.5 py-2 rounded-lg text-sm font-medium transition-all"
          >
            <Plus className="w-4 h-4 text-blue-400" />
            <span>New Agent</span>
          </button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="h-48 bg-gray-900/40 border border-gray-800 rounded-xl animate-pulse" />
            <div className="h-48 bg-gray-900/40 border border-gray-800 rounded-xl animate-pulse" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className="bg-gray-900/60 border border-gray-800 hover:border-gray-700 rounded-xl p-5 flex flex-col justify-between transition-all group hover:shadow-xl hover:shadow-blue-500/5"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-lg text-white group-hover:text-blue-400 transition-colors">
                        {agent.name}
                      </h3>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className="text-[11px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded font-mono">
                          {agent.model}
                        </span>
                        <span className="text-[11px] bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded font-mono">
                          {agent.voice}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-950/70 rounded-lg p-2.5 border border-gray-800/80">
                    <span className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider block mb-1">
                      Initial Greeting
                    </span>
                    <p className="text-xs text-gray-300 line-clamp-2 italic">
                      "{agent.greeting}"
                    </p>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-gray-800 flex items-center justify-between">
                  <button
                    onClick={() => handleStartCall(agent.id)}
                    disabled={startingCall === agent.id}
                    className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 px-4 rounded-lg text-sm flex items-center justify-center space-x-2 transition-all shadow-lg shadow-blue-600/20 disabled:opacity-50"
                  >
                    <PhoneCall className="w-4 h-4" />
                    <span>{startingCall === agent.id ? 'Connecting...' : 'Start Customer Call'}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Calls Feed */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-100">Recent Sessions</h2>
            <p className="text-xs text-gray-400">Live & past call sessions and compliance audits</p>
          </div>
          <button
            onClick={loadData}
            className="text-xs text-gray-400 hover:text-white flex items-center space-x-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        {calls.length === 0 ? (
          <div className="text-center py-10 bg-gray-900/30 border border-dashed border-gray-800 rounded-xl text-gray-400 text-sm">
            No calls recorded yet. Click "Start Customer Call" above to begin.
          </div>
        ) : (
          <div className="bg-gray-900/40 border border-gray-800 rounded-xl overflow-hidden divide-y divide-gray-800">
            {calls.map((c) => (
              <div
                key={c.id}
                className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-gray-800/30 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-3">
                    <span className="font-mono text-sm font-semibold text-gray-200">
                      call-{c.id}
                    </span>
                    <span
                      className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                        c.status === 'active'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                          : c.status === 'waiting'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                          : 'bg-gray-800 text-gray-400'
                      }`}
                    >
                      {c.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 flex items-center space-x-3">
                    <span>Room: {c.room_name}</span>
                    <span>?</span>
                    <span>
                      {c.started_at
                        ? new Date(c.started_at).toLocaleString()
                        : 'Not started'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => router.push(`/call/${c.id}`)}
                    className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-200 px-3 py-1.5 rounded-lg border border-gray-700 flex items-center space-x-1 transition-all"
                  >
                    <PhoneCall className="w-3.5 h-3.5 text-blue-400" />
                    <span>Customer View</span>
                  </button>
                  <button
                    onClick={() => router.push(`/operator/${c.id}`)}
                    className="text-xs bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 px-3 py-1.5 rounded-lg flex items-center space-x-1 transition-all font-medium"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    <span>Operator Panel</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New Agent Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Create New Voice Agent</h3>
            <form onSubmit={handleCreateAgent} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-gray-300 block mb-1">
                  Agent Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Billing Support"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-300 block mb-1">
                  Initial Greeting (Must include recording disclosure)
                </label>
                <textarea
                  rows={2}
                  required
                  value={greeting}
                  onChange={(e) => setGreeting(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-300 block mb-1">
                  System Prompt
                </label>
                <textarea
                  rows={4}
                  required
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500 font-mono text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-300 block mb-1">
                    LLM Model
                  </label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 font-mono text-xs"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-300 block mb-1">
                    Voice ID
                  </label>
                  <input
                    type="text"
                    value={voice}
                    onChange={(e) => setVoice(e.target.value)}
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 font-mono text-xs"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm rounded-lg"
                >
                  Save Agent
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
