import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { AlertOctagon, Activity, Clock, Zap, Loader2, Play, Square } from 'lucide-react'
import { useApp } from '../App'
import { api } from '../services/api'
import AIThoughts from '../components/AIThoughts'
import CandlestickChart from '../components/CandlestickChart'
import clsx from 'clsx'

interface Position {
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
}

interface Trade {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  exit_price: number | null;
  pnl: number | null;
  status: string;
  entry_time: string;
}

export default function Trading() {
  const { isAgentRunning, setIsAgentRunning, addToast } = useApp();
  const [selectedSymbol, setSelectedSymbol] = useState('BTC/USDT');
  const [currentPrice, setCurrentPrice] = useState(0);
  const [priceChange, setPriceChange] = useState(0);
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [agentLoading, setAgentLoading] = useState(false);

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Get current price
        const marketData = await api.getMarketData(selectedSymbol.replace('/', ''));
        setCurrentPrice(marketData.price);
        setPriceChange(marketData.change_percent);

        // Get positions
        const positionsData = await api.getPositions();
        setPositions(positionsData);

        // Get trades
        const tradesData = await api.getTrades(10);
        setTrades(tradesData);

        // Get agent status
        const agentStatus = await api.getAgentStatus();
        setIsAgentRunning(agentStatus.running);

        setLoading(false);
      } catch (err) {
        console.error('Failed to fetch data:', err);
        setLoading(false);
      }
    };

    fetchData();

    // Connect to price stream
    api.connectPriceStream((prices) => {
      const symbolKey = selectedSymbol.replace('/', '');
      const priceData = prices[symbolKey];
      if (priceData) {
        setCurrentPrice(priceData.price);
        setPriceChange(priceData.change);
      }
    });

    // Refresh positions and trades periodically
    const refreshInterval = setInterval(async () => {
      try {
        const positionsData = await api.getPositions();
        setPositions(positionsData);

        const tradesData = await api.getTrades(10);
        setTrades(tradesData);

        const agentStatus = await api.getAgentStatus();
        setIsAgentRunning(agentStatus.running);
      } catch (err) {
        console.error('Refresh error:', err);
      }
    }, 10000);

    return () => {
      api.disconnectPriceStream();
      clearInterval(refreshInterval);
    };
  }, [selectedSymbol, setIsAgentRunning]);

  const handleStartAgent = async () => {
    setAgentLoading(true);
    try {
      await api.startAgent();
      setIsAgentRunning(true);
      addToast({ type: 'info', message: 'Trading agent started - analyzing markets' });
    } catch (err: any) {
      addToast({ type: 'error', message: err.message || 'Failed to start agent' });
    }
    setAgentLoading(false);
  };

  const handleStopAgent = async () => {
    setAgentLoading(true);
    try {
      await api.stopAgent();
      setIsAgentRunning(false);
      addToast({ type: 'warning', message: 'Trading agent stopped' });
    } catch (err: any) {
      addToast({ type: 'error', message: err.message || 'Failed to stop agent' });
    }
    setAgentLoading(false);
  };

  const handleKillSwitch = async () => {
    await handleStopAgent();
    addToast({ type: 'warning', message: 'Emergency stop triggered - All trading halted' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
        <span className="ml-3 text-ink-secondary">Loading trading data...</span>
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Live Trading</h1>
          <p className="text-ink-secondary text-sm mt-1">Real-time market data and AI-powered execution</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Agent Control */}
          {isAgentRunning ? (
            <button
              onClick={handleStopAgent}
              disabled={agentLoading}
              className="btn-secondary text-warning border-warning/30"
            >
              {agentLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Square className="w-4 h-4" />}
              Stop Agent
            </button>
          ) : (
            <button
              onClick={handleStartAgent}
              disabled={agentLoading}
              className="btn-primary"
            >
              {agentLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Start Agent
            </button>
          )}

          {/* Kill Switch */}
          <button
            onClick={handleKillSwitch}
            className="btn-danger px-6 py-3 font-semibold"
          >
            <AlertOctagon className="w-5 h-5" />
            Kill Switch
          </button>
        </div>
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
                  <option value="XRP/USDT">XRP/USDT</option>
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
                    Agent Stopped
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Candlestick Chart - Real-time 1m candles */}
          <div className="card p-4">
            <CandlestickChart symbol={selectedSymbol} timeframe="1m" height={380} />
          </div>

          {/* Positions & Trades */}
          <div className="card">
            <div className="border-b border-surface-border">
              <div className="flex">
                <button className="px-6 py-3 text-sm font-medium text-accent border-b-2 border-accent">
                  Positions ({positions.length})
                </button>
                <button className="px-6 py-3 text-sm font-medium text-ink-secondary hover:text-ink">
                  Trade History ({trades.length})
                </button>
              </div>
            </div>
            <div className="overflow-x-auto">
              {positions.length === 0 ? (
                <div className="p-8 text-center">
                  <Activity className="w-6 h-6 text-ink-faint mx-auto mb-2" />
                  <p className="text-ink-secondary text-sm">No open positions</p>
                  <p className="text-ink-faint text-xs mt-1">Trades will appear here when the agent opens positions</p>
                </div>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-xs text-ink-faint uppercase tracking-wider">
                      <th className="px-6 py-3">Symbol</th>
                      <th className="px-6 py-3">Side</th>
                      <th className="px-6 py-3">Quantity</th>
                      <th className="px-6 py-3">Entry</th>
                      <th className="px-6 py-3">Current</th>
                      <th className="px-6 py-3">P&L</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {positions.map((pos, idx) => (
                      <tr key={idx} className="hover:bg-surface-hover transition-colors">
                        <td className="px-6 py-4 text-sm font-medium text-ink">{pos.symbol}</td>
                        <td className="px-6 py-4">
                          <span className={clsx(
                            'text-sm font-medium',
                            pos.side === 'long' ? 'text-profit' : 'text-loss'
                          )}>
                            {pos.side.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm font-mono text-ink">{pos.quantity.toFixed(6)}</td>
                        <td className="px-6 py-4 text-sm font-mono text-ink">${pos.entry_price.toLocaleString()}</td>
                        <td className="px-6 py-4 text-sm font-mono text-ink">${pos.current_price.toLocaleString()}</td>
                        <td className="px-6 py-4">
                          <span className={clsx(
                            'text-sm font-mono font-medium',
                            pos.pnl >= 0 ? 'text-profit' : 'text-loss'
                          )}>
                            {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)} ({pos.pnl_percent.toFixed(2)}%)
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        {/* AI Panel - 1 col */}
        <div className="space-y-4">
          {/* AI Thoughts Component */}
          <AIThoughts />

          {/* Recent Trades */}
          <div className="card">
            <div className="px-4 py-3 border-b border-surface-border">
              <h3 className="font-medium text-ink text-sm">Recent Trades</h3>
            </div>
            <div className="divide-y divide-surface-border max-h-[300px] overflow-y-auto">
              {trades.length === 0 ? (
                <div className="p-6 text-center">
                  <Clock className="w-5 h-5 text-ink-faint mx-auto mb-2" />
                  <p className="text-sm text-ink-secondary">No trades yet</p>
                </div>
              ) : (
                trades.map((trade) => (
                  <div key={trade.id} className="px-4 py-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className={clsx(
                          'text-xs font-medium',
                          trade.side === 'BUY' ? 'text-profit' : 'text-loss'
                        )}>
                          {trade.side}
                        </span>
                        <span className="text-sm text-ink ml-2">{trade.symbol}</span>
                      </div>
                      {trade.pnl !== null && (
                        <span className={clsx(
                          'text-sm font-mono',
                          trade.pnl >= 0 ? 'text-profit' : 'text-loss'
                        )}>
                          {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-ink-faint">
                      <Clock className="w-3 h-3" />
                      {new Date(trade.entry_time).toLocaleString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Strategy Info */}
          <div className="card p-4 space-y-3">
            <h3 className="font-medium text-ink text-sm">Strategy: TJR Liquidity Sweep</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-ink-secondary">Risk per Trade</span>
                <span className="font-mono text-ink">7%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-secondary">Min R:R</span>
                <span className="font-mono text-ink">2:1</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-secondary">Symbols</span>
                <span className="font-mono text-ink">BTC, ETH, XRP</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-secondary">Analysis Interval</span>
                <span className="font-mono text-ink">60s</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
