'use client';

import React, { useState } from 'react';
import { Send, Sparkles, MessageSquare, CheckCheck, Clock } from 'lucide-react';

export interface WhisperRecord {
  id: string;
  text: string;
  sentAt: number;
  acknowledged: boolean;
}

interface WhisperPanelProps {
  onSendWhisper: (text: string) => void;
  whispers: WhisperRecord[];
  disabled?: boolean;
}

const PRESETS = [
  'Offer a 10% promotional discount on their next monthly bill.',
  'Politely ask for the customer account or order number.',
  'Assure them we are running background line diagnostics now.',
  'If problem persists, offer free expedited technician dispatch.',
];

export default function WhisperPanel({
  onSendWhisper,
  whispers,
  disabled = false,
}: WhisperPanelProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || disabled) return;
    onSendWhisper(text);
    setInput('');
  };

  const handlePresetClick = (preset: string) => {
    if (disabled) return;
    onSendWhisper(preset);
  };

  return (
    <div className="flex flex-col h-full bg-gray-900/50 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between pb-3 border-b border-gray-800">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <h3 className="font-semibold text-gray-200 text-sm">Supervisor Whisper</h3>
        </div>
        <span className="text-[11px] font-medium text-amber-400/90 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
          Hidden from Customer
        </span>
      </div>

      {/* Preset Suggestions */}
      <div className="my-3">
        <label className="text-[11px] font-medium text-gray-400 uppercase tracking-wider block mb-2">
          Quick Suggestions
        </label>
        <div className="flex flex-wrap gap-1.5">
          {PRESETS.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              disabled={disabled}
              onClick={() => handlePresetClick(preset)}
              className="text-left text-xs bg-gray-800/80 hover:bg-gray-800 border border-gray-700/60 hover:border-blue-500/50 text-gray-300 hover:text-white px-2.5 py-1.5 rounded-lg transition-all duration-150 disabled:opacity-50"
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      {/* Whisper Input */}
      <form onSubmit={handleSubmit} className="mt-auto pt-3 border-t border-gray-800">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type private instruction for AI agent..."
            disabled={disabled}
            className="flex-1 bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || disabled}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 text-white font-medium px-4 py-2 rounded-lg text-sm flex items-center space-x-1.5 transition-all shadow-lg shadow-blue-600/20 disabled:shadow-none disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
            <span>Send</span>
          </button>
        </div>
      </form>

      {/* Whisper Feed / History */}
      {whispers.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-800">
          <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider block mb-2">
            Dispatched Whispers ({whispers.length})
          </span>
          <div className="space-y-2 max-h-36 overflow-y-auto pr-1">
            {whispers.map((w) => (
              <div
                key={w.id}
                className="bg-gray-950/70 border border-gray-800 rounded-lg p-2.5 flex items-start justify-between text-xs"
              >
                <div className="flex items-start space-x-2">
                  <MessageSquare className="w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0" />
                  <p className="text-gray-200">{w.text}</p>
                </div>
                <div className="shrink-0 ml-2">
                  {w.acknowledged ? (
                    <span className="flex items-center space-x-1 text-emerald-400 text-[10px]">
                      <CheckCheck className="w-3 h-3" />
                      <span>Injected</span>
                    </span>
                  ) : (
                    <span className="flex items-center space-x-1 text-amber-400 text-[10px]">
                      <Clock className="w-3 h-3 animate-spin" />
                      <span>Sending</span>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
