import React from 'react';
import { CheckCircle2, AlertOctagon, HelpCircle, Loader2 } from 'lucide-react';

export default function StatusBadge({
  status = 'authentic', // 'authentic' | 'manipulated' | 'suspicious' | 'processing'
  size = 'md', // 'sm' | 'md'
}) {
  const configs = {
    authentic: {
      label: 'Likely authentic',
      icon: CheckCircle2,
      style: 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60',
    },
    manipulated: {
      label: 'Potentially manipulated',
      icon: AlertOctagon,
      style: 'bg-rose-950/80 text-rose-400 border-rose-800/60',
    },
    suspicious: {
      label: 'Needs review',
      icon: HelpCircle,
      style: 'bg-amber-950/80 text-amber-400 border-amber-800/60',
    },
    processing: {
      label: 'In progress',
      icon: Loader2,
      iconClass: 'animate-spin',
      style: 'bg-cyan-950/80 text-cyan-400 border-cyan-800/60',
    },
  };

  const config = configs[status] || configs.authentic;
  const Icon = config.icon;

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs gap-1' : 'px-3 py-1 text-xs font-semibold gap-1.5';

  return (
    <span className={`inline-flex items-center rounded-full border ${config.style} ${sizeClasses}`}>
      <Icon className={`w-3.5 h-3.5 ${config.iconClass || ''}`} />
      <span>{config.label}</span>
    </span>
  );
}
