'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { TurnMetric } from '@/types';

interface LatencyChartProps {
  metrics: TurnMetric[];
}

export default function LatencyChart({ metrics }: LatencyChartProps) {
  if (!metrics || metrics.length === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center border border-dashed border-gray-800 rounded-xl bg-gray-950/40 text-gray-400 text-sm">
        <p>No latency data available for this session yet.</p>
        <span className="text-xs text-gray-600 mt-1">Data captures automatically upon agent response turns.</span>
      </div>
    );
  }

  // Calculate p50 and p95 for E2E
  const e2eValues = metrics.map((m) => m.e2e_ms || (m.transcription_delay_ms + m.end_of_turn_delay_ms + m.llm_ttft_ms + m.tts_ttfb_ms)).sort((a, b) => a - b);
  const p50 = e2eValues[Math.floor(e2eValues.length * 0.5)] || 0;
  const p95 = e2eValues[Math.floor(e2eValues.length * 0.95)] || 0;
  const avg = Math.round(e2eValues.reduce((a, b) => a + b, 0) / (e2eValues.length || 1));

  const chartData = metrics.map((m) => ({
    turn: `Turn ${m.turn_idx}`,
    STT: Math.round(m.transcription_delay_ms),
    'Turn Decision': Math.round(m.end_of_turn_delay_ms),
    'LLM TTFT': Math.round(m.llm_ttft_ms),
    'TTS TTFB': Math.round(m.tts_ttfb_ms),
    total: Math.round(m.e2e_ms),
  }));

  return (
    <div className="space-y-4">
      {/* Metric summary badges */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-3">
          <span className="text-[11px] text-gray-400 font-medium uppercase tracking-wider block">Avg E2E Latency</span>
          <span className="text-xl font-bold text-blue-400 mt-0.5 block">{avg} ms</span>
        </div>
        <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-3">
          <span className="text-[11px] text-gray-400 font-medium uppercase tracking-wider block">p50 Latency</span>
          <span className="text-xl font-bold text-emerald-400 mt-0.5 block">{Math.round(p50)} ms</span>
        </div>
        <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-3">
          <span className="text-[11px] text-gray-400 font-medium uppercase tracking-wider block">p95 Latency</span>
          <span className="text-xl font-bold text-amber-400 mt-0.5 block">{Math.round(p95)} ms</span>
        </div>
      </div>

      {/* Chart */}
      <div className="h-72 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
            <XAxis dataKey="turn" stroke="#6b7280" fontSize={11} tickLine={false} />
            <YAxis stroke="#6b7280" fontSize={11} tickLine={false} unit="ms" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#030712',
                borderColor: '#374151',
                borderRadius: '0.5rem',
                fontSize: '12px',
                color: '#f3f4f6',
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
              iconType="circle"
              iconSize={8}
            />
            <Bar dataKey="STT" stackId="a" fill="#3b82f6" name="STT Transcribe" />
            <Bar dataKey="Turn Decision" stackId="a" fill="#8b5cf6" name="Turn Decision (VAD)" />
            <Bar dataKey="LLM TTFT" stackId="a" fill="#ec4899" name="LLM First Token" />
            <Bar dataKey="TTS TTFB" stackId="a" fill="#10b981" name="TTS First Audio" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
