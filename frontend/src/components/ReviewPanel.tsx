'use client';

import { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Send,
  Loader2,
  ThumbsUp,
  ThumbsDown,
  MessageCircle,
  ShieldAlert,
  ExternalLink,
  FileText,
  AlertTriangle,
} from 'lucide-react';
import { PR, GeneratedReview, CommentAnalysis, TicketEvaluation } from '@/lib/types';
import { reviewApi } from '@/lib/api';

interface ReviewPanelProps {
  pr: PR;
  repo: string;
}

type ReviewState = 'idle' | 'loading' | 'generated' | 'submitting' | 'submitted' | 'escalated';

const COMMENT_STATUS_CONFIG = {
  applied: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Applied' },
  partial: { icon: AlertCircle, color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'Partial' },
  not_applied: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Not Applied' },
};

const RISK_CONFIG: Record<string, { color: string; bg: string; border: string; label: string }> = {
  low: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', label: 'Low Risk' },
  medium: { color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', label: 'Medium Risk' },
  high: { color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/20', label: 'High Risk' },
  critical: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', label: 'Critical Risk' },
};

export function ReviewPanel({ pr, repo }: ReviewPanelProps) {
  const [state, setState] = useState<ReviewState>('idle');
  const [review, setReview] = useState<GeneratedReview | null>(null);
  const [error, setError] = useState('');
  const [submitResult, setSubmitResult] = useState<{ github_review_id: number; fallback?: string } | null>(null);

  const generateReview = async () => {
    setState('loading');
    setError('');
    try {
      const data: GeneratedReview = await reviewApi.generate(pr.number, repo);
      setReview(data);
      // If AI flags this as needing human review, escalate
      if (data.needs_human_review) {
        setState('escalated');
      } else {
        setState('generated');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate review');
      setState('idle');
    }
  };

  const submitReview = async () => {
    if (!review) return;
    setState('submitting');
    setError('');
    try {
      const result = await reviewApi.submit(pr.number, repo, review.body, review.event);
      setSubmitResult(result);
      setState('submitted');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit review');
      setState('generated');
    }
  };

  // --- IDLE ---
  if (state === 'idle') {
    return (
      <div className="p-6 rounded-2xl border border-purple-500/20 bg-purple-500/5">
        <h2 className="text-sm font-semibold text-purple-300 uppercase tracking-wider mb-3">
          AI Review
        </h2>
        <p className="text-xs text-slate-400 mb-4">
          Analyzes comments, ticket, code quality, and engineering criteria to give you an honest opinion.
        </p>
        <button
          onClick={generateReview}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-500 rounded-xl text-sm font-medium text-white transition-all"
        >
          <Sparkles className="w-4 h-4" />
          Generate Review
        </button>
        {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
      </div>
    );
  }

  // --- LOADING ---
  if (state === 'loading') {
    return (
      <div className="p-6 rounded-2xl border border-purple-500/20 bg-purple-500/5">
        <div className="flex flex-col items-center gap-3 py-4">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
          <p className="text-sm text-slate-400">Analyzing ticket, comments & code...</p>
          <p className="text-xs text-slate-500">Evaluating against engineering criteria</p>
        </div>
      </div>
    );
  }

  // --- SUBMITTED ---
  if (state === 'submitted' && submitResult) {
    return (
      <div className="p-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/5">
        <div className="flex items-center gap-2 mb-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          <h2 className="text-sm font-semibold text-emerald-300">Review Submitted</h2>
        </div>
        <p className="text-xs text-slate-400 mb-3">
          Your review has been posted to GitHub.
        </p>
        {submitResult.fallback === 'issue_comment' && (
          <p className="text-xs text-yellow-400 mb-3">
            Posted as a comment instead of a formal review due to permission restrictions (you may be the PR author or the org limits OAuth app access).
          </p>
        )}
        <a
          href={pr.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-purple-400 hover:text-purple-300 transition-colors flex items-center gap-1"
        >
          <ExternalLink className="w-3 h-3" />
          View on GitHub
        </a>
        <button
          onClick={() => { setState('idle'); setReview(null); setSubmitResult(null); }}
          className="w-full mt-3 px-4 py-2 rounded-xl border border-white/10 text-xs text-slate-400 hover:text-white hover:bg-white/5 transition-all"
        >
          Generate Another Review
        </button>
      </div>
    );
  }

  if (!review) return null;

  const viability = review.viability;
  const ticketEval = review.ticket_eval;
  const riskCfg = RISK_CONFIG[review.risk_level] || RISK_CONFIG.low;

  // --- ESCALATED (needs human review) ---
  if (state === 'escalated') {
    return (
      <div className="space-y-4">
        {/* Risk alert */}
        <div className={`p-6 rounded-2xl border ${riskCfg.border} ${riskCfg.bg}`}>
          <div className="flex items-center gap-2 mb-3">
            <ShieldAlert className={`w-5 h-5 ${riskCfg.color}`} />
            <h2 className={`text-sm font-semibold ${riskCfg.color} uppercase tracking-wider`}>
              Needs Your Review
            </h2>
          </div>
          <p className="text-sm text-slate-300 mb-3">
            {review.human_review_reason || 'The AI detected uncertainty or risk that requires your judgment.'}
          </p>

          {/* Show the AI's analysis so the human can make an informed decision */}
          <div className="p-3 rounded-lg bg-black/20 mb-3">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">AI Opinion (for your reference)</p>
            <div className="text-xs text-slate-400 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
              {review.body}
            </div>
          </div>

          {/* Ticket eval summary if relevant */}
          {ticketEval && ticketEval.ticket_assessment !== 'No linked ticket found.' && (
            <div className="p-3 rounded-lg bg-black/20 mb-3">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Ticket Assessment</p>
              <p className="text-xs text-slate-400">{ticketEval.ticket_assessment}</p>
              {ticketEval.is_redundant && (
                <p className="text-xs text-yellow-400 mt-1">⚠ Ticket may be redundant with existing functionality</p>
              )}
              {ticketEval.is_counterproductive && (
                <p className="text-xs text-red-400 mt-1">⚠ Implementation could be counterproductive</p>
              )}
            </div>
          )}

          <div className="flex gap-2">
            <a
              href={pr.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-white/10 hover:bg-white/15 rounded-xl text-sm font-medium text-white transition-all"
            >
              <ExternalLink className="w-4 h-4" />
              Review on GitHub
            </a>
            <button
              onClick={() => setState('generated')}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-white/10 hover:bg-white/5 rounded-xl text-xs text-slate-400 hover:text-white transition-all"
            >
              Send AI Review Anyway
            </button>
          </div>
        </div>

        {/* Viability summary */}
        <ViabilityCard viability={viability} />
      </div>
    );
  }

  // --- GENERATED (safe to auto-send) ---
  return (
    <div className="space-y-4">
      {/* Risk level badge */}
      <div className={`px-4 py-2 rounded-xl flex items-center gap-2 ${riskCfg.bg} border ${riskCfg.border}`}>
        <div className={`w-2 h-2 rounded-full ${riskCfg.color.replace('text-', 'bg-')}`} />
        <span className={`text-xs font-medium ${riskCfg.color}`}>{riskCfg.label}</span>
      </div>

      {/* Viability Score */}
      <ViabilityCard viability={viability} />

      {/* Ticket Evaluation */}
      {ticketEval && ticketEval.ticket_assessment !== 'No linked ticket found.' && (
        <div className="p-6 rounded-2xl border border-white/5 bg-white/[0.02]">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="w-4 h-4 text-blue-400" />
            <h2 className="text-sm font-semibold text-blue-300 uppercase tracking-wider">
              Ticket Evaluation
            </h2>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              {ticketEval.ticket_makes_sense ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <XCircle className="w-3.5 h-3.5 text-red-400" />
              )}
              <span className="text-slate-400">
                Ticket {ticketEval.ticket_makes_sense ? 'makes sense' : 'questionable'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {ticketEval.implementation_matches_ticket ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <XCircle className="w-3.5 h-3.5 text-red-400" />
              )}
              <span className="text-slate-400">
                Implementation {ticketEval.implementation_matches_ticket ? 'matches ticket' : 'diverges from ticket'}
              </span>
            </div>
            {ticketEval.is_redundant && (
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />
                <span className="text-yellow-400">Potentially redundant</span>
              </div>
            )}
            {ticketEval.is_counterproductive && (
              <div className="flex items-center gap-2">
                <XCircle className="w-3.5 h-3.5 text-red-400" />
                <span className="text-red-400">Potentially counterproductive</span>
              </div>
            )}
            <p className="text-slate-500 mt-2 italic">{ticketEval.ticket_assessment}</p>
            <p className="text-slate-500 italic">{ticketEval.implementation_assessment}</p>
          </div>
        </div>
      )}

      {/* Comment Analysis */}
      {review.comment_analysis.length > 0 && (
        <div className="p-6 rounded-2xl border border-white/5 bg-white/[0.02]">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Comment Analysis ({review.comment_analysis.length})
          </h2>
          <div className="space-y-2">
            {review.comment_analysis.map((c: CommentAnalysis, i: number) => {
              const cfg = COMMENT_STATUS_CONFIG[c.status] || COMMENT_STATUS_CONFIG.not_applied;
              const Icon = cfg.icon;
              return (
                <div key={i} className={`p-3 rounded-lg ${cfg.bg}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className={`w-3.5 h-3.5 ${cfg.color}`} />
                    <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
                    <span className="text-xs text-slate-500">by @{c.author}</span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2">{c.body}</p>
                  <p className="text-xs text-slate-500 mt-1 italic">{c.explanation}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* AI Opinion (read-only) */}
      <div className="p-6 rounded-2xl border border-purple-500/20 bg-purple-500/5">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 rounded bg-purple-500/20 flex items-center justify-center">
            <span className="text-purple-400 text-xs">AI</span>
          </div>
          <h2 className="text-sm font-semibold text-purple-300">Review Opinion</h2>
          <span className={`ml-auto text-xs font-medium px-2 py-0.5 rounded ${
            review.event === 'APPROVE' ? 'bg-emerald-500/20 text-emerald-400' :
            review.event === 'REQUEST_CHANGES' ? 'bg-orange-500/20 text-orange-400' :
            'bg-blue-500/20 text-blue-400'
          }`}>
            {review.event === 'APPROVE' ? 'Approve' :
             review.event === 'REQUEST_CHANGES' ? 'Request Changes' : 'Comment'}
          </span>
        </div>
        <div className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto pr-2">
          {review.body}
        </div>
      </div>

      {/* Submit button */}
      <button
        onClick={submitReview}
        disabled={state === 'submitting'}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-500 disabled:bg-purple-600/30 disabled:cursor-not-allowed rounded-xl text-sm font-medium text-white transition-all"
      >
        {state === 'submitting' ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Submitting...
          </>
        ) : (
          <>
            <Send className="w-4 h-4" />
            Send Review to GitHub
          </>
        )}
      </button>
      {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
    </div>
  );
}

// --- Viability card sub-component ---
function ViabilityCard({ viability }: { viability: GeneratedReview['viability'] }) {
  return (
    <div className="p-6 rounded-2xl border border-purple-500/20 bg-purple-500/5">
      <h2 className="text-sm font-semibold text-purple-300 uppercase tracking-wider mb-4">
        Viability Assessment
      </h2>
      <div className="flex items-center gap-4 mb-4">
        <div className="relative w-16 h-16">
          <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="none" stroke="currentColor" strokeWidth="4" className="text-white/5" />
            <circle
              cx="32" cy="32" r="28" fill="none" strokeWidth="4"
              strokeDasharray={`${(viability.viability_score / 100) * 175.9} 175.9`}
              strokeLinecap="round"
              className={viability.viability_score >= 70 ? 'text-emerald-400' : viability.viability_score >= 40 ? 'text-yellow-400' : 'text-red-400'}
              stroke="currentColor"
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white">
            {viability.viability_score}
          </span>
        </div>
        <p className="text-xs text-slate-400 flex-1">{viability.overall_assessment}</p>
      </div>

      {viability.strengths.length > 0 && (
        <div className="mb-3">
          <h3 className="text-xs font-semibold text-emerald-400 mb-1">Strengths</h3>
          <ul className="space-y-1">
            {viability.strengths.map((s, i) => (
              <li key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                <CheckCircle2 className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {viability.weaknesses.length > 0 && (
        <div className="mb-3">
          <h3 className="text-xs font-semibold text-red-400 mb-1">Weaknesses</h3>
          <ul className="space-y-1">
            {viability.weaknesses.map((w, i) => (
              <li key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                <XCircle className="w-3 h-3 text-red-400 mt-0.5 flex-shrink-0" />
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {viability.recommendations.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-yellow-400 mb-1">Recommendations</h3>
          <ul className="space-y-1">
            {viability.recommendations.map((r, i) => (
              <li key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                <AlertCircle className="w-3 h-3 text-yellow-400 mt-0.5 flex-shrink-0" />
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
