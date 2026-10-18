import React from 'react';
import { Shield, ShieldAlert, ShieldCheck } from 'lucide-react';

export default function ConfidenceGauge({
  score = 0.91, // Decimal score 0.0 to 1.0
  result = 'manipulated', // 'authentic' | 'manipulated' | 'suspicious'
  showLabel = true,
}) {
  const percentage = Math.round(score * 100);

  const getTheme = () => {
    if (result === 'authentic') {
      return {
        color: '#10b981', // emerald
        gradient: 'from-emerald-500 to-teal-400',
        text: 'text-emerald-400',
        border: 'border-emerald-500/40',
        bg: 'bg-emerald-950/40',
        icon: ShieldCheck,
        label: 'Authentic Confidence Level',
      };
    }
    if (result === 'manipulated') {
      return {
        color: '#f43f5e', // rose
        gradient: 'from-rose-500 to-red-400',
        text: 'text-rose-400',
        border: 'border-rose-500/40',
        bg: 'bg-rose-950/40',
        icon: ShieldAlert,
        label: 'Manipulation Confidence Score',
      };
    }
    return {
      color: '#f59e0b', // amber
      gradient: 'from-amber-500 to-yellow-400',
      text: 'text-amber-400',
      border: 'border-amber-500/40',
      bg: 'bg-amber-950/40',
      icon: Shield,
      label: 'Anomalous Confidence Score',
    };
  };

  const theme = getTheme();
  const Icon = theme.icon;

  // SVG Gauge calculations
  const strokeWidth = 8;
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className={`p-6 rounded-2xl ${theme.bg} border ${theme.border} flex flex-col items-center justify-center space-y-4 text-center`}>
      
      {/* Gauge SVG Circular Bar */}
      <div className="relative w-36 h-36 flex items-center justify-center">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 120 120">
          {/* Background circle track */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            stroke="rgba(255, 255, 255, 0.1)"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Animated score indicator */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            stroke={theme.color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        {/* Center Display Score */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <Icon className={`w-6 h-6 ${theme.text} mb-1`} />
          <span className="text-3xl font-black text-white font-['Outfit'] tracking-tight">
            {percentage}%
          </span>
          <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400">
            Score
          </span>
        </div>
      </div>

      {showLabel && (
        <div className="space-y-1">
          <h4 className={`text-sm font-bold font-['Outfit'] ${theme.text}`}>
            {theme.label}
          </h4>
          <p className="text-xs text-slate-400 max-w-xs">
            Derived from multi-modal neural network tensor output values.
          </p>
        </div>
      )}

    </div>
  );
}
