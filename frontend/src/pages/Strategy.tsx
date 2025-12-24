import { useState } from 'react'
import { motion } from 'framer-motion'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts'
import { Plus, Play, Pause, GitCompare, TrendingUp, TrendingDown, Activity, Calendar, Clock, ArrowRight } from 'lucide-react'
import { backtestRuns } from '../data/mockData'
import { useApp } from '../App'
import clsx from 'clsx'

// Mock backtest equity curve
const backtestEquity = Array.from({ length: 60 }, (_, i) => ({
  day: i + 1,
  portfolio: 10000 + (Math.random() * 500 - 100) * i * 0.5 + i * 50,
  benchmark: 10000 + i * 35,
}));

// Mock trade distribution
const tradeDistribution = [
  { range: '-10%+', count: 3, color: '#ef4444' },
  { range: '-5 to -10%', count: 8, color: '#f87171' },
  { range: '-1 to -5%', count: 15, color: '#fca5a5' },
  { range: '0 to -1%', count: 12, color: '#71717a' },
  { range: '0 to 1%', count: 18, color: '#86efac' },
  { range: '1 to 5%', count: 35, color: '#4ade80' },
  { range: '5 to 10%', count: 28, color: '#22c55e' },
  { range: '10%+', count: 26, color: '#16a34a' },
];

export default function Strategy() {
  const { addToast } = useApp();
  const [selectedRun, setSelectedRun] = useState(backtestRuns[0]);
  const [showNewBacktest, setShowNewBacktest] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Strategy Lab</h1>
          <p className="text-ink-secondary text-sm mt-1">Backtest and analyze trading strategies</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-secondary">
            <GitCompare className="w-4 h-4" />
            Compare Runs
          </button>
          <button
            onClick={() => setShowNewBacktest(true)}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" />
            New Backtest
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6">
        {/* Backtest Runs List */}
        <div className="card">
          <div className="px-4 py-3 border-b border-surface-border">
            <h3 className="font-medium text-ink text-sm">Backtest Runs</h3>
          </div>
          <div className="divide-y divide-surface-border">
            {backtestRuns.map((run) => (
              <button
                key={run.id}
                onClick={() => setSelectedRun(run)}
                className={clsx(
                  'w-full px-4 py-4 text-left transition-colors',
                  selectedRun.id === run.id ? 'bg-accent-muted' : 'hover:bg-surface-hover'
                )}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-ink text-sm">{run.name}</p>
                    <p className="text-xs text-ink-tertiary mt-1">{run.strategy}</p>
                  </div>
                  {run.status === 'running' ? (
                    <span className="badge-warning">
                      <Activity className="w-3 h-3 animate-pulse" />
                      Running
                    </span>
                  ) : run.status === 'completed' ? (
                    <span className={run.returns >= 0 ? 'text-profit font-mono text-sm' : 'text-loss font-mono text-sm'}>
                      {run.returns >= 0 ? '+' : ''}{run.returns}%
                    </span>
                  ) : (
                    <span className="badge-loss">Failed</span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-2 text-xs text-ink-faint">
                  <Calendar className="w-3 h-3" />
                  {run.period}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Results Panel */}
        <div className="col-span-3 space-y-6">
          {selectedRun.status === 'completed' ? (
            <>
              {/* Metrics */}
              <div className="grid grid-cols-5 gap-4">
                <div className="card p-4">
                  <p className="stat-label">Returns</p>
                  <p className={clsx(
                    'stat-value',
                    selectedRun.returns >= 0 ? 'text-profit' : 'text-loss'
                  )}>
                    {selectedRun.returns >= 0 ? '+' : ''}{selectedRun.returns}%
                  </p>
                </div>
                <div className="card p-4">
                  <p className="stat-label">Sharpe Ratio</p>
                  <p className="stat-value text-ink">{selectedRun.sharpe}</p>
                </div>
                <div className="card p-4">
                  <p className="stat-label">Max Drawdown</p>
                  <p className="stat-value text-loss">{selectedRun.maxDrawdown}%</p>
                </div>
                <div className="card p-4">
                  <p className="stat-label">Win Rate</p>
                  <p className="stat-value text-ink">{selectedRun.winRate}%</p>
                </div>
                <div className="card p-4">
                  <p className="stat-label">Total Trades</p>
                  <p className="stat-value text-ink">{selectedRun.trades}</p>
                </div>
              </div>

              {/* Equity Curve */}
              <div className="card p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="font-medium text-ink">Equity Curve</h3>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-0.5 bg-accent rounded" />
                      <span className="text-ink-secondary">Strategy</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-0.5 bg-ink-faint rounded" />
                      <span className="text-ink-secondary">Buy & Hold</span>
                    </div>
                  </div>
                </div>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={backtestEquity}>
                      <defs>
                        <linearGradient id="stratGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#14b8a6" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis
                        dataKey="day"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#71717a', fontSize: 11 }}
                        tickFormatter={(v) => `Day ${v}`}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#71717a', fontSize: 11 }}
                        tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                        domain={['dataMin - 500', 'dataMax + 500']}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1c1d21',
                          border: '1px solid #2e3035',
                          borderRadius: '8px',
                        }}
                        formatter={(value: number) => [`$${value.toLocaleString()}`, '']}
                      />
                      <Area
                        type="monotone"
                        dataKey="benchmark"
                        stroke="#52525b"
                        strokeWidth={1}
                        fill="none"
                      />
                      <Area
                        type="monotone"
                        dataKey="portfolio"
                        stroke="#14b8a6"
                        strokeWidth={2}
                        fill="url(#stratGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Trade Distribution */}
              <div className="card p-6">
                <h3 className="font-medium text-ink mb-6">Trade P&L Distribution</h3>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={tradeDistribution}>
                      <XAxis
                        dataKey="range"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#71717a', fontSize: 10 }}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#71717a', fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1c1d21',
                          border: '1px solid #2e3035',
                          borderRadius: '8px',
                        }}
                        formatter={(value: number) => [`${value} trades`, '']}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {tradeDistribution.map((entry, idx) => (
                          <Cell key={idx} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          ) : (
            <div className="card p-12 text-center">
              <Activity className="w-12 h-12 text-warning mx-auto mb-4 animate-pulse" />
              <h3 className="text-lg font-medium text-ink mb-2">Backtest Running</h3>
              <p className="text-ink-secondary mb-6">Processing historical data...</p>
              <div className="w-48 h-2 bg-surface-border rounded-full mx-auto overflow-hidden">
                <div className="h-full w-[45%] bg-warning rounded-full animate-pulse" />
              </div>
              <p className="text-sm text-ink-faint mt-4">Estimated time remaining: 2m 34s</p>
            </div>
          )}
        </div>
      </div>

      {/* New Backtest Modal */}
      {showNewBacktest && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="card p-6 w-full max-w-lg"
          >
            <h2 className="text-lg font-semibold text-ink mb-6">New Backtest</h2>
            <div className="space-y-4">
              <div>
                <label className="label">Strategy</label>
                <select className="input">
                  <option>Momentum v3</option>
                  <option>MeanRevert v2</option>
                  <option>Hybrid</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Start Date</label>
                  <input type="date" className="input" defaultValue="2024-10-01" />
                </div>
                <div>
                  <label className="label">End Date</label>
                  <input type="date" className="input" defaultValue="2024-12-24" />
                </div>
              </div>
              <div>
                <label className="label">Initial Capital</label>
                <input type="number" className="input" defaultValue="10000" />
              </div>
              <div>
                <label className="label">Symbols</label>
                <input type="text" className="input" defaultValue="BTC/USDT, ETH/USDT" />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowNewBacktest(false)} className="btn-ghost flex-1">
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowNewBacktest(false);
                  addToast({ type: 'info', message: 'Backtest started...' });
                }}
                className="btn-primary flex-1"
              >
                <Play className="w-4 h-4" />
                Run Backtest
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </motion.div>
  );
}
