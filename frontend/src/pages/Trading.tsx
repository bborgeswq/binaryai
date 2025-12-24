import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { AlertOctagon, TrendingUp, TrendingDown, Activity, Clock, Zap } from 'lucide-react'
import { positions, recentOrders, generateCandleData, recentTrades } from '../data/mockData'
import { useApp } from '../App'
import clsx from 'clsx'

export default function Trading() {
  const { isAgentRunning, setIsAgentRunning, addToast } = useApp();
  const [selectedSymbol, setSelectedSymbol] = useState('BTC/USDT');
  const [candleData, setCandleData] = useState(() => generateCandleData(97000, 50));
  const [currentPrice, setCurrentPrice] = useState(97245.32);
  const [priceChange, setPriceChange] = useState(2.25);
  const [tickData, setTickData] = useState<{ price: number; time: string; side: 'buy' | 'sell' }[]>([]);

  // Simulate live updates
  useEffect(() => {
    if (!isAgentRunning) return;

    const interval = setInterval(() => {
      const change = (Math.random() - 0.5) * 100;
      setCurrentPrice(prev => {
        const newPrice = prev + change;
        setTickData(ticks => {
          const newTick = {
            price: Math.round(newPrice * 100) / 100,
            time: new Date().toLocaleTimeString(),
            side: change > 0 ? 'buy' as const : 'sell' as const
          };
          return [newTick, ...ticks].slice(0, 20);
        });
        return newPrice;
      });
    }, 1500);

    return () => clearInterval(interval);
  }, [isAgentRunning]);

  const handleKillSwitch = () => {
    setIsAgentRunning(false);
    addToast({ type: 'warning', message: 'Emergency stop triggered - All trading halted' });
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Live Trading</h1>
          <p className="text-ink-secondary text-sm mt-1">Real-time market data and order execution</p>
        </div>

        {/* Kill Switch */}
        <button
          onClick={handleKillSwitch}
          className="btn-danger px-6 py-3 font-semibold"
        >
          <AlertOctagon className="w-5 h-5" />
          Kill Switch
        </button>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-4 gap-6">
        {/* Price Chart - 3 cols */}
        <div className="col-span-3 space-y-4">
          {/* Symbol Header */}
          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <select
                  value={selectedSymbol}
                  onChange={(e) => setSelectedSymbol(e.target.value)}
                  className="bg-surface border border-surface-border rounded-lg px-4 py-2 text-ink font-medium focus:border-accent outline-none"
                >
                  <option value="BTC/USDT">BTC/USDT</option>
                  <option value="ETH/USDT">ETH/USDT</option>
                  <option value="SOL/USDT">SOL/USDT</option>
                </select>
                <div>
                  <span className="text-3xl font-bold font-mono text-ink">
                    ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  <span className={clsx(
                    'ml-3 text-lg font-mono',
                    priceChange >= 0 ? 'text-profit' : 'text-loss'
                  )}>
                    {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {isAgentRunning ? (
                  <span className="badge-profit">
                    <Zap className="w-3 h-3" />
                    Agent Active
                  </span>
                ) : (
                  <span className="badge bg-surface text-ink-tertiary">
                    Agent Paused
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Chart */}
          <div className="card p-6">
            <div className="h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={candleData}>
                  <defs>
                    <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.2} />
                      <stop offset="100%" stopColor="#14b8a6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="time"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#71717a', fontSize: 11 }}
                    tickFormatter={(v) => new Date(v).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    minTickGap={50}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#71717a', fontSize: 11 }}
                    domain={['dataMin - 500', 'dataMax + 500']}
                    tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                    orientation="right"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1c1d21',
                      border: '1px solid #2e3035',
                      borderRadius: '8px',
                    }}
                    labelFormatter={(v) => new Date(v).toLocaleString()}
                    formatter={(value: number, name: string) => [
                      `$${value.toLocaleString()}`,
                      name === 'close' ? 'Price' : name
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="close"
                    stroke="#14b8a6"
                    strokeWidth={2}
                    fill="url(#priceGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Orders & Trades Tabs */}
          <div className="card">
            <div className="border-b border-surface-border">
              <div className="flex">
                <button className="px-6 py-3 text-sm font-medium text-accent border-b-2 border-accent">
                  Open Orders ({recentOrders.filter(o => o.status === 'pending').length})
                </button>
                <button className="px-6 py-3 text-sm font-medium text-ink-secondary hover:text-ink">
                  Recent Trades
                </button>
                <button className="px-6 py-3 text-sm font-medium text-ink-secondary hover:text-ink">
                  Positions ({positions.length})
                </button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs text-ink-faint uppercase tracking-wider">
                    <th className="px-6 py-3">Time</th>
                    <th className="px-6 py-3">Symbol</th>
                    <th className="px-6 py-3">Type</th>
                    <th className="px-6 py-3">Side</th>
                    <th className="px-6 py-3">Quantity</th>
                    <th className="px-6 py-3">Price</th>
                    <th className="px-6 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {recentOrders.map((order) => (
                    <tr key={order.id} className="hover:bg-surface-hover transition-colors">
                      <td className="px-6 py-4 text-sm font-mono text-ink-secondary">{order.time}</td>
                      <td className="px-6 py-4 text-sm font-medium text-ink">{order.symbol}</td>
                      <td className="px-6 py-4 text-sm text-ink-secondary capitalize">{order.type}</td>
                      <td className="px-6 py-4">
                        <span className={clsx(
                          'text-sm font-medium',
                          order.side === 'buy' ? 'text-profit' : 'text-loss'
                        )}>
                          {order.side.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm font-mono text-ink">{order.quantity}</td>
                      <td className="px-6 py-4 text-sm font-mono text-ink">${order.price.toLocaleString()}</td>
                      <td className="px-6 py-4">
                        <span className={clsx(
                          'badge',
                          order.status === 'filled' && 'bg-profit-muted text-profit',
                          order.status === 'pending' && 'bg-warning-muted text-warning',
                          order.status === 'cancelled' && 'bg-surface text-ink-tertiary'
                        )}>
                          {order.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Tape & Quick Actions - 1 col */}
        <div className="space-y-4">
          {/* Time & Sales Tape */}
          <div className="card">
            <div className="px-4 py-3 border-b border-surface-border">
              <h3 className="font-medium text-ink text-sm">Time & Sales</h3>
            </div>
            <div className="h-[300px] overflow-y-auto">
              {tickData.length === 0 ? (
                <div className="p-8 text-center text-ink-faint text-sm">
                  <Activity className="w-6 h-6 mx-auto mb-2 opacity-50" />
                  Start agent to see live trades
                </div>
              ) : (
                <div className="divide-y divide-surface-border">
                  {tickData.map((tick, i) => (
                    <div key={i} className="px-4 py-2 flex items-center justify-between text-sm font-mono">
                      <span className="text-ink-faint">{tick.time}</span>
                      <span className={tick.side === 'buy' ? 'text-profit' : 'text-loss'}>
                        ${tick.price.toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Quick Stats */}
          <div className="card p-4 space-y-4">
            <h3 className="font-medium text-ink text-sm">Session Stats</h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-ink-secondary">Trades Today</span>
                <span className="font-mono text-ink">12</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-ink-secondary">Win Rate</span>
                <span className="font-mono text-profit">67%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-ink-secondary">Day P&L</span>
                <span className="font-mono text-profit">+$847.50</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-ink-secondary">Max Drawdown</span>
                <span className="font-mono text-loss">-$234.00</span>
              </div>
            </div>
          </div>

          {/* Recent Fills */}
          <div className="card">
            <div className="px-4 py-3 border-b border-surface-border">
              <h3 className="font-medium text-ink text-sm">Recent Fills</h3>
            </div>
            <div className="divide-y divide-surface-border">
              {recentTrades.slice(0, 4).map((trade) => (
                <div key={trade.id} className="px-4 py-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className={clsx(
                        'text-xs font-medium',
                        trade.side === 'buy' ? 'text-profit' : 'text-loss'
                      )}>
                        {trade.side.toUpperCase()}
                      </span>
                      <span className="text-sm text-ink ml-2">{trade.symbol}</span>
                    </div>
                    <span className={clsx(
                      'text-sm font-mono',
                      trade.pnl >= 0 ? 'text-profit' : 'text-loss'
                    )}>
                      {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-ink-faint">
                    <Clock className="w-3 h-3" />
                    {trade.time}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
