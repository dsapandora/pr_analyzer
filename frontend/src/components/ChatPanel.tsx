'use client';

import { useState, useRef, useEffect } from 'react';
import {
  Send, Bot, User, Loader2, MessageSquare, ChevronRight,
  Sparkles, RotateCcw,
} from 'lucide-react';
import { PR, ChatMessage } from '@/lib/types';
import { chatApi } from '@/lib/api';
import { TopicBadge } from './TopicBadge';

interface ChatPanelProps {
  selectedPR: PR | null;
  repo: string;
  isOpen: boolean;
  onToggle: () => void;
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  return (
    <div className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center
        ${isUser ? 'bg-violet-500/20 border border-violet-500/30' : 'bg-blue-500/20 border border-blue-500/30'}`}>
        {isUser
          ? <User className="w-3 h-3 text-violet-400" />
          : <Bot className="w-3 h-3 text-blue-400" />}
      </div>
      <div className={`max-w-[85%] px-3 py-2 rounded-xl text-xs leading-relaxed
        ${isUser
          ? 'bg-violet-500/20 border border-violet-500/20 text-white rounded-tr-sm'
          : 'bg-white/[0.04] border border-white/10 text-slate-200 rounded-tl-sm'}`}>
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-2.5">
      <div className="flex-shrink-0 w-6 h-6 rounded-md bg-blue-500/20 border border-blue-500/30 flex items-center justify-center">
        <Bot className="w-3 h-3 text-blue-400" />
      </div>
      <div className="px-3 py-2 rounded-xl rounded-tl-sm bg-white/[0.04] border border-white/10">
        <div className="flex gap-1 items-center h-3.5">
          <span className="w-1 h-1 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-1 h-1 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-1 h-1 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}

const SUGGESTED: Record<string, string[]> = {
  default: [
    'Which PRs are duplicates?',
    'What PRs should I merge first?',
    'Summarize the vectordb changes',
    'Any risky PRs I should review carefully?',
  ],
  pr: [
    'What does this PR do?',
    'Is this safe to merge?',
    'What are the risks?',
    'Does this duplicate another PR?',
  ],
};

export function ChatPanel({ selectedPR, repo, isOpen, onToggle }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const prevPRRef = useRef<number | null>(null);

  // Reset chat when PR selection changes
  useEffect(() => {
    const currentId = selectedPR?.number ?? null;
    if (currentId === prevPRRef.current) return;
    prevPRRef.current = currentId;

    const welcome = selectedPR
      ? `Asking about PR #${selectedPR.number}: "${selectedPR.title}". Qdrant has the full context — ask anything.`
      : `Hi! I have context of all analyzed PRs in this repo. Ask me anything about them.`;

    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: welcome,
      timestamp: new Date().toISOString(),
    }]);
    setInput('');
  }, [selectedPR]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const history = messages
        .filter(m => m.id !== 'welcome')
        .map(m => ({ role: m.role, content: m.content }));

      const response = await chatApi.sendMessage(
        selectedPR?.number ?? 0,
        repo,
        content.trim(),
        history,
      );

      setMessages(prev => [...prev, {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: response.message,
        timestamp: new Date().toISOString(),
      }]);
    } catch {
      setMessages(prev => [...prev, {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const clearChat = () => {
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: selectedPR
        ? `Asking about PR #${selectedPR.number}. Ask anything.`
        : 'Hi! Ask me anything about the analyzed PRs.',
      timestamp: new Date().toISOString(),
    }]);
  };

  const suggestions = selectedPR ? SUGGESTED.pr : SUGGESTED.default;
  const showSuggestions = messages.length <= 1;

  return (
    <>
      {/* Collapsed tab — visible when closed */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className="fixed right-0 top-1/2 -translate-y-1/2 z-40 flex flex-col items-center gap-1.5
            px-1.5 py-4 bg-[#0d1424] border border-r-0 border-white/10 rounded-l-xl
            text-slate-400 hover:text-white transition-all group"
        >
          <MessageSquare className="w-4 h-4" />
          <span className="text-[10px] font-medium tracking-widest [writing-mode:vertical-rl] rotate-180">
            AI CHAT
          </span>
          <Sparkles className="w-3 h-3 text-violet-400" />
        </button>
      )}

      {/* Panel */}
      <aside className={`fixed right-0 inset-y-0 z-40 flex flex-col bg-[#0a0f1e] border-l border-white/10
        shadow-2xl transition-all duration-300 ease-in-out
        ${isOpen ? 'w-80 translate-x-0' : 'w-0 translate-x-full'}`}>

        {isOpen && (
          <>
            {/* Header */}
            <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-violet-500/20 border border-violet-500/30 flex items-center justify-center">
                  <Bot className="w-3.5 h-3.5 text-violet-400" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-white">AI Assistant</p>
                  {selectedPR && (
                    <p className="text-[10px] text-slate-500 truncate max-w-[160px]">
                      PR #{selectedPR.number}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={clearChat}
                  title="Clear chat"
                  className="w-6 h-6 rounded-md bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-500 hover:text-slate-300 transition-all"
                >
                  <RotateCcw className="w-3 h-3" />
                </button>
                <button
                  onClick={onToggle}
                  className="w-6 h-6 rounded-md bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-500 hover:text-slate-300 transition-all"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* PR context pill */}
            {selectedPR && (
              <div className="flex-shrink-0 px-3 py-2 border-b border-white/5 bg-white/[0.02]">
                <p className="text-[10px] text-slate-500 mb-1 uppercase tracking-wider">Focused on</p>
                <p className="text-xs text-white font-medium truncate mb-1.5">{selectedPR.title}</p>
                <div className="flex flex-wrap gap-1">
                  {selectedPR.topics.slice(0, 3).map(t => (
                    <TopicBadge key={t} topic={t} size="sm" />
                  ))}
                </div>
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
              {messages.map(m => <MessageBubble key={m.id} message={m} />)}
              {isLoading && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>

            {/* Suggested questions */}
            {showSuggestions && (
              <div className="flex-shrink-0 px-3 pb-2">
                <p className="text-[10px] text-slate-600 mb-1.5 uppercase tracking-wider">Suggestions</p>
                <div className="flex flex-col gap-1">
                  {suggestions.map(q => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      className="text-left px-2.5 py-1.5 text-[11px] text-slate-400 hover:text-white
                        bg-white/[0.03] hover:bg-white/[0.07] border border-white/5 hover:border-white/10
                        rounded-lg transition-all"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input */}
            <div className="flex-shrink-0 px-3 py-3 border-t border-white/10">
              <div className="flex gap-2 items-end">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={selectedPR ? `Ask about PR #${selectedPR.number}...` : 'Ask about your PRs...'}
                  rows={1}
                  disabled={isLoading}
                  className="flex-1 resize-none px-3 py-2 bg-white/5 border border-white/10 rounded-lg
                    text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1
                    focus:ring-violet-500/50 focus:border-violet-500/50 transition-all
                    disabled:opacity-50 max-h-24"
                  onInput={e => {
                    const t = e.target as HTMLTextAreaElement;
                    t.style.height = 'auto';
                    t.style.height = `${Math.min(t.scrollHeight, 96)}px`;
                  }}
                />
                <button
                  onClick={() => sendMessage(input)}
                  disabled={!input.trim() || isLoading}
                  className="flex-shrink-0 w-8 h-8 rounded-lg bg-violet-600 hover:bg-violet-500
                    disabled:bg-white/5 disabled:text-slate-600 flex items-center justify-center
                    text-white transition-all"
                >
                  {isLoading
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : <Send className="w-3.5 h-3.5" />}
                </button>
              </div>
              <p className="text-[9px] text-slate-700 mt-1.5 text-center">
                Enter · Shift+Enter new line
              </p>
            </div>
          </>
        )}
      </aside>
    </>
  );
}
