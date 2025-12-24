import { useState } from 'react'
import { motion } from 'framer-motion'
import { Moon, Sun, Bell, BellOff, Volume2, VolumeX, Keyboard, Eye, EyeOff, Trash2, LogOut, ExternalLink } from 'lucide-react'
import { useApp } from '../App'
import clsx from 'clsx'

const shortcuts = [
  { key: 'Cmd/Ctrl + K', action: 'Open command palette' },
  { key: 'Cmd/Ctrl + /', action: 'Toggle sidebar' },
  { key: 'Escape', action: 'Close modal/palette' },
  { key: 'G then D', action: 'Go to Dashboard' },
  { key: 'G then T', action: 'Go to Trading' },
  { key: 'G then S', action: 'Go to Strategy' },
  { key: 'Space', action: 'Pause/Resume agent' },
];

export default function Settings() {
  const { addToast } = useApp();
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [notifications, setNotifications] = useState(true);
  const [sounds, setSounds] = useState(true);
  const [showApiKey, setShowApiKey] = useState(false);
  const apiKey = localStorage.getItem('vertex_api_key') || '';

  const handleClearData = () => {
    if (confirm('This will clear all local data including settings and API keys. Continue?')) {
      localStorage.clear();
      addToast({ type: 'warning', message: 'All local data cleared' });
      window.location.reload();
    }
  };

  const handleDisconnect = () => {
    if (confirm('Disconnect from exchange? This will stop all trading activity.')) {
      localStorage.removeItem('vertex_onboarded');
      localStorage.removeItem('vertex_api_key');
      localStorage.removeItem('vertex_api_secret');
      addToast({ type: 'info', message: 'Disconnected from exchange' });
      window.location.reload();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6 max-w-4xl"
    >
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-ink">Settings</h1>
        <p className="text-ink-secondary text-sm mt-1">Customize your trading experience</p>
      </div>

      {/* Appearance */}
      <div className="card p-6">
        <h2 className="font-semibold text-ink mb-6">Appearance</h2>
        <div className="space-y-6">
          {/* Theme */}
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-ink">Theme</p>
              <p className="text-sm text-ink-secondary mt-0.5">Choose your preferred color scheme</p>
            </div>
            <div className="flex items-center gap-2 p-1 bg-surface rounded-lg">
              <button
                onClick={() => setTheme('dark')}
                className={clsx(
                  'flex items-center gap-2 px-4 py-2 rounded-md transition-colors',
                  theme === 'dark' ? 'bg-accent text-canvas' : 'text-ink-secondary hover:text-ink'
                )}
              >
                <Moon className="w-4 h-4" />
                Dark
              </button>
              <button
                onClick={() => {
                  setTheme('light');
                  addToast({ type: 'info', message: 'Light theme coming soon' });
                }}
                className={clsx(
                  'flex items-center gap-2 px-4 py-2 rounded-md transition-colors',
                  theme === 'light' ? 'bg-accent text-canvas' : 'text-ink-secondary hover:text-ink'
                )}
              >
                <Sun className="w-4 h-4" />
                Light
              </button>
            </div>
          </div>

          {/* Typography Preview */}
          <div className="p-4 bg-surface rounded-lg">
            <p className="text-xs text-ink-faint uppercase tracking-wider mb-3">Typography Preview</p>
            <div className="space-y-2">
              <p className="text-2xl font-bold text-ink">Space Grotesk Display</p>
              <p className="font-mono text-ink-secondary">JetBrains Mono: $97,245.32 +2.25%</p>
              <p className="text-sm text-ink-tertiary">Body text for descriptions and explanations</p>
            </div>
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="card p-6">
        <h2 className="font-semibold text-ink mb-6">Notifications</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {notifications ? <Bell className="w-5 h-5 text-ink-secondary" /> : <BellOff className="w-5 h-5 text-ink-tertiary" />}
              <div>
                <p className="font-medium text-ink">Push Notifications</p>
                <p className="text-sm text-ink-secondary">Get notified about trades and signals</p>
              </div>
            </div>
            <button
              onClick={() => setNotifications(!notifications)}
              className={clsx(
                'relative w-12 h-6 rounded-full transition-colors',
                notifications ? 'bg-accent' : 'bg-surface-border'
              )}
            >
              <div className={clsx(
                'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
                notifications ? 'left-7' : 'left-1'
              )} />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {sounds ? <Volume2 className="w-5 h-5 text-ink-secondary" /> : <VolumeX className="w-5 h-5 text-ink-tertiary" />}
              <div>
                <p className="font-medium text-ink">Sound Effects</p>
                <p className="text-sm text-ink-secondary">Audio feedback for actions</p>
              </div>
            </div>
            <button
              onClick={() => setSounds(!sounds)}
              className={clsx(
                'relative w-12 h-6 rounded-full transition-colors',
                sounds ? 'bg-accent' : 'bg-surface-border'
              )}
            >
              <div className={clsx(
                'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
                sounds ? 'left-7' : 'left-1'
              )} />
            </button>
          </div>
        </div>
      </div>

      {/* Keyboard Shortcuts */}
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-6">
          <Keyboard className="w-5 h-5 text-ink-secondary" />
          <h2 className="font-semibold text-ink">Keyboard Shortcuts</h2>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {shortcuts.map((shortcut, idx) => (
            <div key={idx} className="flex items-center justify-between p-3 bg-surface rounded-lg">
              <span className="text-sm text-ink-secondary">{shortcut.action}</span>
              <kbd className="px-2 py-1 bg-canvas rounded text-xs font-mono text-ink-faint">
                {shortcut.key}
              </kbd>
            </div>
          ))}
        </div>
      </div>

      {/* API Connection */}
      <div className="card p-6">
        <h2 className="font-semibold text-ink mb-6">API Connection</h2>
        <div className="space-y-4">
          <div>
            <label className="label">API Key</label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={apiKey || '••••••••••••••••'}
                readOnly
                className="input pr-10 bg-surface"
              />
              <button
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-tertiary hover:text-ink"
              >
                {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-2 bg-profit-muted rounded-lg">
              <div className="w-2 h-2 rounded-full bg-profit" />
              <span className="text-sm text-profit font-medium">Connected to Binance Testnet</span>
            </div>
            <button
              onClick={handleDisconnect}
              className="btn-ghost text-loss"
            >
              <LogOut className="w-4 h-4" />
              Disconnect
            </button>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="card p-6 border-loss/30">
        <h2 className="font-semibold text-loss mb-4">Danger Zone</h2>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-ink">Clear All Local Data</p>
            <p className="text-sm text-ink-secondary mt-0.5">
              Remove all settings, API keys, and cached data
            </p>
          </div>
          <button
            onClick={handleClearData}
            className="btn-danger"
          >
            <Trash2 className="w-4 h-4" />
            Clear Data
          </button>
        </div>
      </div>

      {/* About */}
      <div className="card p-6">
        <h2 className="font-semibold text-ink mb-4">About</h2>
        <div className="space-y-3 text-sm text-ink-secondary">
          <div className="flex items-center justify-between">
            <span>Version</span>
            <span className="font-mono text-ink">1.0.0</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Build</span>
            <span className="font-mono text-ink">2024.12.24</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Documentation</span>
            <a href="#" className="text-accent hover:underline flex items-center gap-1">
              View Docs <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
