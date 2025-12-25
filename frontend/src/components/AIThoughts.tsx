import { useState, useEffect } from 'react';
import { Brain, Zap, TrendingUp, TrendingDown, AlertCircle, Activity, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../services/api';
import clsx from 'clsx';

interface Thought {
  time: string;
  symbol: string;
  thought: string;
  type: string;
}

interface AIState {
  status: string;
  thinking: string;
  analyzing_symbol: string | null;
  last_signal: {
    symbol: string;
    signal: string;
    confidence: number;
    price: number;
  } | null;
  confidence: number;
}

export default function AIThoughts() {
  const [thoughts, setThoughts] = useState<Thought[]>([]);
  const [state, setState] = useState<AIState | null>(null);
  const [expanded, setExpanded] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchState = async () => {
      try {
        const data = await fetch('http://localhost:8000/api/ai/state').then(r => r.json());
        setState(data.state);
        setThoughts(data.thoughts || []);
        setLoading(false);
      } catch (err) {
        console.error('Failed to fetch AI state:', err);
        setLoading(false);
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 2000); // Update every 2 seconds
    return () => clearInterval(interval);
  }, []);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'thinking': return <Brain className="w-3 h-3" />;
      case 'analyzing': return <Activity className="w-3 h-3" />;
      case 'signal_generated': return <Zap className="w-3 h-3" />;
      case 'pattern_detected': return <TrendingUp className="w-3 h-3" />;
      default: return <Brain className="w-3 h-3" />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'thinking': return 'text-purple-400 bg-purple-500/10';
      case 'analyzing': return 'text-blue-400 bg-blue-500/10';
      case 'signal_generated': return 'text-accent bg-accent-muted';
      case 'pattern_detected': return 'text-yellow-400 bg-yellow-500/10';
      default: return 'text-ink-secondary bg-surface';
    }
  };

  if (loading) {
    return (
      <div className="card p-4">
        <div className="flex items-center gap-2 text-ink-secondary">
          <Brain className="w-4 h-4 animate-pulse" />
          <span className="text-sm">Connecting to AI...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between border-b border-surface-border hover:bg-surface-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={clsx(
            'p-1.5 rounded-lg',
            state?.status === 'analyzing' ? 'bg-accent-muted' : 'bg-surface'
          )}>
            <Brain className={clsx(
              'w-4 h-4',
              state?.status === 'analyzing' ? 'text-accent animate-pulse' : 'text-ink-tertiary'
            )} />
          </div>
          <span className="font-medium text-ink text-sm">AI Thought Process</span>
          {state?.status === 'analyzing' && (
            <span className="text-xs text-accent ml-2">Analyzing {state.analyzing_symbol}...</span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-ink-tertiary" />
        ) : (
          <ChevronDown className="w-4 h-4 text-ink-tertiary" />
        )}
      </button>

      {expanded && (
        <>
          {/* Current Thinking */}
          {state?.thinking && (
            <div className="px-4 py-3 bg-surface/50 border-b border-surface-border">
              <div className="flex items-start gap-2">
                <Brain className="w-4 h-4 text-accent mt-0.5 flex-shrink-0" />
                <p className="text-sm text-ink">{state.thinking}</p>
              </div>
            </div>
          )}

          {/* Last Signal */}
          {state?.last_signal && (
            <div className="px-4 py-3 border-b border-surface-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {state.last_signal.signal === 'BUY' ? (
                    <TrendingUp className="w-4 h-4 text-profit" />
                  ) : state.last_signal.signal === 'SELL' ? (
                    <TrendingDown className="w-4 h-4 text-loss" />
                  ) : (
                    <Activity className="w-4 h-4 text-warning" />
                  )}
                  <span className="text-sm font-medium text-ink">
                    {state.last_signal.signal} {state.last_signal.symbol}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-sm font-mono text-ink">
                    ${state.last_signal.price?.toLocaleString()}
                  </span>
                  <span className="text-xs text-ink-faint ml-2">
                    {(state.last_signal.confidence * 100).toFixed(0)}% conf
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Thought Stream */}
          <div className="max-h-[200px] overflow-y-auto">
            {thoughts.length === 0 ? (
              <div className="p-6 text-center">
                <Brain className="w-6 h-6 text-ink-faint mx-auto mb-2" />
                <p className="text-sm text-ink-secondary">No thoughts yet</p>
                <p className="text-xs text-ink-faint mt-1">Start the agent to see AI analysis</p>
              </div>
            ) : (
              <div className="divide-y divide-surface-border">
                {thoughts.map((thought, idx) => (
                  <div key={idx} className="px-4 py-2 hover:bg-surface-hover transition-colors">
                    <div className="flex items-start gap-2">
                      <span className={clsx(
                        'p-1 rounded flex-shrink-0 mt-0.5',
                        getTypeColor(thought.type)
                      )}>
                        {getTypeIcon(thought.type)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-xs font-mono text-ink-faint">{thought.time}</span>
                          {thought.symbol !== 'SYSTEM' && (
                            <span className="text-xs font-medium text-ink-secondary">{thought.symbol}</span>
                          )}
                        </div>
                        <p className="text-xs text-ink leading-relaxed">{thought.thought}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
