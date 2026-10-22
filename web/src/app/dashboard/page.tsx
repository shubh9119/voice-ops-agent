'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Radio,
  RefreshCw,
  ChevronRight,
  ExternalLink,
  ChevronDown,
  PhoneCall,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { fetchCalls, fetchCall, fetchMetrics } from '@/lib/api';
import type { Call, TurnMetric } from '@/types';
import ComplianceBadge from '@/components/ComplianceBadge';
import LatencyChart from '@/components/LatencyChart';

export default function DashboardPage() {
  const [calls, setCalls] = useState<Call[]>([]);
  const [selectedCall, setSelectedCall] = useState<Call | null>(null);
  const [selectedMetrics, setSelectedMetrics] = useState<TurnMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'active' | 'ended'>('all');

  const loadCalls = async () => {
    try {
      setLoading(true);
      const data = await fetchCalls();
      setCalls(data);

      // Auto-select first ended call or first available call
      if (data.length > 0 && !selectedCall) {
        const target = data.find((c) => c.status === 'ended') || data[0];
        handleSelectCall(target.id);
      }
    } catch (err) {
      console.error('Failed to fetch dashboard calls:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectCall = async (callId: string) => {
    try {
      const [fullCall, metricsData] = await Promise.all([
        fetchCall(callId),
        fetchMetrics(callId).catch(() => []),
      ]);
      setSelectedCall(fullCall);
      setSelectedMetrics(metricsData);
    } catch (err) {
      console.error('Failed to load call detail:', err);
    }
  };

  useEffect(() => {
    loadCalls();
  }, []);

  const filteredCalls = calls.filter((c) => {
    if (filter === 'all') return true;
    return c.status === filter;
  });

  // Calculate compliance statistics across loaded calls
  const allCompliance = calls.flatMap((c) => c.compliance || []);
  const recordingAudits = allCompliance.filter((a) => a.rule === 'recording_disclosure_30s');
  const refundAudits = allCompliance.filter((a) => a.rule === 'no_refund_promise');

  const recPassRate =
    recordingAudits.length > 0
      ? Math.round(
          (recordingAudits.filter((a) => a.status === 'pass').length / recordingAudits.length) * 100
        )
      : 100;

  const refundPassRate =
    refundAudits.length > 0
      ? Math.round(
          (refundAudits.filter((a) => a.status === 'pass').length / refundAudits.length) * 100
        )
      : 100;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center space-x-3">
            <span>Operations & Compliance Dashboard</span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Real-time call monitoring, automated compliance auditing, and latency telemetry
          </p>
        </div>
        <button
          onClick={loadCalls}
          className="self-start sm:self-auto flex items-center space-x-1.5 bg-gray-900 hover:bg-gray-800 border border-gray-700 text-gray-200 px-3.5 py-2 rounded-lg text-sm font-medium transition-all"
        >
          <RefreshCw className="w-4 h-4 text-blue-400" />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">Total Calls</span>
            <PhoneCall className="w-4 h-4 text-blue-400" />
          </div>
          <span className="text-2xl font-bold text-white mt-2 block">{calls.length}</span>
          <span className="text-xs text-gray-500 mt-1 block">Live & past recorded calls</span>
        </div>

        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">Recording Disclosure</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <span className="text-2xl font-bold text-emerald-400 mt-2 block">{recPassRate}%</span>
          <span className="text-xs text-gray-500 mt-1 block">Stated within first 30 seconds</span>
        </div>

        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">No Refund Promise</span>
            <ShieldAlert className="w-4 h-4 text-purple-400" />
          </div>
          <span className="text-2xl font-bold text-purple-400 mt-2 block">{refundPassRate}%</span>
          <span className="text-xs text-gray-500 mt-1 block">Audited via LLM validator</span>
        </div>

        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">Active SFU Nodes</span>
            <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
          </div>
          <span className="text-2xl font-bold text-white mt-2 block">1 Node</span>
          <span className="text-xs text-emerald-400 mt-1 block">LiveKit v1.8 (Localhost)</span>
        </div>
      </div>

      {/* Main Grid: Calls List (Left) + Detail Telemetry (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Call Sessions List (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-200 text-sm">Call Log</h3>
            <div className="flex space-x-1 bg-gray-900 p-0.5 rounded-lg border border-gray-800 text-xs">
              {(['all', 'active', 'ended'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setFilter(t)}
                  className={`px-2.5 py-1 rounded font-medium capitalize transition-all ${
                    filter === t
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-gray-900/40 border border-gray-800 rounded-xl overflow-hidden divide-y divide-gray-800 max-h-[640px] overflow-y-auto">
            {filteredCalls.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-xs">No calls match this filter.</div>
            ) : (
              filteredCalls.map((c) => {
                const isSelected = selectedCall?.id === c.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => handleSelectCall(c.id)}
                    className={`p-4 cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-blue-600/10 border-l-4 border-l-blue-500'
                        : 'hover:bg-gray-800/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-gray-200">
                        call-{c.id}
                      </span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase ${
                          c.status === 'active'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                            : c.status === 'waiting'
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                            : 'bg-gray-800 text-gray-400'
                        }`}
                      >
                        {c.status}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-gray-500 mt-2">
                      <span>{c.room_name}</span>
                      <span>{c.started_at ? new Date(c.started_at).toLocaleTimeString() : 'Pending'}</span>
                    </div>

                    {/* Small badges */}
                    {c.compliance && c.compliance.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2.5">
                        {c.compliance.map((comp, idx) => (
                          <ComplianceBadge key={idx} result={comp} compact />
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Selected Call Detail (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {selectedCall ? (
            <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-5 space-y-6">
              {/* Header */}
              <div className="flex items-center justify-between pb-4 border-b border-gray-800">
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="font-bold text-gray-100 text-base">
                      Session Detail: <span className="font-mono text-blue-400">call-{selectedCall.id}</span>
                    </h3>
                  </div>
                  <span className="text-xs text-gray-400">
                    Room: {selectedCall.room_name} ? Status: {selectedCall.status}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <Link
                    href={`/call/${selectedCall.id}`}
                    className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-200 px-3 py-1.5 rounded-lg border border-gray-700 flex items-center space-x-1"
                  >
                    <ExternalLink className="w-3 h-3 text-blue-400" />
                    <span>Call View</span>
                  </Link>
                  <Link
                    href={`/operator/${selectedCall.id}`}
                    className="text-xs bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 px-3 py-1.5 rounded-lg flex items-center space-x-1 font-medium"
                  >
                    <span>Operator Panel</span>
                  </Link>
                </div>
              </div>

              {/* Compliance Breakdown Section */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center space-x-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>Compliance Audit Results</span>
                </h4>

                {!selectedCall.compliance || selectedCall.compliance.length === 0 ? (
                  <div className="p-4 bg-gray-950/60 rounded-lg text-xs text-gray-500 border border-gray-800">
                    Compliance checks run automatically when a call ends.
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {selectedCall.compliance.map((c, i) => (
                      <div
                        key={i}
                        className={`p-3 rounded-lg border text-xs space-y-1 ${
                          c.status === 'pass'
                            ? 'bg-emerald-950/20 border-emerald-900/40 text-emerald-300'
                            : c.status === 'fail'
                            ? 'bg-red-950/20 border-red-900/40 text-red-300'
                            : 'bg-amber-950/20 border-amber-900/40 text-amber-300'
                        }`}
                      >
                        <div className="flex items-center justify-between font-semibold">
                          <span className="font-mono">{c.rule}</span>
                          <span className="uppercase text-[10px] px-2 py-0.5 rounded font-bold bg-black/40">
                            {c.status} ({c.method})
                          </span>
                        </div>
                        <p className="text-gray-300 text-[11px]">{c.detail}</p>
                        {c.offending_line && (
                          <div className="mt-1 bg-black/50 p-2 rounded text-red-400 font-mono text-[10px]">
                            Offending quote: "{c.offending_line}"
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Latency Waterfall / Telemetry Chart */}
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center space-x-1.5">
                  <Activity className="w-4 h-4 text-blue-400" />
                  <span>5-Stage Latency Telemetry (Part G)</span>
                </h4>

                <LatencyChart metrics={selectedMetrics} />
              </div>

              {/* Transcript Preview */}
              {selectedCall.transcript && selectedCall.transcript.length > 0 && (
                <div className="space-y-3 pt-2">
                  <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Call Transcript ({selectedCall.transcript.length} turns)
                  </h4>
                  <div className="max-h-60 overflow-y-auto space-y-2 bg-gray-950/60 p-3 rounded-lg border border-gray-800 text-xs">
                    {selectedCall.transcript.map((t, idx) => (
                      <div key={idx} className="flex space-x-2">
                        <span
                          className={`font-semibold shrink-0 uppercase text-[10px] w-12 text-right ${
                            t.speaker === 'agent' ? 'text-blue-400' : 'text-emerald-400'
                          }`}
                        >
                          {t.speaker}:
                        </span>
                        <p className="text-gray-200">
                          {t.text}
                          {t.interrupted && (
                            <span className="ml-1 text-[10px] text-amber-400 italic font-mono">
                              [barge-in interrupted]
                            </span>
                          )}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-96 flex items-center justify-center border border-dashed border-gray-800 rounded-xl bg-gray-900/20 text-gray-500 text-sm">
              Select a call session from the list to view compliance and latency metrics.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
