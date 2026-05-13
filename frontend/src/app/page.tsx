'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authApi } from '@/lib/api';
import {
  GitPullRequest,
  Sparkles,
  Search,
  GitMerge,
  MessageSquare,
  ArrowRight,
  Star,
  Zap,
  Shield,
} from 'lucide-react';

const FEATURES = [
  {
    icon: Sparkles,
    title: 'AI Topic Clustering',
    description: 'Automatically group PRs by domain: VectorDB, Engine, LLMs, Integrations, and more.',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/20',
  },
  {
    icon: Search,
    title: 'Duplicate Detection',
    description: 'Find semantically similar PRs using vector embeddings. Never review the same work twice.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20',
  },
  {
    icon: Star,
    title: 'Smart Scoring',
    description: 'Each PR gets a quality score (0-100) with actionable recommendations: Merge, Keep, Discard, or Combine.',
    color: 'text-yellow-400',
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/20',
  },
  {
    icon: MessageSquare,
    title: 'Chat With PRs',
    description: 'Ask questions about any PR in natural language. AI answers with full code context.',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/20',
  },
  {
    icon: Zap,
    title: 'Fast Pipeline',
    description: 'Powered by Rocketride. Analyze hundreds of PRs in minutes with parallel processing.',
    color: 'text-orange-400',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/20',
  },
  {
    icon: Shield,
    title: 'Secure Auth',
    description: 'GitHub OAuth ensures only you can access your repositories. No data stored beyond analysis.',
    color: 'text-pink-400',
    bg: 'bg-pink-500/10',
    border: 'border-pink-500/20',
  },
];

export default function HomePage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Check if user is already authenticated
    const token = localStorage.getItem('auth_token');
    if (token) {
      router.push('/dashboard');
    }

    // Handle OAuth callback - token passed as URL param
    const params = new URLSearchParams(window.location.search);
    const authToken = params.get('token');
    if (authToken) {
      localStorage.setItem('auth_token', authToken);
      router.push('/dashboard');
    }
  }, [router]);

  const handleGitHubLogin = () => {
    setIsLoading(true);
    window.location.href = authApi.getLoginUrl();
  };

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-white overflow-hidden">
      {/* Animated background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl" />
        {/* Grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)`,
            backgroundSize: '50px 50px',
          }}
        />
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-white/5 bg-white/[0.02] backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg flex items-center justify-center">
              <GitPullRequest className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-white">PR Analyzer</span>
          </div>
          <button
            onClick={handleGitHubLogin}
            disabled={isLoading}
            className="text-sm text-slate-400 hover:text-white transition-colors"
          >
            Sign in
          </button>
        </div>
      </header>

      {/* Hero */}
      <main className="relative z-10">
        <div className="max-w-7xl mx-auto px-6 pt-24 pb-16 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-purple-500/10 border border-purple-500/20 rounded-full text-purple-300 text-xs font-medium mb-8">
            <Sparkles className="w-3 h-3" />
            Powered by Rocketride
          </div>

          {/* Headline */}
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight tracking-tight">
            <span className="text-white">Analyze PRs</span>
            <br />
            <span className="bg-gradient-to-r from-purple-400 via-blue-400 to-emerald-400 bg-clip-text text-transparent">
              at the speed of AI
            </span>
          </h1>

          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-12 leading-relaxed">
            Stop drowning in pull requests. PR Analyzer uses AI to automatically cluster, score,
            and surface insights from your GitHub PRs — so you can focus on what matters.
          </p>

          {/* CTA */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-20">
            <button
              onClick={handleGitHubLogin}
              disabled={isLoading}
              className="group flex items-center gap-3 px-8 py-4 bg-white text-slate-900 rounded-xl font-semibold text-base hover:bg-slate-100 transition-all duration-200 shadow-lg shadow-white/10 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                </svg>
              )}
              {isLoading ? 'Connecting...' : 'Sign in with GitHub'}
              {!isLoading && <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />}
            </button>
            <span className="text-slate-500 text-sm">Free to use • No credit card required</span>
          </div>

          {/* Stats */}
          <div className="flex items-center justify-center gap-12 mb-20 text-center">
            {[
              { value: '10x', label: 'Faster Review' },
              { value: '95%', label: 'Duplicate Detection' },
              { value: '0ms', label: 'Setup Time' },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-3xl font-bold text-white mb-1">{stat.value}</div>
                <div className="text-sm text-slate-500">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Preview mockup */}
          <div className="relative max-w-4xl mx-auto mb-24">
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#0a0f1a] z-10 pointer-events-none" />
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-sm overflow-hidden shadow-2xl">
              {/* Fake browser bar */}
              <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5 bg-white/[0.02]">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/50" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                  <div className="w-3 h-3 rounded-full bg-green-500/50" />
                </div>
                <div className="flex-1 mx-4 h-6 bg-white/5 rounded-md flex items-center px-3">
                  <span className="text-xs text-slate-500">pr-analyzer.app/dashboard</span>
                </div>
              </div>
              {/* Fake dashboard content */}
              <div className="p-6 text-left">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex gap-2">
                    {['All', 'VectorDB', 'Engine', 'LLMs', 'Integrations'].map((tab, i) => (
                      <div
                        key={tab}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
                          i === 0
                            ? 'bg-white/10 text-white'
                            : 'text-slate-500'
                        }`}
                      >
                        {tab}
                      </div>
                    ))}
                  </div>
                  <div className="h-8 w-32 bg-purple-500/20 rounded-lg border border-purple-500/30" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { title: 'Add Qdrant vector store support', score: 87, tag: 'vectordb', rec: 'Merge' },
                    { title: 'Fix embedding dimension mismatch', score: 72, tag: 'bugfix', rec: 'Keep' },
                    { title: 'Integrate OpenAI GPT-4o', score: 91, tag: 'llms', rec: 'Merge' },
                    { title: 'Add Pinecone fallback store', score: 45, tag: 'vectordb', rec: 'Combine' },
                  ].map((pr) => (
                    <div key={pr.title} className="p-3 rounded-xl border border-white/5 bg-white/[0.02]">
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-xs text-slate-300 font-medium leading-snug flex-1">{pr.title}</span>
                        <span className={`ml-2 text-xs font-bold ${pr.score >= 80 ? 'text-emerald-400' : pr.score >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {pr.score}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-300 text-[10px] rounded border border-purple-500/20">
                          {pr.tag}
                        </span>
                        <span className="px-1.5 py-0.5 bg-emerald-500/20 text-emerald-300 text-[10px] rounded border border-emerald-500/20">
                          {pr.rec}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Features */}
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">Everything you need to manage PRs</h2>
            <p className="text-slate-400">Built for teams that move fast and care about code quality.</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-5xl mx-auto">
            {FEATURES.map((feature) => {
              const Icon = feature.icon;
              return (
                <div
                  key={feature.title}
                  className={`p-6 rounded-2xl border ${feature.border} ${feature.bg} text-left transition-all duration-200 hover:scale-[1.02]`}
                >
                  <div className={`w-10 h-10 rounded-xl ${feature.bg} border ${feature.border} flex items-center justify-center mb-4`}>
                    <Icon className={`w-5 h-5 ${feature.color}`} />
                  </div>
                  <h3 className="font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/5 py-8 mt-16">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <GitPullRequest className="w-4 h-4" />
            <span>PR Analyzer</span>
          </div>
          <span>Built with Rocketride + Claude AI</span>
        </div>
      </footer>
    </div>
  );
}
