import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Brain, Activity, TrendingUp, TrendingDown, AlertCircle, Zap, Eye, Clock } from 'lucide-react'
import clsx from 'clsx'

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

interface Thought {
  time: string;
  symbol: string;
  thought: string;
  type: string;
}

interface StrategyStatus {
  active: boolean;
  symbols: string[];
  risk_per_trade: number;
  min_rr: number;
  active_setups: Record<string, any>;
  liquidity_zones: Record<string, number>;
  order_blocks: Record<string, number>;
}

export default function Models() {
  const [aiState, setAiState] = useState<AIState | null>(null);
  const [thoughts, setThoughts] = useState<Thought[]>([]);
  const [strategy, setStrategy] = useState<StrategyStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [aiResponse, strategyResponse] = await Promise.all([
          fetch('http://localhost:8000/api/ai/state'),
          fetch('http://localhost:8000/api/strategy/status')
        ]);

        const aiData = await aiResponse.json();
        const strategyData = await strategyResponse.json();

        setAiState(aiData.state);
        setThoughts(aiData.thoughts || []);
        setStrategy(strategyData.status);
        setLoading(false);
      } catch (err) {
        setError('Could not connect to trading server');
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

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
      <div className="flex items-center justify-center h-64">
        <Activity className="w-6 h-6 text-accent animate-spin" />
        <span className="ml-3 text-ink-secondary">Loading AI status...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <AlertCircle className="w-10 h-10 text-loss mb-4" />
        <p className="text-ink-secondary">{error}</p>
        <p className="text-ink-faint text-sm mt-2">Make sure the API server is running on port 8000</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-ink">AI Strategy Engine</h1>
        <p className="text-ink-secondary text-sm mt-1">TJR Liquidity Sweep - Real-time AI Analysis</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Strategy Info */}
        <div className="space-y-4">
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-accent-muted rounded-lg">
                <Brain className="w-5 h-5 text-accent" />
              </div>
              <div>
                <h3 className="font-semibold text-ink">Active Strategy</h3>
                <p className="text-xs text-ink-tertiary">Smart Money Concepts</p>
              </div>
            </div>
            <p className="text-lg font-bold text-ink mb-2">TJR Liquidity Sweep</p>
            <p className="text-sm text-ink-secondary">
              Multi-timeframe analysis looking for liquidity sweeps, break of structure, and order block entries.
            </p>
          </div>

          {/* Strategy Parameters */}
          <div className="card p-6">
            <h3 className="font-semibold text-ink mb-4">Strategy Parameters</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-ink-secondary">Risk Per Trade</span>
                <span className="font-mono text-ink">{((strategy?.risk_per_trade || 0.07) * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-ink-secondary">Minimum R:R</span>
                <span className="font-mono text-ink">{strategy?.min_rr || 2}:1</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-ink-secondary">Timeframes</span>
                <span className="font-mono text-ink">4H, 1H, 15m, 5m</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-ink-secondary">Analysis Interval</span>
                <span className="font-mono text-ink">60 seconds</span>
              </div>
            </div>
          </div>

          {/* Tracked Symbols */}
          <div className="card p-6">
            <h3 className="font-semibold text-ink mb-4">Tracked Symbols</h3>
            <div className="space-y-2">
              {(strategy?.symbols || ['BTC/USDT', 'ETH/USDT', 'XRP/USDT']).map((symbol) => (
                <div key={symbol} className="flex justify-between items-center p-2 bg-surface rounded-lg">
                  <span className="font-medium text-ink">{symbol}</span>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-ink-faint">LZ: {strategy?.liquidity_zones?.[symbol] || 0}</span>
                    <span className="text-ink-faint">OB: {strategy?.order_blocks?.[symbol] || 0}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* AI State Panel */}
        <div className="col-span-2 space-y-6">
          {/* Current AI Status */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className={clsx(
                  'p-2 rounded-lg',
                  aiState?.status === 'analyzing' ? 'bg-accent-muted' : 'bg-surface'
                )}>
                  <Brain className={clsx(
                    'w-5 h-5',
                    aiState?.status === 'analyzing' ? 'text-accent animate-pulse' : 'text-ink-tertiary'
                  )} />
                </div>
                <div>
                  <h3 className="font-semibold text-ink">AI Status</h3>
                  <p className="text-xs text-ink-tertiary">
                    {aiState?.status === 'analyzing'
                      ? `Analyzing ${aiState.analyzing_symbol}...`
                      : aiState?.status === 'idle'
                        ? 'Waiting for next analysis cycle'
                        : 'Monitoring markets'}
                  </p>
                </div>
              </div>
              {aiState?.last_signal && (
                <div className="text-right">
                  <div className="flex items-center gap-2">
                    <span className={clsx(
                      'text-xl font-bold',
                      aiState.last_signal.signal === 'BUY' ? 'text-profit' :
                      aiState.last_signal.signal === 'SELL' ? 'text-loss' : 'text-warning'
                    )}>
                      {aiState.last_signal.signal}
                    </span>
                    {aiState.last_signal.signal === 'BUY' ? (
                      <TrendingUp className="w-5 h-5 text-profit" />
                    ) : aiState.last_signal.signal === 'SELL' ? (
                      <TrendingDown className="w-5 h-5 text-loss" />
                    ) : null}
                  </div>
                  <p className="text-sm text-ink-secondary">
                    {aiState.last_signal.symbol} @ ${aiState.last_signal.price?.toLocaleString()}
                  </p>
                  <p className="text-xs text-ink-faint">
                    {(aiState.last_signal.confidence * 100).toFixed(0)}% confidence
                  </p>
                </div>
              )}
            </div>

            {/* Current Thinking */}
            {aiState?.thinking && (
              <div className="p-4 bg-surface/50 rounded-lg mb-4">
                <div className="flex items-start gap-2">
                  <Brain className="w-4 h-4 text-accent mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-ink">{aiState.thinking}</p>
                </div>
              </div>
            )}

            {/* Confidence Meter */}
            {aiState?.confidence > 0 && (
              <div>
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="text-ink-secondary">Analysis Confidence</span>
                  <span className="font-mono text-ink">{(aiState.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="h-2 bg-surface-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-accent to-teal-400 rounded-full transition-all duration-500"
                    style={{ width: `${aiState.confidence * 100}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Active Setups */}
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Zap className="w-5 h-5 text-warning" />
              <h3 className="font-semibold text-ink">Active Trade Setups</h3>
            </div>
            {Object.keys(strategy?.active_setups || {}).length === 0 ? (
              <div className="text-center py-6">
                <Eye className="w-8 h-8 text-ink-faint mx-auto mb-2" />
                <p className="text-ink-secondary">No active setups detected</p>
                <p className="text-xs text-ink-faint mt-1">AI is scanning for valid entry conditions</p>
              </div>
            ) : (
              <div className="space-y-3">
                {Object.entries(strategy?.active_setups || {}).map(([symbol, setup]: [string, any]) => (
                  <div key={symbol} className="p-4 bg-surface rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className={clsx(
                          'px-2 py-1 rounded text-xs font-medium',
                          setup.signal === 'BUY' ? 'bg-profit-muted text-profit' : 'bg-loss-muted text-loss'
                        )}>
                          {setup.signal}
                        </span>
                        <span className="font-medium text-ink">{symbol}</span>
                      </div>
                      <span className="text-sm text-ink-secondary">R:R {setup.rr?.toFixed(1) || '-'}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-ink-faint">Entry</span>
                        <p className="font-mono text-ink">${setup.entry?.toLocaleString()}</p>
                      </div>
                      <div>
                        <span className="text-ink-faint">Stop Loss</span>
                        <p className="font-mono text-loss">${setup.stop_loss?.toLocaleString()}</p>
                      </div>
                      <div>
                        <span className="text-ink-faint">Take Profit</span>
                        <p className="font-mono text-profit">${setup.take_profit?.toLocaleString()}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent AI Thoughts */}
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-5 h-5 text-ink-tertiary" />
              <h3 className="font-semibold text-ink">Recent AI Analysis</h3>
            </div>
            {thoughts.length === 0 ? (
              <div className="text-center py-6">
                <Brain className="w-8 h-8 text-ink-faint mx-auto mb-2" />
                <p className="text-ink-secondary">No analysis history yet</p>
                <p className="text-xs text-ink-faint mt-1">Start the trading agent to see AI thoughts</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {thoughts.slice(0, 15).map((thought, idx) => (
                  <div key={idx} className="p-3 bg-surface rounded-lg">
                    <div className="flex items-start gap-2">
                      <span className={clsx(
                        'px-2 py-0.5 rounded text-xs',
                        getTypeColor(thought.type)
                      )}>
                        {thought.type}
                      </span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-ink-faint">{thought.time}</span>
                          {thought.symbol !== 'SYSTEM' && (
                            <span className="text-xs font-medium text-ink-secondary">{thought.symbol}</span>
                          )}
                        </div>
                        <p className="text-sm text-ink">{thought.thought}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
