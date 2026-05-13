'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import {
  GitPullRequest,
  RefreshCw,
  LogOut,
  ChevronDown,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Clock,
  BarChart3,
  Loader2,
} from 'lucide-react';
import { PR, AnalysisJob, IngestionJob, Repository } from '@/lib/types';
import { prsApi, analyzeApi, reposApi, authApi, criteriaApi } from '@/lib/api';
import { PRList } from '@/components/PRList';
import { SearchBar } from '@/components/SearchBar';
import { ChatPanel } from '@/components/ChatPanel';
import { TopicBadge } from '@/components/TopicBadge';

const TOPICS = ['All', 'vectordb', 'engine', 'llms', 'integrations', 'ui', 'bugfix', 'docs', 'testing', 'devops', 'other'];

interface UserInfo {
  login: string;
  name: string;
  avatar_url: string;
}

function getUserFromToken(token: string): UserInfo | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return {
      login: payload.login || payload.sub || '',
      name: payload.name || payload.login || '',
      avatar_url: payload.avatar_url || '',
    };
  } catch {
    return null;
  }
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [prs, setPRs] = useState<PR[]>([]);
  const [activeTopic, setActiveTopic] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setPRsLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null);
  const [selectedPR, setSelectedPR] = useState<PR | null>(null);
  const [chatOpen, setChatOpen] = useState(true);
  const [activeQualityFilter, setActiveQualityFilter] = useState<'duplicates' | 'highQuality' | null>(null);
  const [activeRecommendation, setActiveRecommendation] = useState<string | null>(null);
  const [showRepoDropdown, setShowRepoDropdown] = useState(false);
  const [reposLoading, setReposLoading] = useState(true);
  const [repoSearch, setRepoSearch] = useState('');
  const [repoSearchLoading, setRepoSearchLoading] = useState(false);
  const [error, setError] = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [ingestionJob, setIngestionJob] = useState<IngestionJob | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      router.push('/');
      return;
    }
    const userInfo = getUserFromToken(token);
    setUser(userInfo);
    fetchRepos();
  }, [router]);

  useEffect(() => {
    if (selectedRepo) {
      setActiveQualityFilter(null);
      setActiveRecommendation(null);
      fetchPRs();
    }
  }, [selectedRepo, activeTopic]);

  const fetchRepos = async () => {
    setReposLoading(true);
    try {
      const data = await reposApi.list();
      setRepos(data.repos || []);
      if (data.repos?.length > 0 && !selectedRepo) {
        setSelectedRepo(data.repos[0].fullName);
      }
    } catch (err) {
      setError('Failed to load repositories');
    } finally {
      setReposLoading(false);
    }
  };

  const fetchPRs = async () => {
    if (!selectedRepo) return;
    setPRsLoading(true);
    setError('');
    try {
      const topic = activeTopic !== 'All' ? activeTopic : undefined;
      const data = await prsApi.list(selectedRepo, topic);
      setPRs(data.prs || []);
    } catch (err) {
      setError('Failed to load pull requests');
    } finally {
      setPRsLoading(false);
    }
  };

  const triggerAnalysis = async () => {
    if (!selectedRepo || analyzing) return;
    setAnalyzing(true);
    setError('');
    try {
      const job = await analyzeApi.trigger(selectedRepo);
      setAnalysisJob(job);
      // Poll for status
      const poll = setInterval(async () => {
        try {
          const status = await analyzeApi.getStatus(job.jobId);
          setAnalysisJob(status);
          if (status.status === 'completed' || status.status === 'error') {
            clearInterval(poll);
            setAnalyzing(false);
            if (status.status === 'completed') {
              fetchPRs();
            }
          }
        } catch {
          clearInterval(poll);
          setAnalyzing(false);
        }
      }, 2000);
    } catch (err) {
      setError('Failed to start analysis');
      setAnalyzing(false);
    }
  };

  const triggerIngestion = async () => {
    if (ingesting) return;
    setIngesting(true);
    setError('');
    try {
      const job = await criteriaApi.ingest(selectedRepo || undefined);
      setIngestionJob(job);
      const poll = setInterval(async () => {
        try {
          const status = await criteriaApi.getStatus(job.jobId);
          setIngestionJob(status);
          if (status.status === 'completed' || status.status === 'error') {
            clearInterval(poll);
            setIngesting(false);
          }
        } catch {
          clearInterval(poll);
          setIngesting(false);
        }
      }, 3000);
    } catch (err) {
      setError('Failed to start criteria ingestion');
      setIngesting(false);
    }
  };

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  const filteredPRs = useMemo(() => {
    let result = prs;
    if (activeRecommendation === 'changes_requested') {
      result = result.filter((pr) => pr.reviewStatus === 'changes_requested');
    } else if (activeRecommendation === 'approved') {
      result = result.filter((pr) => pr.reviewStatus === 'approved');
    } else {
      result = result.filter((pr) => pr.reviewStatus !== 'changes_requested' && pr.reviewStatus !== 'approved');
      if (activeQualityFilter === 'duplicates') {
        result = result.filter((pr) => pr.similarPRs?.length > 0);
      } else if (activeQualityFilter === 'highQuality') {
        result = result.filter((pr) => pr.score >= 80);
      }
      if (activeRecommendation) {
        result = result.filter((pr) => pr.recommendation === activeRecommendation);
      }
    }
    if (!searchQuery) return result;
    const q = searchQuery.toLowerCase();
    return result.filter(
      (pr) =>
        pr.title.toLowerCase().includes(q) ||
        pr.author.toLowerCase().includes(q) ||
        pr.topics.some((t) => t.toLowerCase().includes(q)) ||
        pr.description?.toLowerCase().includes(q)
    );
  }, [prs, searchQuery, activeQualityFilter, activeRecommendation]);

  const stats = useMemo(() => {
    return {
      total: prs.length,
      analyzed: prs.filter((p) => p.status === 'analyzed').length,
      duplicates: prs.filter((p) => p.similarPRs?.length > 0).length,
      topics: [...new Set(prs.flatMap((p) => p.topics))].length,
      highScore: prs.filter((p) => p.score >= 80).length,
    };
  }, [prs]);

  const handleRepoSearch = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== 'Enter' || !repoSearch.includes('/')) return;
    setRepoSearchLoading(true);
    try {
      const repo = await reposApi.search(repoSearch.trim());
      setRepos(prev => prev.find(r => r.fullName === repo.fullName) ? prev : [repo, ...prev]);
      setSelectedRepo(repo.fullName);
      setShowRepoDropdown(false);
      setRepoSearch('');
    } catch {
      setError(`Repo "${repoSearch}" not found`);
    } finally {
      setRepoSearchLoading(false);
    }
  };

  const handleLogout = () => {
    authApi.logout();
    router.push('/');
  };

  const visibleTopics = TOPICS.filter((t) => {
    if (t === 'All') return true;
    return prs.some((pr) => pr.topics.includes(t));
  });

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-white flex">
      {/* Left chat panel */}
      <ChatPanel
        selectedPR={selectedPR}
        repo={selectedRepo}
        isOpen={chatOpen}
        onToggle={() => setChatOpen(o => !o)}
      />

      {/* Main content — shifts right when panel is open */}
      <div className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${chatOpen ? 'mr-80' : 'mr-0'}`}>

      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-white/5 bg-[#0a0f1a]/80 backdrop-blur-xl">
        <div className="px-6 py-3 flex items-center gap-4">
          {/* Logo */}
          <div className="flex items-center gap-2 mr-4">
            <Image
              src="/logo.png"
              alt="PR Analyzer"
              width={32}
              height={32}
              className="rounded-lg"
            />
            <span className="font-semibold text-sm text-white hidden sm:block">PR Analyzer</span>
          </div>

          {/* Repo selector */}
          <div className="relative">
            <button
              onClick={() => setShowRepoDropdown(!showRepoDropdown)}
              className="flex items-center gap-2 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-slate-300 transition-all"
            >
              {reposLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-500" />
              ) : (
                <GitPullRequest className="w-3.5 h-3.5 text-slate-500" />
              )}
              <span className="max-w-[200px] truncate">{selectedRepo || 'Select repository'}</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-500 ml-1" />
            </button>

            {showRepoDropdown && (
              <div className="absolute top-full left-0 mt-1 w-72 bg-[#111827] border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50">
                <div className="p-2 border-b border-white/5">
                  <div className="flex items-center gap-2 px-2 py-1.5 bg-white/5 rounded-lg">
                    {repoSearchLoading ? (
                      <Loader2 className="w-3.5 h-3.5 text-slate-500 animate-spin flex-shrink-0" />
                    ) : (
                      <GitPullRequest className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                    )}
                    <input
                      autoFocus
                      type="text"
                      value={repoSearch}
                      onChange={(e) => setRepoSearch(e.target.value)}
                      onKeyDown={handleRepoSearch}
                      placeholder="owner/repo — press Enter"
                      className="flex-1 bg-transparent text-xs text-white placeholder-slate-600 outline-none"
                    />
                  </div>
                </div>
                {repos.length > 0 && (
                  <div className="p-1.5 max-h-52 overflow-y-auto">
                    {repos.map((repo) => (
                      <button
                        key={repo.id}
                        onClick={() => {
                          setSelectedRepo(repo.fullName);
                          setShowRepoDropdown(false);
                        }}
                        className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-all hover:bg-white/5 ${
                          selectedRepo === repo.fullName ? 'bg-purple-500/10' : ''
                        }`}
                      >
                        <GitPullRequest className="w-4 h-4 text-slate-500 mt-0.5 flex-shrink-0" />
                        <div className="min-w-0">
                          <div className="text-sm text-white font-medium truncate">{repo.fullName}</div>
                          {repo.description && (
                            <div className="text-xs text-slate-500 truncate">{repo.description}</div>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex-1" />

          {/* Ingest Criteria button */}
          <button
            onClick={triggerIngestion}
            disabled={ingesting}
            className="flex items-center gap-2 px-4 py-1.5 bg-teal-600 hover:bg-teal-500 disabled:bg-teal-600/30 disabled:text-teal-400 rounded-lg text-sm font-medium text-white transition-all"
          >
            {ingesting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Ingesting...</span>
              </>
            ) : (
              <>
                <BarChart3 className="w-3.5 h-3.5" />
                <span>Ingest Criteria</span>
              </>
            )}
          </button>

          {/* Analyze button */}
          <button
            onClick={triggerAnalysis}
            disabled={analyzing || !selectedRepo}
            className="flex items-center gap-2 px-4 py-1.5 bg-purple-600 hover:bg-purple-500 disabled:bg-purple-600/30 disabled:text-purple-400 rounded-lg text-sm font-medium text-white transition-all"
          >
            {analyzing ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Analyze Repo</span>
              </>
            )}
          </button>

          {/* Refresh */}
          <button
            onClick={fetchPRs}
            disabled={loading || !selectedRepo}
            className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 text-slate-400 hover:text-white transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {/* User */}
          {user && (
            <div className="flex items-center gap-2">
              {user.avatar_url ? (
                <Image
                  src={user.avatar_url}
                  alt={user.name}
                  width={28}
                  height={28}
                  className="rounded-full ring-1 ring-white/10"
                />
              ) : (
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center text-xs font-bold">
                  {user.name?.[0]?.toUpperCase()}
                </div>
              )}
              <button
                onClick={handleLogout}
                className="p-1.5 text-slate-500 hover:text-slate-300 transition-colors"
                title="Sign out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </header>

      <div className="max-w-screen-xl mx-auto px-6 py-6">
        {/* Analysis progress */}
        {analysisJob && analyzing && (
          <div className="mb-6 p-4 bg-purple-500/10 border border-purple-500/20 rounded-xl flex items-center gap-4">
            <Loader2 className="w-5 h-5 text-purple-400 animate-spin flex-shrink-0" />
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-purple-300">{analysisJob.message}</span>
                <span className="text-xs text-purple-400">{analysisJob.processed}/{analysisJob.total} PRs</span>
              </div>
              <div className="h-1.5 bg-purple-500/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-purple-500 rounded-full transition-all duration-500"
                  style={{ width: `${analysisJob.progress}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Ingestion progress */}
        {ingestionJob && ingesting && (
          <div className="mb-6 p-4 bg-teal-500/10 border border-teal-500/20 rounded-xl flex items-center gap-4">
            <Loader2 className="w-5 h-5 text-teal-400 animate-spin flex-shrink-0" />
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-teal-300">{ingestionJob.message}</span>
                <span className="text-xs text-teal-400">{ingestionJob.processed}/{ingestionJob.total} commits</span>
              </div>
              <div className="h-1.5 bg-teal-500/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-teal-500 rounded-full transition-all duration-500"
                  style={{ width: `${ingestionJob.progress}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Ingestion completed */}
        {ingestionJob && !ingesting && ingestionJob.status === 'completed' && (
          <div className="mb-6 p-4 bg-teal-500/10 border border-teal-500/20 rounded-xl flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-teal-400 flex-shrink-0" />
            <span className="text-sm text-teal-300">{ingestionJob.message}</span>
            <button
              onClick={() => setIngestionJob(null)}
              className="ml-auto text-teal-400/60 hover:text-teal-400"
            >
              ×
            </button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span className="text-sm">{error}</span>
            <button onClick={() => setError('')} className="ml-auto text-red-400/60 hover:text-red-400">
              ×
            </button>
          </div>
        )}

        {/* Stats bar */}
        {prs.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            {[
              { icon: GitPullRequest, label: 'Total PRs', value: stats.total, color: 'text-slate-400' },
              { icon: BarChart3, label: 'Topics Found', value: stats.topics, color: 'text-purple-400' },
              { icon: AlertTriangle, label: 'Duplicates', value: stats.duplicates, color: 'text-yellow-400', filter: 'duplicates' as const },
              { icon: CheckCircle2, label: 'High Quality', value: stats.highScore, color: 'text-emerald-400', filter: 'highQuality' as const },
            ].map((stat) => {
              const Icon = stat.icon;
              const isClickable = 'filter' in stat;
              const isActive = isClickable && activeQualityFilter === stat.filter;
              return (
                <div
                  key={stat.label}
                  onClick={() => isClickable && setActiveQualityFilter(isActive ? null : stat.filter!)}
                  className={`p-4 rounded-xl border transition-all ${
                    isClickable ? 'cursor-pointer' : ''
                  } ${
                    isActive
                      ? 'border-white/20 bg-white/[0.06]'
                      : 'border-white/5 bg-white/[0.02] hover:border-white/10'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className={`w-4 h-4 ${stat.color}`} />
                    <span className="text-xs text-slate-500">{stat.label}</span>
                    {isActive && <span className="ml-auto text-xs text-slate-500">× clear</span>}
                  </div>
                  <span className="text-2xl font-bold text-white">{stat.value}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Search + Topic filter */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="flex-1">
            <SearchBar onSearch={handleSearch} />
          </div>
        </div>

        {/* Recommendation filters */}
        {prs.some((p) => p.recommendation) && (
          <div className="flex gap-2 mb-4 overflow-x-auto pb-1 scrollbar-none">
            {([
              { key: null,               label: 'All',              color: 'text-slate-400',  bg: 'bg-slate-500/10',  field: null },
              { key: 'merge',            label: '✓ Merge',           color: 'text-emerald-400', bg: 'bg-emerald-500/10', field: 'recommendation' },
              { key: 'keep',             label: '◷ Keep',            color: 'text-blue-400',   bg: 'bg-blue-500/10',   field: 'recommendation' },
              { key: 'combine',          label: '⇄ Combine',         color: 'text-purple-400', bg: 'bg-purple-500/10', field: 'recommendation' },
              { key: 'discard',          label: '✕ Discard',         color: 'text-red-400',    bg: 'bg-red-500/10',    field: 'recommendation' },
              { key: 'changes_requested', label: '⚠ Changes Requested', color: 'text-orange-400', bg: 'bg-orange-500/10', field: 'reviewStatus' },
              { key: 'approved',          label: '✓ Approved',           color: 'text-teal-400',   bg: 'bg-teal-500/10',   field: 'reviewStatus' },
            ] as { key: string | null; label: string; color: string; bg: string; field: string | null }[]).map(({ key, label, color, bg, field }) => {
              const count = key === null
                ? prs.length
                : field === 'reviewStatus'
                  ? prs.filter((p) => p.reviewStatus === key).length
                  : prs.filter((p) => p.recommendation === key).length;
              if (key !== null && count === 0) return null;
              const isActive = activeRecommendation === key;
              return (
                <button
                  key={label}
                  onClick={() => setActiveRecommendation(key)}
                  className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                    isActive
                      ? `${bg} ${color} border-current/30`
                      : 'text-slate-500 border-transparent hover:text-slate-300 hover:border-white/10'
                  }`}
                >
                  {label}
                  <span className={`${isActive ? color : 'text-slate-600'}`}>({count})</span>
                </button>
              );
            })}
          </div>
        )}

        {/* Topic tabs */}
        {visibleTopics.length > 1 && (
          <div className="flex gap-2 mb-6 overflow-x-auto pb-1 scrollbar-none">
            {visibleTopics.map((topic) => (
              <button
                key={topic}
                onClick={() => setActiveTopic(topic)}
                className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-all
                  ${activeTopic === topic
                    ? 'bg-white/10 text-white border border-white/20'
                    : 'text-slate-500 hover:text-slate-300 border border-transparent hover:border-white/10'
                  }`}
              >
                {topic === 'All' ? (
                  <span className="flex items-center gap-1">
                    All <span className="text-slate-600">({prs.length})</span>
                  </span>
                ) : (
                  <TopicBadge topic={topic} size="sm" />
                )}
              </button>
            ))}
          </div>
        )}

        {/* PR List */}
        {!selectedRepo && !reposLoading ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
              <GitPullRequest className="w-8 h-8 text-slate-600" />
            </div>
            <h3 className="text-lg font-medium text-slate-400 mb-2">Select a repository</h3>
            <p className="text-sm text-slate-600 max-w-sm">
              Choose a GitHub repository from the dropdown above, then click "Analyze Repo" to get started.
            </p>
          </div>
        ) : (
          <PRList
            prs={filteredPRs}
            repo={selectedRepo}
            onPRClick={setSelectedPR}
            loading={loading}
          />
        )}
      </div>

      </div>
    </div>
  );
}
