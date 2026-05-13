export interface PR {
  id: number;
  number: number;
  title: string;
  description: string;
  author: string;
  authorAvatar: string;
  url: string;
  topics: string[];
  score: number;
  recommendation: 'merge' | 'keep' | 'discard' | 'combine';
  similarPRs: number[];
  filesChanged: string[];
  additions: number;
  deletions: number;
  status: 'analyzed' | 'pending' | 'error';
  reviewStatus?: 'changes_requested' | 'approved' | 'commented' | null;
  reviewers?: Array<{ login: string; state: string; avatar: string }>;
  createdAt: string;
  summary?: string;
  reasoning?: string;
  repo?: string;
  isPrimary?: boolean;
}

export interface RelatedPR extends PR {
  isPrimary: boolean;
}

export interface ViabilityAssessment {
  viability_score: number;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  overall_assessment: string;
}

export interface CommentAnalysis {
  author: string;
  body: string;
  status: 'applied' | 'not_applied' | 'partial';
  explanation: string;
}

export interface TicketEvaluation {
  ticket_makes_sense: boolean;
  implementation_matches_ticket: boolean;
  is_redundant: boolean;
  is_counterproductive: boolean;
  risk_level: string;
  risk_reasons: string[];
  ticket_assessment: string;
  implementation_assessment: string;
  needs_human_review: boolean;
  human_review_reason: string;
}

export interface GeneratedReview {
  body: string;
  event: 'APPROVE' | 'REQUEST_CHANGES' | 'COMMENT';
  viability: ViabilityAssessment;
  comment_analysis: CommentAnalysis[];
  ticket_eval?: TicketEvaluation | null;
  risk_level: string;
  needs_human_review: boolean;
  human_review_reason: string;
}

export interface ReviewSubmission {
  github_review_id: number;
  pr_number: number;
  event: string;
  submitted_at: string;
}

export interface IngestionJob {
  jobId: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  total: number;
  processed: number;
  message: string;
}

export interface AnalysisResult {
  topics: Record<string, PR[]>;
  duplicateGroups: number[][];
  stats: {
    total: number;
    analyzed: number;
    duplicates: number;
    recommended: { merge: number; keep: number; discard: number; combine: number };
  };
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatSession {
  prNumber: number;
  messages: ChatMessage[];
}

export interface Repository {
  id: number;
  name: string;
  fullName: string;
  description: string;
  private: boolean;
  language: string;
  stargazersCount: number;
  openPRsCount: number;
}

export interface User {
  login: string;
  name: string;
  avatarUrl: string;
  email: string;
}

export interface AnalysisJob {
  jobId: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  total: number;
  processed: number;
  message: string;
  startedAt: string;
  completedAt?: string;
}

export type TopicColor = {
  bg: string;
  text: string;
  border: string;
};

export const TOPIC_COLORS: Record<string, TopicColor> = {
  vectordb: { bg: 'bg-purple-500/20', text: 'text-purple-300', border: 'border-purple-500/30' },
  engine: { bg: 'bg-blue-500/20', text: 'text-blue-300', border: 'border-blue-500/30' },
  llms: { bg: 'bg-emerald-500/20', text: 'text-emerald-300', border: 'border-emerald-500/30' },
  integrations: { bg: 'bg-orange-500/20', text: 'text-orange-300', border: 'border-orange-500/30' },
  ui: { bg: 'bg-pink-500/20', text: 'text-pink-300', border: 'border-pink-500/30' },
  bugfix: { bg: 'bg-red-500/20', text: 'text-red-300', border: 'border-red-500/30' },
  docs: { bg: 'bg-yellow-500/20', text: 'text-yellow-300', border: 'border-yellow-500/30' },
  testing: { bg: 'bg-cyan-500/20', text: 'text-cyan-300', border: 'border-cyan-500/30' },
  devops: { bg: 'bg-indigo-500/20', text: 'text-indigo-300', border: 'border-indigo-500/30' },
  other: { bg: 'bg-slate-500/20', text: 'text-slate-300', border: 'border-slate-500/30' },
};

export const RECOMMENDATION_CONFIG = {
  merge: { label: 'Merge', color: 'text-emerald-400', bg: 'bg-emerald-500/20', border: 'border-emerald-500/30' },
  keep: { label: 'Keep', color: 'text-blue-400', bg: 'bg-blue-500/20', border: 'border-blue-500/30' },
  discard: { label: 'Discard', color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30' },
  combine: { label: 'Combine', color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30' },
};
