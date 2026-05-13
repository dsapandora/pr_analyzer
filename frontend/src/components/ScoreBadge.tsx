'use client';

interface ScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

function getScoreConfig(score: number) {
  if (score >= 80) {
    return {
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/30',
      ring: '#10b981',
      label: 'High Quality',
    };
  } else if (score >= 60) {
    return {
      color: 'text-yellow-400',
      bg: 'bg-yellow-500/10',
      border: 'border-yellow-500/30',
      ring: '#f59e0b',
      label: 'Medium Quality',
    };
  } else {
    return {
      color: 'text-red-400',
      bg: 'bg-red-500/10',
      border: 'border-red-500/30',
      ring: '#ef4444',
      label: 'Low Quality',
    };
  }
}

export function ScoreBadge({ score, size = 'md', showLabel = false }: ScoreBadgeProps) {
  const config = getScoreConfig(score);
  const circumference = 2 * Math.PI * 16;
  const offset = circumference - (circumference * score) / 100;

  if (size === 'lg') {
    return (
      <div className="flex flex-col items-center gap-2">
        <div className="relative w-20 h-20">
          <svg className="w-20 h-20 -rotate-90" viewBox="0 0 40 40">
            <circle cx="20" cy="20" r="16" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="3" />
            <circle
              cx="20"
              cy="20"
              r="16"
              fill="none"
              stroke={config.ring}
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              style={{ transition: 'stroke-dashoffset 0.5s ease' }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-xl font-bold ${config.color}`}>{score}</span>
          </div>
        </div>
        {showLabel && <span className={`text-xs font-medium ${config.color}`}>{config.label}</span>}
      </div>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg border text-xs font-semibold
        ${config.bg} ${config.color} ${config.border}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full`} style={{ background: config.ring }} />
      {score}
      {showLabel && <span className="font-normal opacity-70">/ 100</span>}
    </span>
  );
}
