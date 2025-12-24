import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown, Activity, Target, Wallet, BarChart3, ArrowUpRight, ArrowDownRight, Sparkles, Brain } from 'lucide-react'
import { watchlist, equityHistory, positions, generatePriceUpdate, WatchlistItem } from '../data/mockData'
import { useApp } from '../App'
import clsx from 'clsx'

const staggerChildren = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }
};

export default function Dashboard() {
  const { isAgentRunning, addToast } = useApp();
  const [liveWatchlist, setLiveWatchlist] = useState<WatchlistItem[]>(watchlist);
  const [selectedPeriod, setSelectedPeriod] = useState('1M');

  // Simulate live price updates
  useEffect(() => {
    if (!isAgentRunning) return;

    const interval = setInterval(() => {
      setLiveWatchlist(prev => prev.map(item => {
        const newPrice = generatePriceUpdate(item.price);
        const change = newPrice - (item.price - item.change);
        const changePercent = (change / (item.price - item.change)) * 100;
        return { ...item, price: newPrice, change, changePercent };
      }));
    }, 2000);

    return () => clearInterval(interval);
  }, [isAgentRunning]);

  // Calculate metrics
  const portfolioValue = 13650;
  const dayChange = 370;
  const dayChangePercent = 2.79;
  const totalPnL = 3650;
  const winRate = 67;

  return (
    <motion.div
      variants={staggerChildren}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* Header */}
      <motion.div variants={fadeInUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Dashboard</h1>
          <p className="text-ink-secondary text-sm mt-1">Real-time portfolio overview</p>
        </div>
        <div className="flex items-center gap-2">
          {['1D', '1W', '1M', '3M', 'ALL'].map((period) => (
            <button
              key={period}
              onClick={() => setSelectedPeriod(period)}
              className={clsx(
                'px-3 py-1.5 text-sm font-medium rounded-lg transition-all',
                selectedPeriod === period
                  ? 'bg-accent text-canvas'
                  : 'text-ink-secondary hover:text-ink hover:bg-surface'
              )}
            >
              {period}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Metrics Row */}
      <motion.div variants={fadeInUp} className="grid grid-cols-4 gap-4">
        <div className="card p-5 glow-accent">
          <div className="flex items-center justify-between mb-3">
            <Wallet className="w-5 h-5 text-accent" />
            <span className="badge-profit">+{dayChangePercent.toFixed(2)}%</span>
          </div>
          <p className="stat-value text-ink">${portfolioValue.toLocaleString()}</p>
          <p className="stat-label mt-1">Portfolio Value</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <Activity className="w-5 h-5 text-profit" />
            <span className={dayChange >= 0 ? 'text-profit' : 'text-loss'}>
              {dayChange >= 0 ? '+' : ''}{dayChange.toLocaleString()}
            </span>
          </div>
          <p className="stat-value text-ink">${dayChange >= 0 ? '+' : ''}{dayChange.toLocaleString()}</p>
          <p className="stat-label mt-1">Today's P&L</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <BarChart3 className="w-5 h-5 text-ink-tertiary" />
          </div>
          <p className="stat-value text-profit">+${totalPnL.toLocaleString()}</p>
          <p className="stat-label mt-1">Total Profit</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <Target className="w-5 h-5 text-ink-tertiary" />
          </div>
          <p className="stat-value text-ink">{winRate}%</p>
          <p className="stat-label mt-1">Win Rate</p>
        </div>
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Equity Chart */}
        <motion.div variants={fadeInUp} className="col-span-2 card p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-ink">Equity Curve</h2>
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-0.5 bg-accent rounded" />
                <span className="text-ink-secondary">Portfolio</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-0.5 bg-ink-faint rounded" />
                <span className="text-ink-secondary">Benchmark</span>
              </div>
            </div>
          </div>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityHistory}>
                <defs>
                  <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#14b8a6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#71717a', fontSize: 12 }}
                  tickFormatter={(value) => value.slice(5)}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#71717a', fontSize: 12 }}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                  domain={['dataMin - 500', 'dataMax + 500']}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1c1d21',
                    border: '1px solid #2e3035',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                  }}
                  labelStyle={{ color: '#a1a1aa' }}
                  formatter={(value: number) => [`$${value.toLocaleString()}`, '']}
                />
                <Area
                  type="monotone"
                  dataKey="benchmark"
                  stroke="#52525b"
                  strokeWidth={1}
                  fill="none"
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#14b8a6"
                  strokeWidth={2}
                  fill="url(#equityGradient)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* AI Insight Card */}
        <motion.div variants={fadeInUp} className="card p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-radial from-accent/20 to-transparent" />
          <div className="relative">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-2 bg-accent-muted rounded-lg">
                <Brain className="w-5 h-5 text-accent" />
              </div>
              <h2 className="text-lg font-semibold text-ink">AI Insight</h2>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-sm text-ink-secondary mb-2">Today's Market Bias</p>
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold text-profit">Bullish</span>
                  <TrendingUp className="w-5 h-5 text-profit" />
                </div>
              </div>

              <div className="p-3 bg-surface/50 rounded-lg space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-ink-secondary">Confidence</span>
                  <span className="text-ink font-mono">78%</span>
                </div>
                <div className="w-full h-1.5 bg-surface-border rounded-full overflow-hidden">
                  <div className="h-full w-[78%] bg-gradient-to-r from-accent to-teal-400 rounded-full" />
                </div>
              </div>

              <div className="text-sm text-ink-secondary leading-relaxed">
                <p className="flex items-start gap-2 mb-2">
                  <Sparkles className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
                  BTC showing strong momentum above key EMAs with increasing volume
                </p>
                <p className="flex items-start gap-2">
                  <Sparkles className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
                  RSI indicates room for further upside before overbought
                </p>
              </div>

              <div className="pt-3 border-t border-surface-border">
                <p className="text-xs text-ink-faint">Model: Momentum v3 • Updated 2m ago</p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Watchlist & Positions */}
      <div className="grid grid-cols-2 gap-6">
        {/* Watchlist */}
        <motion.div variants={fadeInUp} className="card">
          <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between">
            <h2 className="font-semibold text-ink">Watchlist</h2>
            <span className="text-xs text-ink-faint">{liveWatchlist.length} assets</span>
          </div>
          <div className="divide-y divide-surface-border">
            {liveWatchlist.map((item) => (
              <div key={item.symbol} className="px-6 py-4 hover:bg-surface-hover transition-colors cursor-pointer group">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-surface flex items-center justify-center font-mono text-sm font-semibold text-ink">
                      {item.symbol.split('/')[0].slice(0, 3)}
                    </div>
                    <div>
                      <p className="font-medium text-ink group-hover:text-accent transition-colors">{item.symbol}</p>
                      <p className="text-xs text-ink-tertiary">{item.name}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-mono font-medium text-ink">
                      ${item.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                    <p className={clsx(
                      'text-sm font-mono flex items-center justify-end gap-1',
                      item.changePercent >= 0 ? 'text-profit' : 'text-loss'
                    )}>
                      {item.changePercent >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                      {item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%
                    </p>
                  </div>
                  {item.signal && (
                    <div className={clsx(
                      'ml-4 px-3 py-1 rounded-lg text-xs font-medium',
                      item.signal === 'buy' && 'bg-profit-muted text-profit',
                      item.signal === 'sell' && 'bg-loss-muted text-loss',
                      item.signal === 'hold' && 'bg-warning-muted text-warning'
                    )}>
                      {item.signal.toUpperCase()}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Positions */}
        <motion.div variants={fadeInUp} className="card">
          <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between">
            <h2 className="font-semibold text-ink">Open Positions</h2>
            <span className="text-xs text-ink-faint">{positions.length} active</span>
          </div>
          <div className="divide-y divide-surface-border">
            {positions.map((pos) => (
              <div key={pos.id} className="px-6 py-4 hover:bg-surface-hover transition-colors">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-ink">{pos.symbol}</p>
                      <span className={clsx(
                        'text-xs px-2 py-0.5 rounded',
                        pos.side === 'long' ? 'bg-profit-muted text-profit' : 'bg-loss-muted text-loss'
                      )}>
                        {pos.side.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-xs text-ink-tertiary mt-1">
                      {pos.quantity} @ ${pos.entryPrice.toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={clsx(
                      'font-mono font-medium',
                      pos.pnl >= 0 ? 'text-profit' : 'text-loss'
                    )}>
                      {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toLocaleString()}
                    </p>
                    <p className={clsx(
                      'text-sm font-mono',
                      pos.pnlPercent >= 0 ? 'text-profit' : 'text-loss'
                    )}>
                      {pos.pnlPercent >= 0 ? '+' : ''}{pos.pnlPercent.toFixed(2)}%
                    </p>
                  </div>
                </div>
              </div>
            ))}
            {positions.length === 0 && (
              <div className="px-6 py-12 text-center">
                <Activity className="w-8 h-8 text-ink-faint mx-auto mb-2" />
                <p className="text-ink-secondary">No open positions</p>
                <p className="text-xs text-ink-faint mt-1">Positions will appear here when trades are opened</p>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
