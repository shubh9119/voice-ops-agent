'use client';

import React from 'react';
import clsx from 'clsx';
import { ShieldCheck, ShieldAlert, ShieldQuestion } from 'lucide-react';
import type { ComplianceResult } from '@/types';

const config = {
  pass: {
    icon: ShieldCheck,
    label: 'Pass',
    bg: 'bg-green-500/10',
    text: 'text-green-400',
    border: 'border-green-500/20',
  },
  fail: {
    icon: ShieldAlert,
    label: 'Fail',
    bg: 'bg-red-500/10',
    text: 'text-red-400',
    border: 'border-red-500/20',
  },
  inconclusive: {
    icon: ShieldQuestion,
    label: 'Inconclusive',
    bg: 'bg-yellow-500/10',
    text: 'text-yellow-400',
    border: 'border-yellow-500/20',
  },
};

interface ComplianceBadgeProps {
  status?: ComplianceResult['status'];
  result?: ComplianceResult;
  size?: 'sm' | 'md';
  compact?: boolean;
  showLabel?: boolean;
  className?: string;
}

export default function ComplianceBadge({
  status,
  result,
  size = 'sm',
  compact = false,
  showLabel = true,
  className,
}: ComplianceBadgeProps) {
  const actualStatus = result?.status || status || 'inconclusive';
  const c = config[actualStatus];
  const Icon = c.icon;
  const iconSize = size === 'sm' || compact ? 12 : 16;
  const label = result?.rule ? `${result.rule}: ${c.label}` : c.label;

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full border font-medium',
        c.bg,
        c.text,
        c.border,
        compact ? 'px-2 py-0.5 text-[10px]' : size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-3 py-1 text-xs',
        className
      )}
    >
      <Icon size={iconSize} />
      {showLabel && label}
    </span>
  );
}

/* ---- Summary badge (aggregate) ---- */
export function ComplianceSummaryBadge({
  results,
  className,
}: {
  results?: ComplianceResult[];
  className?: string;
}) {
  if (!results || results.length === 0) {
    return (
      <span className={clsx('text-[10px] text-gray-500', className)}>--</span>
    );
  }

  const hasFail = results.some((r) => r.status === 'fail');
  const hasInconclusive = results.some((r) => r.status === 'inconclusive');

  if (hasFail) return <ComplianceBadge status="fail" className={className} />;
  if (hasInconclusive) return <ComplianceBadge status="inconclusive" className={className} />;
  return <ComplianceBadge status="pass" className={className} />;
}
