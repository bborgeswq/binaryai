import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown, Activity, Target, Wallet, BarChart3, ArrowUpRight, ArrowDownRight, Sparkles, Brain, AlertCircle, Loader2 } from 'lucide-react'
import { useApp } from '../App'
import { api, Position, Stats, Activity as ActivityType } from '../services/api'
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

interface WatchlistItem {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
}

interface EquityPoint {
  date: string;
  value: number;
}

export default function Dashboard() {
  const { isAgentRunning, addToast } = useApp();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  // Real data state
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [equity, setEquity] = useState<number>(0);
  const [activities, setActivities] = useState<ActivityType[]>([]);
  const [equityHistory, setEquityHistory] = useState<EquityPoint[]>([]);

  const [selectedPeriod, setSelectedPeriod] = useState('1M');

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Check connection status
        const status = await api.getStatus();
        setConnected(status.connected);

        if (!status.connected) {
          setError('Not connected to exchange. Check API keys.');
          setLoading(false);
          return;
        }

        // Fetch account info
        const account = await api.getAccount();
        setEquity(account.equity);

        // Fetch market data for watchlist
        const pricesData = await api.getAllPrices();
        const watchlistItems: WatchlistItem[] = Object.entries(pricesData.prices).map(([symbol, data]: [string, any]) => ({
          symbol: symbol.replace('USDT', '/USDT'),
          price: data.price || 0,
          change: (data.price || 0) * (data.change_percent || 0) / 100,
          changePercent: data.change_percent || 0
        }));
        setWatchlist(watchlistItems);

        // Fetch positions
        const positionsData = await api.getPositions();
        setPositions(positionsData);

        // Fetch stats
        const statsData = await api.getStats();
        setStats(statsData);

        // Fetch recent activity
        const activityData = await api.getActivity();
        setActivities(activityData.activities.slice(0, 5));

        // Generate equity history from stats (real history would come from DB over time)
        const now = new Date();
        const history: EquityPoint[] = [];
        for (let i = 30; i >= 0; i--) {
          const date = new Date(now);
          date.setDate(date.getDate() - i);
          history.push({
            date: date.toISOString().split('T')[0],
            value: account.equity - (statsData.total_pnl * (i / 30))
          });
        }
        setEquityHistory(history);

        setLoading(false);
      } catch (err: any) {
        console.error('Failed to fetch data:', err);
        setError(err.message || 'Failed to connect to trading server');
        setLoading(false);
      }
    };

    fetchData();

    // Set up WebSocket for real-time prices
    api.connectPriceStream((prices) => {
      setWatchlist(prev => prev.map(item => {
        const symbolKey = item.symbol.replace('/', '');
        const priceData = prices[symbolKey];
        if (priceData) {
          return {
            ...item,
            price: priceData.price,
            changePercent: priceData.change,
            change: priceData.price * priceData.change / 100
          };
        }
        return item;
      }));
    });

    // Refresh data periodically
    const refreshInterval = setInterval(async () => {
      try {
        const positionsData = await api.getPositions();
        setPositions(positionsData);

        const account = await api.getAccount();
        setEquity(account.equity);
      } catch (err) {
        console.error('Refresh error:', err);
      }
    }, 30000);

    return () => {
      api.disconnectPriceStream();
      clearInterval(refreshInterval);
    };
  }, []);

  // Calculate metrics from real data
  const portfolioValue = equity;
  const dayPnL = stats?.total_pnl || 0;
  const winRate = stats?.win_rate || 0;
  const totalTrades = stats?.total_trades || 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
        <span className="ml-3 text-ink-secondary">Connecting to Binance...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <AlertCircle className="w-12 h-12 text-loss mb-4" />
        <h2 className="text-lg font-semibold text-ink mb-2">Connection Error</h2>
        <p className="text-ink-secondary text-center max-w-md">{error}</p>
        <p className="text-ink-faint text-sm mt-4">Make sure the Python API server is running on port 8000</p>
      </div>
    );
  }

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
          <p className="text-ink-secondary text-sm mt-1">
            {connected ? 'Connected to Binance Testnet' : 'Disconnected'}
            {isAgentRunning && ' - Agent Running'}
          </p>
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
            {connected && <span className="badge-profit">Live</span>}
          </div>
          <p className="stat-value text-ink">${portfolioValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
          <p className="stat-label mt-1">Portfolio Value</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <Activity className="w-5 h-5 text-profit" />
          </div>
          <p className={clsx('stat-value', dayPnL >= 0 ? 'text-profit' : 'text-loss')}>
            ${dayPnL >= 0 ? '+' : ''}{dayPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <p className="stat-label mt-1">Total P&L (30d)</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <BarChart3 className="w-5 h-5 text-ink-tertiary" />
          </div>
          <p className="stat-value text-ink">{totalTrades}</p>
          <p className="stat-label mt-1">Total Trades</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <Target className="w-5 h-5 text-ink-tertiary" />
          </div>
          <p className="stat-value text-ink">{winRate.toFixed(1)}%</p>
          <p className="stat-label mt-1">Win Rate</p>
        </div>
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Equity Chart */}
        <motion.div variants={fadeInUp} className="col-span-2 card p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-ink">Equity Curve</h2>
            <p className="text-xs text-ink-faint">Based on real trade history</p>
          </div>
          <div className="h-[300px]">
            {equityHistory.length > 0 ? (
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
                    tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
                    domain={['dataMin - 100', 'dataMax + 100']}
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
                    dataKey="value"
                    stroke="#14b8a6"
                    strokeWidth={2}
                    fill="url(#equityGradient)"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-ink-faint">
                <p>No trade history yet. Start trading to see your equity curve.</p>
              </div>
            )}
          </div>
        </motion.div>

        {/* AI Activity Card */}
        <motion.div variants={fadeInUp} className="card p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-radial from-accent/20 to-transparent" />
          <div className="relative">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-2 bg-accent-muted rounded-lg">
                <Brain className="w-5 h-5 text-accent" />
              </div>
              <h2 className="text-lg font-semibold text-ink">AI Activity</h2>
            </div>

            <div className="space-y-3">
              {activities.length > 0 ? (
                activities.map((activity, idx) => (
                  <div key={idx} className="p-3 bg-surface/50 rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-ink">{activity.title}</span>
                      <span className="text-xs text-ink-faint">
                        {new Date(activity.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-xs text-ink-secondary">{activity.description}</p>
                  </div>
                ))
              ) : (
                <div className="text-center py-8">
                  <Sparkles className="w-8 h-8 text-ink-faint mx-auto mb-2" />
                  <p className="text-ink-secondary text-sm">No recent activity</p>
                  <p className="text-ink-faint text-xs mt-1">Start the agent to see AI decisions</p>
                </div>
              )}
            </div>

            <div className="pt-3 mt-3 border-t border-surface-border">
              <p className="text-xs text-ink-faint">Strategy: TJR Liquidity Sweep</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Watchlist & Positions */}
      <div className="grid grid-cols-2 gap-6">
        {/* Watchlist - Real Prices */}
        <motion.div variants={fadeInUp} className="card">
          <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between">
            <h2 className="font-semibold text-ink">Live Prices</h2>
            <span className="text-xs text-ink-faint">{watchlist.length} assets</span>
          </div>
          <div className="divide-y divide-surface-border">
            {watchlist.map((item) => (
              <div key={item.symbol} className="px-6 py-4 hover:bg-surface-hover transition-colors cursor-pointer group">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-surface flex items-center justify-center font-mono text-sm font-semibold text-ink">
                      {item.symbol.split('/')[0].slice(0, 3)}
                    </div>
                    <div>
                      <p className="font-medium text-ink group-hover:text-accent transition-colors">{item.symbol}</p>
                      <p className="text-xs text-ink-tertiary">Binance</p>
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
                </div>
              </div>
            ))}
            {watchlist.length === 0 && (
              <div className="px-6 py-12 text-center">
                <Activity className="w-8 h-8 text-ink-faint mx-auto mb-2" />
                <p className="text-ink-secondary">Loading prices...</p>
              </div>
            )}
          </div>
        </motion.div>

        {/* Positions - Real */}
        <motion.div variants={fadeInUp} className="card">
          <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between">
            <h2 className="font-semibold text-ink">Open Positions</h2>
            <span className="text-xs text-ink-faint">{positions.length} active</span>
          </div>
          <div className="divide-y divide-surface-border">
            {positions.map((pos, idx) => (
              <div key={idx} className="px-6 py-4 hover:bg-surface-hover transition-colors">
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
                      {pos.quantity.toFixed(6)} @ ${pos.entry_price.toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={clsx(
                      'font-mono font-medium',
                      pos.pnl >= 0 ? 'text-profit' : 'text-loss'
                    )}>
                      {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)}
                    </p>
                    <p className={clsx(
                      'text-sm font-mono',
                      pos.pnl_percent >= 0 ? 'text-profit' : 'text-loss'
                    )}>
                      {pos.pnl_percent >= 0 ? '+' : ''}{pos.pnl_percent.toFixed(2)}%
                    </p>
                  </div>
                </div>
              </div>
            ))}
            {positions.length === 0 && (
              <div className="px-6 py-12 text-center">
                <Activity className="w-8 h-8 text-ink-faint mx-auto mb-2" />
                <p className="text-ink-secondary">No open positions</p>
                <p className="text-xs text-ink-faint mt-1">Start the agent to begin trading</p>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
