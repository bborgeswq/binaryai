import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Download, Filter, Search, Activity, AlertCircle, CheckCircle2, Info, Zap, RefreshCw } from 'lucide-react'
import { logs, LogEntry } from '../data/mockData'
import { useApp } from '../App'
import clsx from 'clsx'

const logTypeConfig = {
  signal: { icon: Zap, color: 'text-accent', bg: 'bg-accent-muted' },
  order: { icon: Activity, color: 'text-warning', bg: 'bg-warning-muted' },
  fill: { icon: CheckCircle2, color: 'text-profit', bg: 'bg-profit-muted' },
  error: { icon: AlertCircle, color: 'text-loss', bg: 'bg-loss-muted' },
  system: { icon: Info, color: 'text-ink-secondary', bg: 'bg-surface' },
};

export default function Logs() {
  const { addToast, isAgentRunning } = useApp();
  const [allLogs, setAllLogs] = useState<LogEntry[]>(logs);
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Simulate new logs when agent is running
  useEffect(() => {
    if (!isAgentRunning || !autoRefresh) return;

    const interval = setInterval(() => {
      const types: LogEntry['type'][] = ['signal', 'order', 'fill', 'system'];
      const randomType = types[Math.floor(Math.random() * types.length)];
      const messages = {
        signal: ['BUY signal generated for ETH/USDT', 'SELL signal for SOL/USDT', 'HOLD signal for BTC/USDT'],
        order: ['Limit order placed: BTC/USDT', 'Stop order modified: ETH/USDT', 'Order cancelled: SOL/USDT'],
        fill: ['Order filled: BTC/USDT', 'Partial fill: ETH/USDT', 'Order completed: XRP/USDT'],
        system: ['Model weights updated', 'Connection health check passed', 'Risk limits recalculated'],
      };

      const newLog: LogEntry = {
        id: Math.random().toString(36).slice(2),
        type: randomType,
        message: messages[randomType][Math.floor(Math.random() * messages[randomType].length)],
        timestamp: new Date().toLocaleTimeString(),
      };

      setAllLogs(prev => [newLog, ...prev].slice(0, 100));
    }, 5000);

    return () => clearInterval(interval);
  }, [isAgentRunning, autoRefresh]);

  const filteredLogs = allLogs.filter(log => {
    if (filter !== 'all' && log.type !== filter) return false;
    if (search && !log.message.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleExport = (format: 'csv' | 'json') => {
    addToast({ type: 'info', message: `Exporting logs as ${format.toUpperCase()}...` });
    // In real app, would trigger download
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
          <h1 className="text-2xl font-bold text-ink">Logs & Audit</h1>
          <p className="text-ink-secondary text-sm mt-1">Complete event history and system logs</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={clsx(
              'btn-secondary',
              autoRefresh && 'text-accent border-accent/30'
            )}
          >
            <RefreshCw className={clsx('w-4 h-4', autoRefresh && 'animate-spin')} />
            {autoRefresh ? 'Auto-refresh On' : 'Auto-refresh Off'}
          </button>
          <div className="relative">
            <button className="btn-secondary">
              <Download className="w-4 h-4" />
              Export
            </button>
            {/* Dropdown would go here */}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-tertiary" />
            <input
              type="text"
              placeholder="Search logs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-ink-tertiary" />
            {['all', 'signal', 'order', 'fill', 'error', 'system'].map((type) => (
              <button
                key={type}
                onClick={() => setFilter(type)}
                className={clsx(
                  'px-3 py-1.5 text-sm font-medium rounded-lg transition-colors capitalize',
                  filter === type
                    ? 'bg-accent text-canvas'
                    : 'text-ink-secondary hover:text-ink hover:bg-surface'
                )}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        <div className="card p-4">
          <p className="stat-label">Total Events</p>
          <p className="stat-value text-ink">{allLogs.length}</p>
        </div>
        <div className="card p-4">
          <p className="stat-label">Signals</p>
          <p className="stat-value text-accent">{allLogs.filter(l => l.type === 'signal').length}</p>
        </div>
        <div className="card p-4">
          <p className="stat-label">Orders</p>
          <p className="stat-value text-warning">{allLogs.filter(l => l.type === 'order').length}</p>
        </div>
        <div className="card p-4">
          <p className="stat-label">Fills</p>
          <p className="stat-value text-profit">{allLogs.filter(l => l.type === 'fill').length}</p>
        </div>
        <div className="card p-4">
          <p className="stat-label">Errors</p>
          <p className="stat-value text-loss">{allLogs.filter(l => l.type === 'error').length}</p>
        </div>
      </div>

      {/* Log List */}
      <div className="card">
        <div className="divide-y divide-surface-border max-h-[600px] overflow-y-auto">
          {filteredLogs.length === 0 ? (
            <div className="p-12 text-center">
              <Activity className="w-8 h-8 text-ink-faint mx-auto mb-3" />
              <p className="text-ink-secondary">No logs matching your filters</p>
              <p className="text-xs text-ink-faint mt-1">Try adjusting your search or filter criteria</p>
            </div>
          ) : (
            filteredLogs.map((log) => {
              const config = logTypeConfig[log.type];
              const Icon = config.icon;
              return (
                <div key={log.id} className="px-6 py-4 hover:bg-surface-hover transition-colors">
                  <div className="flex items-start gap-4">
                    <div className={clsx('p-2 rounded-lg flex-shrink-0', config.bg)}>
                      <Icon className={clsx('w-4 h-4', config.color)} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <span className={clsx('text-xs font-medium uppercase tracking-wider', config.color)}>
                          {log.type}
                        </span>
                        <span className="text-xs text-ink-faint font-mono">{log.timestamp}</span>
                      </div>
                      <p className="text-sm text-ink mt-1">{log.message}</p>
                      {log.details && (
                        <p className="text-xs text-ink-tertiary mt-1">{log.details}</p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Export Options */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-ink">Export Event History</p>
            <p className="text-xs text-ink-tertiary mt-0.5">Download logs for external analysis or compliance</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => handleExport('csv')} className="btn-secondary">
              <Download className="w-4 h-4" />
              Export CSV
            </button>
            <button onClick={() => handleExport('json')} className="btn-secondary">
              <Download className="w-4 h-4" />
              Export JSON
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
