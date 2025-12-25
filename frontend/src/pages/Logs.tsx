import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Download, Filter, Search, Activity, AlertCircle, CheckCircle2, Info, Zap, RefreshCw, Loader2 } from 'lucide-react'
import { useApp } from '../App'
import { api, Activity as ActivityType } from '../services/api'
import clsx from 'clsx'

interface LogEntry {
  id: string;
  type: 'signal' | 'order' | 'fill' | 'error' | 'system' | 'analyzing' | 'thinking';
  message: string;
  details?: string;
  timestamp: string;
  symbol: string;
}

const logTypeConfig: Record<string, { icon: any; color: string; bg: string }> = {
  signal: { icon: Zap, color: 'text-accent', bg: 'bg-accent-muted' },
  signal_generated: { icon: Zap, color: 'text-accent', bg: 'bg-accent-muted' },
  order: { icon: Activity, color: 'text-warning', bg: 'bg-warning-muted' },
  trade_placed: { icon: Activity, color: 'text-warning', bg: 'bg-warning-muted' },
  fill: { icon: CheckCircle2, color: 'text-profit', bg: 'bg-profit-muted' },
  trade_closed: { icon: CheckCircle2, color: 'text-profit', bg: 'bg-profit-muted' },
  error: { icon: AlertCircle, color: 'text-loss', bg: 'bg-loss-muted' },
  system: { icon: Info, color: 'text-ink-secondary', bg: 'bg-surface' },
  analyzing: { icon: Activity, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  thinking: { icon: Info, color: 'text-purple-400', bg: 'bg-purple-500/10' },
  pattern_detected: { icon: Zap, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  risk_check: { icon: AlertCircle, color: 'text-orange-400', bg: 'bg-orange-500/10' },
};

export default function Logs() {
  const { addToast, isAgentRunning } = useApp();
  const [allLogs, setAllLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Fetch logs from API
  const fetchLogs = async () => {
    try {
      const activityData = await api.getActivity();
      const logs: LogEntry[] = activityData.activities.map((activity: ActivityType, idx: number) => ({
        id: `log-${idx}-${Date.now()}`,
        type: activity.type as LogEntry['type'],
        message: activity.title,
        details: activity.description,
        timestamp: new Date(activity.timestamp).toLocaleTimeString(),
        symbol: activity.symbol
      }));
      setAllLogs(logs);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  // Auto-refresh logs
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const filteredLogs = allLogs.filter(log => {
    if (filter !== 'all' && log.type !== filter) return false;
    if (search && !log.message.toLowerCase().includes(search.toLowerCase()) &&
        !log.symbol?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleExport = (format: 'csv' | 'json') => {
    const data = format === 'json'
      ? JSON.stringify(allLogs, null, 2)
      : allLogs.map(l => `${l.timestamp},${l.type},${l.symbol},${l.message}`).join('\n');

    const blob = new Blob([data], { type: format === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trading-logs.${format}`;
    a.click();
    URL.revokeObjectURL(url);

    addToast({ type: 'info', message: `Logs exported as ${format.toUpperCase()}` });
  };

  // Get unique filter types from actual logs
  const filterTypes = ['all', ...new Set(allLogs.map(l => l.type))];

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
          <p className="text-ink-secondary text-sm mt-1">Real-time event history from the trading agent</p>
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
          <button onClick={fetchLogs} className="btn-secondary">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-tertiary" />
            <input
              type="text"
              placeholder="Search logs or symbols..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="w-4 h-4 text-ink-tertiary" />
            {filterTypes.slice(0, 6).map((type) => (
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
                {type.replace('_', ' ')}
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
          <p className="stat-value text-accent">
            {allLogs.filter(l => l.type === 'signal_generated' || l.type === 'signal').length}
          </p>
        </div>
        <div className="card p-4">
          <p className="stat-label">Trades</p>
          <p className="stat-value text-warning">
            {allLogs.filter(l => l.type === 'trade_placed' || l.type === 'order').length}
          </p>
        </div>
        <div className="card p-4">
          <p className="stat-label">Closed</p>
          <p className="stat-value text-profit">
            {allLogs.filter(l => l.type === 'trade_closed' || l.type === 'fill').length}
          </p>
        </div>
        <div className="card p-4">
          <p className="stat-label">Errors</p>
          <p className="stat-value text-loss">{allLogs.filter(l => l.type === 'error').length}</p>
        </div>
      </div>

      {/* Log List */}
      <div className="card">
        {loading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="w-6 h-6 text-accent animate-spin" />
            <span className="ml-3 text-ink-secondary">Loading logs...</span>
          </div>
        ) : (
          <div className="divide-y divide-surface-border max-h-[600px] overflow-y-auto">
            {filteredLogs.length === 0 ? (
              <div className="p-12 text-center">
                <Activity className="w-8 h-8 text-ink-faint mx-auto mb-3" />
                <p className="text-ink-secondary">No logs yet</p>
                <p className="text-xs text-ink-faint mt-1">
                  {isAgentRunning
                    ? 'Waiting for trading activity...'
                    : 'Start the agent to begin generating logs'}
                </p>
              </div>
            ) : (
              filteredLogs.map((log) => {
                const config = logTypeConfig[log.type] || logTypeConfig.system;
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
                            {log.type.replace('_', ' ')}
                          </span>
                          {log.symbol && log.symbol !== 'SYSTEM' && (
                            <span className="text-xs font-mono text-ink-secondary bg-surface px-2 py-0.5 rounded">
                              {log.symbol}
                            </span>
                          )}
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
        )}
      </div>

      {/* Export Options */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-ink">Export Event History</p>
            <p className="text-xs text-ink-tertiary mt-0.5">Download real trading logs for analysis</p>
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
