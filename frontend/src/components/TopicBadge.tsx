'use client';

import { TOPIC_COLORS } from '@/lib/types';

interface TopicBadgeProps {
  topic: string;
  size?: 'sm' | 'md';
}

export function TopicBadge({ topic, size = 'md' }: TopicBadgeProps) {
  const colors = TOPIC_COLORS[topic.toLowerCase()] || TOPIC_COLORS.other;

  return (
    <span
      className={`inline-flex items-center rounded-full border font-medium capitalize
        ${colors.bg} ${colors.text} ${colors.border}
        ${size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs'}
      `}
    >
      {topic}
    </span>
  );
}
