'use client';

import { PR } from '@/lib/types';
import { PRCard } from './PRCard';
import { GitPullRequest } from 'lucide-react';

interface PRListProps {
  prs: PR[];
  repo?: string;
  onPRClick?: (pr: PR) => void;
  loading?: boolean;
}

function PRCardSkeleton() {
  return (
    <div className="p-5 rounded-2xl border border-white/5 bg-white/[0.02] animate-pulse">
      <div className="flex items-start gap-3 mb-3">
        <div className="w-8 h-8 rounded-lg bg-white/5" />
        <div className="flex-1">
          <div className="h-3 bg-white/5 rounded w-12 mb-2" />
          <div className="h-4 bg-white/5 rounded w-3/4 mb-1" />
          <div className="h-4 bg-white/5 rounded w-1/2" />
        </div>
        <div className="w-12 h-6 bg-white/5 rounded-lg" />
      </div>
      <div className="flex gap-2 mb-3">
        <div className="w-5 h-5 rounded-full bg-white/5" />
        <div className="h-3 bg-white/5 rounded w-20" />
      </div>
      <div className="flex gap-1.5 mb-3">
        <div className="h-5 bg-white/5 rounded-full w-16" />
        <div className="h-5 bg-white/5 rounded-full w-20" />
      </div>
      <div className="pt-3 border-t border-white/5 flex justify-between">
        <div className="flex gap-3">
          <div className="h-3 bg-white/5 rounded w-8" />
          <div className="h-3 bg-white/5 rounded w-8" />
          <div className="h-3 bg-white/5 rounded w-12" />
        </div>
        <div className="h-5 bg-white/5 rounded-lg w-16" />
      </div>
    </div>
  );
}

export function PRList({ prs, repo, onPRClick, loading = false }: PRListProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <PRCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (prs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
          <GitPullRequest className="w-8 h-8 text-slate-600" />
        </div>
        <h3 className="text-lg font-medium text-slate-400 mb-2">No pull requests found</h3>
        <p className="text-sm text-slate-600 max-w-sm">
          Try adjusting your search or select a different topic filter. You can also trigger a new analysis.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {prs.map((pr) => (
        <PRCard key={pr.id} pr={pr} repo={repo} onClick={onPRClick} />
      ))}
    </div>
  );
}
