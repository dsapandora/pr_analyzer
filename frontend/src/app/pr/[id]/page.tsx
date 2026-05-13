'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import {
  ArrowLeft,
  GitPullRequest,
  Plus,
  Minus,
  FileCode,
  ExternalLink,
  Copy,
  Check,
  MessageSquare,
  Crown,
  XOctagon,
  Loader2,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { PR, RelatedPR } from '@/lib/types';
import { prsApi, reviewApi } from '@/lib/api';
import { TopicBadge } from '@/components/TopicBadge';
import { ScoreBadge } from '@/components/ScoreBadge';
import { ChatPanel } from '@/components/ChatPanel';
import { ReviewPanel } from '@/components/ReviewPanel';
import { RECOMMENDATION_CONFIG } from '@/lib/types';

export default function PRDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const repo = searchParams.get('repo') || '';
  const prNumber = parseInt(params.id as string, 10);

  const [pr, setPR] = useState<PR | null>(null);
  const [relatedPRs, setRelatedPRs] = useState<RelatedPR[]>([]);
  const [primaryPR, setPrimaryPR] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [chatOpen, setChatOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [closingPR, setClosingPR] = useState<number | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      router.push('/');
      return;
    }
    fetchPR();
  }, [prNumber, repo]);

  const fetchPR = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await prsApi.getOne(prNumber, repo);
      setPR(data.pr);
      setRelatedPRs(data.relatedPRs || []);
      setPrimaryPR(data.primaryPR || null);
    } catch (err) {
      setError('Failed to load PR details');
    } finally {
      setLoading(false);
    }
  };

  const copyUrl = () => {
    if (pr?.url) {
      navigator.clipboard.writeText(pr.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-400 text-sm">Loading PR details...</p>
        </div>
      </div>
    );
  }

  if (error || !pr) {
    return (
      <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error || 'PR not found'}</p>
          <button
            onClick={() => router.back()}
            className="text-sm text-slate-400 hover:text-white transition-colors flex items-center gap-2 mx-auto"
          >
            <ArrowLeft className="w-4 h-4" />
            Go back
          </button>
        </div>
      </div>
    );
  }

  const handleCloseDuplicate = async (dupNumber: number) => {
    if (!primaryPR || !confirm(`Close PR #${dupNumber} as duplicate of #${primaryPR}?`)) return;
    setClosingPR(dupNumber);
    try {
      await reviewApi.closeDuplicate(dupNumber, repo, primaryPR);
      setRelatedPRs((prev) => prev.filter((r) => r.number !== dupNumber));
    } catch {
      alert('Failed to close PR');
    } finally {
      setClosingPR(null);
    }
  };

  const rec = RECOMMENDATION_CONFIG[pr.recommendation];

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-white">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-[#0a0f1a]/80 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Dashboard
          </button>
          <div className="flex-1" />
          <button
            onClick={() => setChatOpen(true)}
            className="flex items-center gap-2 px-4 py-1.5 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium text-white transition-all"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Chat with AI
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* PR Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-slate-500 font-mono text-sm">#{pr.number}</span>
            <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold border ${rec.bg} ${rec.color} ${rec.border}`}>
              {rec.label}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-4 leading-snug">{pr.title}</h1>
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              {pr.authorAvatar ? (
                <Image src={pr.authorAvatar} alt={pr.author} width={24} height={24} className="rounded-full" />
              ) : (
                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center text-[10px] font-bold">
                  {pr.author?.[0]?.toUpperCase()}
                </div>
              )}
              <span className="text-sm text-slate-300">{pr.author}</span>
            </div>
            <span className="text-slate-600">·</span>
            <span className="text-sm text-slate-500">
              {new Date(pr.createdAt).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
            </span>
            <a
              href={pr.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-white transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
              View on GitHub
            </a>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Description */}
            {pr.description && (
              <div className="p-6 rounded-2xl border border-white/5 bg-white/[0.02]">
                <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Description</h2>
                <div className="text-slate-300 leading-relaxed prose prose-invert prose-sm max-w-none prose-headings:text-slate-200 prose-a:text-purple-400 prose-a:no-underline hover:prose-a:underline prose-code:text-purple-300 prose-code:bg-white/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-pre:bg-white/5 prose-pre:border prose-pre:border-white/10 prose-img:rounded-lg prose-hr:border-white/10 prose-blockquote:border-purple-500/30 prose-blockquote:text-slate-400 prose-th:text-slate-300 prose-td:text-slate-400 prose-strong:text-slate-200 prose-li:marker:text-slate-500">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{pr.description}</ReactMarkdown>
                </div>
              </div>
            )}

            {/* AI Summary */}
            {pr.summary && (
              <div className="p-6 rounded-2xl border border-purple-500/20 bg-purple-500/5">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-5 h-5 rounded bg-purple-500/20 flex items-center justify-center">
                    <span className="text-purple-400 text-xs">AI</span>
                  </div>
                  <h2 className="text-sm font-semibold text-purple-300">AI Summary</h2>
                </div>
                <p className="text-slate-300 leading-relaxed mb-4">{pr.summary}</p>
                {pr.reasoning && (
                  <>
                    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Reasoning</h3>
                    <p className="text-slate-400 text-sm leading-relaxed">{pr.reasoning}</p>
                  </>
                )}
              </div>
            )}

            {/* Changed files */}
            {pr.filesChanged.length > 0 && (
              <div className="p-6 rounded-2xl border border-white/5 bg-white/[0.02]">
                <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
                  Changed Files ({pr.filesChanged.length})
                </h2>
                <div className="space-y-1">
                  {pr.filesChanged.map((file) => (
                    <div key={file} className="flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-white/5 transition-colors">
                      <FileCode className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                      <span className="text-xs text-slate-300 font-mono truncate">{file}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Score */}
            <div className="p-6 rounded-2xl border border-white/5 bg-white/[0.02] flex flex-col items-center">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 self-start">Quality Score</h2>
              <ScoreBadge score={pr.score} size="lg" showLabel />
            </div>

            {/* Stats */}
            <div className="p-6 rounded-2xl border border-white/5 bg-white/[0.02]">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Stats</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Additions</span>
                  <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
                    <Plus className="w-3 h-3" />{pr.additions.toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Deletions</span>
                  <span className="text-xs text-red-400 font-medium flex items-center gap-1">
                    <Minus className="w-3 h-3" />{pr.deletions.toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Files Changed</span>
                  <span className="text-xs text-white font-medium">{pr.filesChanged.length}</span>
                </div>
              </div>
            </div>

            {/* Topics */}
            <div className="p-6 rounded-2xl border border-white/5 bg-white/[0.02]">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Topics</h2>
              <div className="flex flex-wrap gap-2">
                {pr.topics.map((topic) => (
                  <TopicBadge key={topic} topic={topic} />
                ))}
              </div>
            </div>

            {/* AI Review */}
            <ReviewPanel pr={pr} repo={repo} />

            {/* Related PRs (enhanced) */}
            {relatedPRs.length > 0 && (
              <div className="p-6 rounded-2xl border border-yellow-500/20 bg-yellow-500/5">
                <h2 className="text-sm font-semibold text-yellow-400 uppercase tracking-wider mb-3">
                  Related PRs ({relatedPRs.length})
                </h2>
                <p className="text-xs text-slate-400 mb-3">
                  These PRs overlap with the same work.
                  {primaryPR && (
                    <> PR <span className="text-yellow-300 font-medium">#{primaryPR}</span> is the primary.</>
                  )}
                </p>
                <div className="space-y-2">
                  {relatedPRs.map((r) => (
                    <div
                      key={r.number}
                      className={`p-3 rounded-lg border ${
                        r.isPrimary ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-white/5 bg-white/[0.02]'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {r.isPrimary && <Crown className="w-3 h-3 text-emerald-400" />}
                        <button
                          onClick={() => router.push(`/pr/${r.number}?repo=${repo}`)}
                          className="text-xs font-medium text-yellow-300 hover:text-yellow-200 transition-colors"
                        >
                          #{r.number}
                        </button>
                        <span className="text-xs text-slate-500">Score: {r.score}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          RECOMMENDATION_CONFIG[r.recommendation]?.bg || ''
                        } ${RECOMMENDATION_CONFIG[r.recommendation]?.color || ''}`}>
                          {r.recommendation}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 line-clamp-1">{r.title}</p>
                      {r.summary && (
                        <p className="text-xs text-slate-500 mt-1 line-clamp-2">{r.summary}</p>
                      )}
                      {!r.isPrimary && primaryPR && primaryPR !== r.number && (
                        <button
                          onClick={() => handleCloseDuplicate(r.number)}
                          disabled={closingPR === r.number}
                          className="mt-2 flex items-center gap-1.5 text-xs text-red-400/70 hover:text-red-400 transition-colors"
                        >
                          {closingPR === r.number ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <XOctagon className="w-3 h-3" />
                          )}
                          Close as duplicate
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={copyUrl}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-sm text-slate-400 hover:text-white transition-all"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied!' : 'Copy URL'}
              </button>
              <a
                href={pr.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-sm text-slate-400 hover:text-white transition-all"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Open PR
              </a>
            </div>
          </div>
        </div>
      </main>

      {/* Chat panel */}
      <ChatPanel
        selectedPR={chatOpen ? pr : null}
        repo={repo}
        isOpen={chatOpen}
        onToggle={() => setChatOpen(o => !o)}
      />
    </div>
  );
}
