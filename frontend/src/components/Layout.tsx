import { ReactNode, useState } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  TrendingUp,
  FlaskConical,
  Shield,
  Brain,
  ScrollText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Command,
  Search,
  Pause,
  Play,
  Download,
  Plus,
  Zap,
  X,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
} from 'lucide-react'
import { useApp } from '../App'
import clsx from 'clsx'

interface LayoutProps {
  children: ReactNode;
}

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/trading', label: 'Live Trading', icon: TrendingUp },
  { path: '/strategy', label: 'Strategy Lab', icon: FlaskConical },
  { path: '/risk', label: 'Risk Controls', icon: Shield },
  { path: '/models', label: 'Models', icon: Brain },
  { path: '/logs', label: 'Logs', icon: ScrollText },
  { path: '/settings', label: 'Settings', icon: Settings },
];

const commandActions = [
  { id: 'dashboard', label: 'Go to Dashboard', icon: LayoutDashboard, path: '/' },
  { id: 'trading', label: 'Go to Live Trading', icon: TrendingUp, path: '/trading' },
  { id: 'strategy', label: 'Go to Strategy Lab', icon: FlaskConical, path: '/strategy' },
  { id: 'risk', label: 'Go to Risk Controls', icon: Shield, path: '/risk' },
  { id: 'pause', label: 'Pause Trading Agent', icon: Pause, action: 'pause' },
  { id: 'start', label: 'Start Trading Agent', icon: Play, action: 'start' },
  { id: 'export', label: 'Export Trade History', icon: Download, action: 'export' },
  { id: 'backtest', label: 'New Backtest', icon: Plus, action: 'backtest' },
];

export default function Layout({ children }: LayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const {
    isPaperTrading,
    isAgentRunning,
    setIsAgentRunning,
    showCommandPalette,
    setShowCommandPalette,
    toasts,
    removeToast,
    addToast,
  } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchQuery, setSearchQuery] = useState('');

  const filteredCommands = commandActions.filter(cmd =>
    cmd.label.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const executeCommand = (cmd: typeof commandActions[0]) => {
    if (cmd.path) {
      navigate(cmd.path);
    } else if (cmd.action === 'pause') {
      setIsAgentRunning(false);
      addToast({ type: 'warning', message: 'Trading agent paused' });
    } else if (cmd.action === 'start') {
      setIsAgentRunning(true);
      addToast({ type: 'success', message: 'Trading agent started' });
    } else if (cmd.action === 'export') {
      addToast({ type: 'info', message: 'Exporting trade history...' });
    } else if (cmd.action === 'backtest') {
      navigate('/strategy');
      addToast({ type: 'info', message: 'Opening backtest creator...' });
    }
    setShowCommandPalette(false);
    setSearchQuery('');
  };

  const toastIcons = {
    success: CheckCircle2,
    error: AlertCircle,
    warning: AlertTriangle,
    info: Info,
  };

  const toastColors = {
    success: 'bg-profit-muted border-profit/30 text-profit',
    error: 'bg-loss-muted border-loss/30 text-loss',
    warning: 'bg-warning-muted border-warning/30 text-warning',
    info: 'bg-accent-muted border-accent/30 text-accent',
  };

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed left-0 top-0 h-screen bg-canvas-elevated border-r border-surface-border z-40 transition-all duration-300 flex flex-col',
          sidebarCollapsed ? 'w-16' : 'w-56'
        )}
      >
        {/* Logo */}
        <div className="h-14 flex items-center justify-between px-4 border-b border-surface-border">
          {!sidebarCollapsed && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-teal-400 flex items-center justify-center">
                <Zap className="w-4 h-4 text-canvas" />
              </div>
              <span className="font-semibold text-ink">Vertex</span>
            </div>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1.5 rounded-lg hover:bg-surface transition-colors text-ink-tertiary hover:text-ink"
          >
            {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group',
                isActive
                  ? 'bg-accent-muted text-accent'
                  : 'text-ink-secondary hover:text-ink hover:bg-surface'
              )}
            >
              <item.icon className={clsx(
                'w-5 h-5 flex-shrink-0',
                location.pathname === item.path && 'text-accent'
              )} />
              {!sidebarCollapsed && (
                <span className="text-sm font-medium">{item.label}</span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Status */}
        <div className="p-3 border-t border-surface-border">
          {isPaperTrading && (
            <div className={clsx(
              'flex items-center gap-2 px-3 py-2 rounded-lg bg-warning-muted',
              sidebarCollapsed && 'justify-center'
            )}>
              <div className="w-2 h-2 rounded-full bg-warning animate-pulse" />
              {!sidebarCollapsed && (
                <span className="text-xs font-medium text-warning">Paper Trading</span>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className={clsx(
        'flex-1 transition-all duration-300',
        sidebarCollapsed ? 'ml-16' : 'ml-56'
      )}>
        {/* Top Bar */}
        <header className="h-14 border-b border-surface-border bg-canvas-elevated/80 backdrop-blur-sm sticky top-0 z-30 flex items-center justify-between px-6">
          {/* Command Bar Trigger */}
          <button
            onClick={() => setShowCommandPalette(true)}
            className="flex items-center gap-3 px-4 py-2 bg-surface rounded-lg border border-surface-border hover:border-surface-active transition-colors group"
          >
            <Search className="w-4 h-4 text-ink-tertiary group-hover:text-ink-secondary" />
            <span className="text-sm text-ink-tertiary group-hover:text-ink-secondary">Search or command...</span>
            <kbd className="hidden sm:flex items-center gap-1 px-2 py-0.5 bg-canvas rounded text-xs text-ink-faint">
              <Command className="w-3 h-3" />K
            </kbd>
          </button>

          {/* Right Actions */}
          <div className="flex items-center gap-3">
            {/* Agent Status */}
            <button
              onClick={() => {
                setIsAgentRunning(!isAgentRunning);
                addToast({
                  type: isAgentRunning ? 'warning' : 'success',
                  message: isAgentRunning ? 'Agent paused' : 'Agent started'
                });
              }}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all',
                isAgentRunning
                  ? 'bg-profit-muted text-profit hover:bg-profit/20'
                  : 'bg-surface text-ink-secondary hover:bg-surface-hover'
              )}
            >
              {isAgentRunning ? (
                <>
                  <div className="w-2 h-2 rounded-full bg-profit animate-pulse" />
                  <span>Agent Running</span>
                  <Pause className="w-4 h-4" />
                </>
              ) : (
                <>
                  <div className="w-2 h-2 rounded-full bg-ink-faint" />
                  <span>Agent Stopped</span>
                  <Play className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-6 animate-fade-in">
          {children}
        </div>
      </main>

      {/* Command Palette */}
      <AnimatePresence>
        {showCommandPalette && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
              onClick={() => setShowCommandPalette(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -20 }}
              transition={{ duration: 0.15 }}
              className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg z-50"
            >
              <div className="bg-canvas-overlay border border-surface-border rounded-xl shadow-2xl overflow-hidden">
                <div className="flex items-center gap-3 px-4 py-3 border-b border-surface-border">
                  <Search className="w-5 h-5 text-ink-tertiary" />
                  <input
                    type="text"
                    placeholder="Type a command or search..."
                    className="flex-1 bg-transparent text-ink placeholder:text-ink-tertiary outline-none"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    autoFocus
                  />
                  <kbd className="px-2 py-0.5 bg-surface rounded text-xs text-ink-faint">ESC</kbd>
                </div>
                <div className="max-h-80 overflow-y-auto py-2">
                  {filteredCommands.map((cmd, idx) => (
                    <button
                      key={cmd.id}
                      onClick={() => executeCommand(cmd)}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-surface-hover transition-colors text-left"
                    >
                      <cmd.icon className="w-4 h-4 text-ink-tertiary" />
                      <span className="text-sm text-ink">{cmd.label}</span>
                    </button>
                  ))}
                  {filteredCommands.length === 0 && (
                    <div className="px-4 py-8 text-center text-ink-tertiary text-sm">
                      No commands found
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Toast Notifications */}
      <div className="fixed bottom-6 right-6 z-50 space-y-3">
        <AnimatePresence>
          {toasts.map((toast) => {
            const Icon = toastIcons[toast.type];
            return (
              <motion.div
                key={toast.id}
                initial={{ opacity: 0, x: 50, scale: 0.9 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 50, scale: 0.9 }}
                className={clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-lg border backdrop-blur-sm min-w-[280px]',
                  toastColors[toast.type]
                )}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm font-medium flex-1">{toast.message}</span>
                <button onClick={() => removeToast(toast.id)} className="p-1 hover:opacity-70">
                  <X className="w-4 h-4" />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
