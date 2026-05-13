'use client';

import Image from 'next/image';
import Link from 'next/link';
import { GitPullRequest, Plus, Minus, FileCode, ExternalLink, MessageSquare, ArrowRight } from 'lucide-react';
import { PR, RECOMMENDATION_CONFIG } from '@/lib/types';
import { TopicBadge } from './TopicBadge';
import { ScoreBadge } from './ScoreBadge';

interface PRCardProps {
  pr: PR;
  repo?: string;
  onClick?: (pr: PR) => void;
}

export function PRCard({ pr, repo, onClick }: PRCardProps) {
  const rec = RECOMMENDATION_CONFIG[pr.recommendation];

  return (
    <div
      onClick={() => onClick?.(pr)}
      className="group relative p-5 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/10 transition-all duration-200 cursor-pointer"
    >
      {/* Status indicator */}
      {pr.status === 'pending' && (
        <div className="absolute top-3 right-3 w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
      )}
      {pr.status === 'error' && (
        <div className="absolute top-3 right-3 w-2 h-2 rounded-full bg-red-400" />
      )}

      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
          <GitPullRequest className="w-4 h-4 text-slate-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-slate-500 font-mono">#{pr.number}</span>
          </div>
          <h3 className="text-sm font-medium text-white leading-snug line-clamp-2 group-hover:text-purple-300 transition-colors">
            {pr.title}
          </h3>
        </div>
        <ScoreBadge score={pr.score} />
      </div>

      {/* Author */}
      <div className="flex items-center gap-2 mb-3">
        {pr.authorAvatar ? (
          <Image
            src={pr.authorAvatar}
            alt={pr.author}
            width={20}
            height={20}
            className="rounded-full"
          />
        ) : (
          <div className="w-5 h-5 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
            <span className="text-[8px] font-bold text-white">{pr.author[0]?.toUpperCase()}</span>
          </div>
        )}
        <span className="text-xs text-slate-400">{pr.author}</span>
        <span className="text-xs text-slate-600">·</span>
        <span className="text-xs text-slate-500">
          {new Date(pr.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
        </span>
      </div>

      {/* Description */}
      {pr.summary && (
        <p className="text-xs text-slate-400 leading-relaxed mb-3 line-clamp-2">
          {pr.summary}
        </p>
      )}

      {/* Topics */}
      {pr.topics.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {pr.topics.slice(0, 3).map((topic) => (
            <TopicBadge key={topic} topic={topic} size="sm" />
          ))}
          {pr.topics.length > 3 && (
            <span className="text-[10px] text-slate-500 self-center">+{pr.topics.length - 3}</span>
          )}
        </div>
      )}

      {/* Footer stats */}
      <div className="flex items-center justify-between pt-3 border-t border-white/5">
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1 text-emerald-400">
            <Plus className="w-3 h-3" />
            {pr.additions.toLocaleString()}
          </span>
          <span className="flex items-center gap-1 text-red-400">
            <Minus className="w-3 h-3" />
            {pr.deletions.toLocaleString()}
          </span>
          <span className="flex items-center gap-1 text-slate-500">
            <FileCode className="w-3 h-3" />
            {pr.filesChanged.length} files
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Recommendation badge */}
          <span
            className={`px-2 py-0.5 rounded-lg text-[10px] font-semibold border
              ${rec.bg} ${rec.color} ${rec.border}`}
          >
            {rec.label}
          </span>
          {repo && (
            <Link
              href={`/pr/${pr.number}?repo=${encodeURIComponent(repo)}`}
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] text-purple-400 hover:text-purple-300 hover:bg-purple-500/10 transition-colors"
            >
              <ArrowRight className="w-3 h-3" />
              Review
            </Link>
          )}
          <a
            href={pr.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-slate-600 hover:text-slate-300 transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Reviewers */}
      {pr.reviewers && pr.reviewers.length > 0 && (
        <div className="mt-2 flex items-center gap-2">
          <MessageSquare className="w-3 h-3 text-slate-500 flex-shrink-0" />
          <div className="flex items-center gap-1">
            {pr.reviewers.slice(0, 4).map((r) => (
              <div
                key={r.login}
                title={`@${r.login} — ${r.state.toLowerCase().replace('_', ' ')}`}
                className="flex items-center gap-1"
              >
                {r.avatar ? (
                  <Image
                    src={r.avatar}
                    alt={r.login}
                    width={16}
                    height={16}
                    className={`rounded-full ring-1 ${
                      r.state === 'APPROVED' ? 'ring-emerald-500/50' :
                      r.state === 'CHANGES_REQUESTED' ? 'ring-orange-500/50' :
                      'ring-slate-500/30'
                    }`}
                  />
                ) : (
                  <div className={`w-4 h-4 rounded-full flex items-center justify-center text-[7px] font-bold ${
                    r.state === 'APPROVED' ? 'bg-emerald-500/20 text-emerald-400' :
                    r.state === 'CHANGES_REQUESTED' ? 'bg-orange-500/20 text-orange-400' :
                    'bg-slate-500/20 text-slate-400'
                  }`}>
                    {r.login[0]?.toUpperCase()}
                  </div>
                )}
              </div>
            ))}
            {pr.reviewers.length > 4 && (
              <span className="text-[10px] text-slate-500">+{pr.reviewers.length - 4}</span>
            )}
          </div>
          <span className="text-[10px] text-slate-500">
            {pr.reviewers.length} review{pr.reviewers.length !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* Similar PRs indicator */}
      {pr.similarPRs.length > 0 && (
        <div className="mt-2 flex items-center gap-1 text-[10px] text-yellow-500/70">
          <span>⚠</span>
          <span>Similar to #{pr.similarPRs.slice(0, 2).join(', #')}</span>
        </div>
      )}
    </div>
  );
}
