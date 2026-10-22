'use client';

import React, { useEffect, useRef, useState } from 'react';
import clsx from 'clsx';

interface AudioVisualizerProps {
  /** 0-1 audio level */
  level?: number;
  /** Whether speaking is active (creates animated waveform) */
  isSpeaking?: boolean;
  /** Number of bars */
  bars?: number;
  className?: string;
  color?: 'blue' | 'green' | 'red';
}

const colorMap = {
  blue: 'bg-blue-500',
  green: 'bg-green-500',
  red: 'bg-red-500',
};

export default function AudioVisualizer({
  level,
  isSpeaking = false,
  bars = 7,
  className,
  color = 'blue',
}: AudioVisualizerProps) {
  const [animLevels, setAnimLevels] = useState<number[]>(Array(bars).fill(0.15));

  useEffect(() => {
    if (level !== undefined) {
      setAnimLevels(
        Array.from({ length: bars }, (_, i) => {
          const threshold = (i + 1) / bars;
          return level >= threshold ? 0.3 + level * 0.7 : 0.15;
        })
      );
      return;
    }

    if (!isSpeaking) {
      setAnimLevels(Array(bars).fill(0.15));
      return;
    }

    // Oscillate randomly when isSpeaking is true
    const interval = setInterval(() => {
      setAnimLevels(
        Array.from({ length: bars }, () => 0.2 + Math.random() * 0.8)
      );
    }, 120);

    return () => clearInterval(interval);
  }, [level, isSpeaking, bars]);

  return (
    <div className={clsx('flex items-center justify-center gap-1.5 h-10', className)}>
      {animLevels.map((lvl, i) => (
        <div
          key={i}
          className={clsx(
            'w-1.5 h-full rounded-full transition-all duration-100 origin-center',
            colorMap[color]
          )}
          style={{
            transform: `scaleY(${lvl})`,
            opacity: lvl > 0.2 ? 1 : 0.35,
          }}
        />
      ))}
    </div>
  );
}
