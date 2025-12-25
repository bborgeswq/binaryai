import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Brain, TrendingUp, Clock, Activity, AlertCircle, CheckCircle2 } from 'lucide-react'
import { api } from '../services/api'
import clsx from 'clsx'

interface StrategyStatus {
  active: boolean;
  symbols: string[];
  risk_per_trade: number;
  min_rr: number;
  active_setups: Record<string, any>;
  liquidity_zones: Record<string, number>;
  order_blocks: Record<string, number>;
}

export default function Strategy() {
  const [status, setStatus] = useState<StrategyStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await fetch('http://localhost:8000/api/strategy/status').then(r => r.json());
        setStatus(data.status);
        setLoading(false);
      } catch (err: any) {
        setError('Could not connect to trading server');
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Activity className="w-6 h-6 text-accent animate-spin" />
        <span className="ml-3 text-ink-secondary">Loading strategy status...</span>
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
        <h1 className="text-2xl font-bold text-ink">Strategy Lab</h1>
        <p className="text-ink-secondary text-sm mt-1">TJR Liquidity Sweep Strategy - Real-time status</p>
      </div>

      {/* Strategy Overview */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-5 h-5 text-accent" />
            <span className="text-sm text-ink-secondary">Strategy</span>
          </div>
          <p className="text-lg font-semibold text-ink">TJR Liquidity Sweep</p>
          <p className="text-xs text-ink-faint mt-1">Smart Money Concepts</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-5 h-5 text-profit" />
            <span className="text-sm text-ink-secondary">Risk/Trade</span>
          </div>
          <p className="text-lg font-semibold text-ink">{((status?.risk_per_trade || 0.07) * 100).toFixed(0)}%</p>
          <p className="text-xs text-ink-faint mt-1">of account balance</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-5 h-5 text-warning" />
            <span className="text-sm text-ink-secondary">Min R:R</span>
          </div>
          <p className="text-lg font-semibold text-ink">{status?.min_rr || 2}:1</p>
          <p className="text-xs text-ink-faint mt-1">Risk to Reward</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-5 h-5 text-ink-tertiary" />
            <span className="text-sm text-ink-secondary">Analysis</span>
          </div>
          <p className="text-lg font-semibold text-ink">Every 60s</p>
          <p className="text-xs text-ink-faint mt-1">Continuous scanning</p>
        </div>
      </div>

      {/* Symbols Being Tracked */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">Tracked Symbols</h2>
        <div className="grid grid-cols-3 gap-4">
          {(status?.symbols || ['BTC/USDT', 'ETH/USDT', 'XRP/USDT']).map((symbol) => (
            <div key={symbol} className="p-4 bg-surface rounded-lg">
              <div className="flex items-center justify-between">
                <span className="font-medium text-ink">{symbol}</span>
                <CheckCircle2 className="w-4 h-4 text-profit" />
              </div>
              <div className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-ink-secondary">Liquidity Zones</span>
                  <span className="text-ink font-mono">{status?.liquidity_zones?.[symbol] || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-secondary">Order Blocks</span>
                  <span className="text-ink font-mono">{status?.order_blocks?.[symbol] || 0}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Active Setups */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">Active Trade Setups</h2>
        {Object.keys(status?.active_setups || {}).length === 0 ? (
          <div className="text-center py-8">
            <Activity className="w-8 h-8 text-ink-faint mx-auto mb-3" />
            <p className="text-ink-secondary">No active setups</p>
            <p className="text-ink-faint text-sm mt-1">The strategy is scanning for valid entry conditions</p>
          </div>
        ) : (
          <div className="space-y-3">
            {Object.entries(status?.active_setups || {}).map(([symbol, setup]: [string, any]) => (
              <div key={symbol} className="p-4 bg-surface rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
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
                <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
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

      {/* Strategy Explanation */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">How TJR Strategy Works</h2>
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-accent-muted flex items-center justify-center text-accent font-semibold text-sm">1</div>
              <div>
                <p className="font-medium text-ink">Multi-Timeframe Analysis</p>
                <p className="text-sm text-ink-secondary">Analyzes 4H, 1H, 15m, and 5m charts for confluence</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-accent-muted flex items-center justify-center text-accent font-semibold text-sm">2</div>
              <div>
                <p className="font-medium text-ink">Find Liquidity Zones</p>
                <p className="text-sm text-ink-secondary">Identifies swing highs/lows where stop losses cluster</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-accent-muted flex items-center justify-center text-accent font-semibold text-sm">3</div>
              <div>
                <p className="font-medium text-ink">Wait for Sweep</p>
                <p className="text-sm text-ink-secondary">Price takes out liquidity then reverses - the sweep</p>
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-accent-muted flex items-center justify-center text-accent font-semibold text-sm">4</div>
              <div>
                <p className="font-medium text-ink">Confirm Break of Structure</p>
                <p className="text-sm text-ink-secondary">Validates reversal with structure break on lower timeframe</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-accent-muted flex items-center justify-center text-accent font-semibold text-sm">5</div>
              <div>
                <p className="font-medium text-ink">Enter at Order Block/FVG</p>
                <p className="text-sm text-ink-secondary">Waits for retracement to premium entry zone</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-accent-muted flex items-center justify-center text-accent font-semibold text-sm">6</div>
              <div>
                <p className="font-medium text-ink">Execute with Risk Management</p>
                <p className="text-sm text-ink-secondary">7% risk, SL below sweep, TP at opposite liquidity</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
