import { useState } from 'react'
import { motion } from 'framer-motion'
import { Shield, AlertTriangle, DollarSign, Clock, BarChart2, Check, X } from 'lucide-react'
import { riskSettings } from '../data/mockData'
import { useApp } from '../App'
import clsx from 'clsx'

export default function Risk() {
  const { addToast } = useApp();
  const [settings, setSettings] = useState(riskSettings);
  const [hasChanges, setHasChanges] = useState(false);

  const updateSetting = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = () => {
    setHasChanges(false);
    addToast({ type: 'success', message: 'Risk settings saved successfully' });
  };

  const symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT', 'ADA/USDT', 'DOGE/USDT', 'DOT/USDT'];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Risk Controls</h1>
          <p className="text-ink-secondary text-sm mt-1">Configure trading limits and safety parameters</p>
        </div>
        {hasChanges && (
          <div className="flex items-center gap-3">
            <button onClick={() => setSettings(riskSettings)} className="btn-ghost">
              Discard
            </button>
            <button onClick={handleSave} className="btn-primary">
              Save Changes
            </button>
          </div>
        )}
      </div>

      {/* Warning Banner */}
      <div className="card p-4 border-warning/30 bg-warning-muted">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-ink">Proceed with caution</p>
            <p className="text-sm text-ink-secondary mt-1">
              Modifying risk controls can significantly impact your trading exposure.
              Ensure you understand the implications of any changes before saving.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Loss Limits */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-loss-muted rounded-lg">
              <Shield className="w-5 h-5 text-loss" />
            </div>
            <h2 className="font-semibold text-ink">Loss Limits</h2>
          </div>

          <div className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="label mb-0">Max Daily Loss</label>
                <span className="text-sm font-mono text-ink">${settings.maxDailyLoss}</span>
              </div>
              <input
                type="range"
                min="100"
                max="2000"
                step="100"
                value={settings.maxDailyLoss}
                onChange={(e) => updateSetting('maxDailyLoss', Number(e.target.value))}
                className="w-full h-2 bg-surface-border rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent"
              />
              <div className="flex justify-between text-xs text-ink-faint mt-1">
                <span>$100</span>
                <span>$2,000</span>
              </div>
            </div>

            <div className="p-4 bg-surface rounded-lg">
              <p className="text-sm text-ink-secondary">
                Trading will automatically pause if daily losses exceed this limit.
                Current daily P&L: <span className="text-profit font-mono">+$245.00</span>
              </p>
            </div>
          </div>
        </div>

        {/* Position Limits */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-accent-muted rounded-lg">
              <BarChart2 className="w-5 h-5 text-accent" />
            </div>
            <h2 className="font-semibold text-ink">Position Limits</h2>
          </div>

          <div className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="label mb-0">Max Position Size</label>
                <span className="text-sm font-mono text-ink">${settings.maxPositionSize}</span>
              </div>
              <input
                type="range"
                min="500"
                max="10000"
                step="500"
                value={settings.maxPositionSize}
                onChange={(e) => updateSetting('maxPositionSize', Number(e.target.value))}
                className="w-full h-2 bg-surface-border rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent"
              />
              <div className="flex justify-between text-xs text-ink-faint mt-1">
                <span>$500</span>
                <span>$10,000</span>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="label mb-0">Max Concurrent Positions</label>
                <span className="text-sm font-mono text-ink">{settings.maxPositions}</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={settings.maxPositions}
                onChange={(e) => updateSetting('maxPositions', Number(e.target.value))}
                className="w-full h-2 bg-surface-border rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent"
              />
              <div className="flex justify-between text-xs text-ink-faint mt-1">
                <span>1</span>
                <span>10</span>
              </div>
            </div>
          </div>
        </div>

        {/* Trading Hours */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-surface rounded-lg">
              <Clock className="w-5 h-5 text-ink-secondary" />
            </div>
            <h2 className="font-semibold text-ink">Trading Hours</h2>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Start Time</label>
                <input
                  type="time"
                  value={settings.tradingHoursStart}
                  onChange={(e) => updateSetting('tradingHoursStart', e.target.value)}
                  className="input"
                />
              </div>
              <div>
                <label className="label">End Time</label>
                <input
                  type="time"
                  value={settings.tradingHoursEnd}
                  onChange={(e) => updateSetting('tradingHoursEnd', e.target.value)}
                  className="input"
                />
              </div>
            </div>

            <div className="p-4 bg-surface rounded-lg">
              <p className="text-sm text-ink-secondary">
                Trading will only execute during these hours (UTC).
                Crypto markets are 24/7, but you can limit activity to specific periods.
              </p>
            </div>
          </div>
        </div>

        {/* Allowed Symbols */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-surface rounded-lg">
              <DollarSign className="w-5 h-5 text-ink-secondary" />
            </div>
            <h2 className="font-semibold text-ink">Allowed Symbols</h2>
          </div>

          <div className="space-y-3">
            {symbols.map((symbol) => {
              const isAllowed = settings.allowedSymbols.includes(symbol);
              return (
                <button
                  key={symbol}
                  onClick={() => {
                    const newSymbols = isAllowed
                      ? settings.allowedSymbols.filter(s => s !== symbol)
                      : [...settings.allowedSymbols, symbol];
                    updateSetting('allowedSymbols', newSymbols);
                  }}
                  className={clsx(
                    'w-full flex items-center justify-between px-4 py-3 rounded-lg transition-colors',
                    isAllowed ? 'bg-accent-muted border border-accent/30' : 'bg-surface hover:bg-surface-hover'
                  )}
                >
                  <span className={clsx('font-medium', isAllowed ? 'text-accent' : 'text-ink-secondary')}>
                    {symbol}
                  </span>
                  {isAllowed ? (
                    <Check className="w-4 h-4 text-accent" />
                  ) : (
                    <X className="w-4 h-4 text-ink-faint" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Paper Trading Toggle */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={clsx(
              'p-3 rounded-lg',
              settings.paperTrading ? 'bg-warning-muted' : 'bg-loss-muted'
            )}>
              <Shield className={clsx(
                'w-6 h-6',
                settings.paperTrading ? 'text-warning' : 'text-loss'
              )} />
            </div>
            <div>
              <h3 className="font-semibold text-ink">Paper Trading Mode</h3>
              <p className="text-sm text-ink-secondary mt-1">
                {settings.paperTrading
                  ? 'Trades are simulated. No real funds are used.'
                  : 'Live trading enabled. Real funds will be used!'}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              if (settings.paperTrading) {
                addToast({ type: 'warning', message: 'Switching to live trading requires additional confirmation' });
              } else {
                updateSetting('paperTrading', true);
                addToast({ type: 'info', message: 'Switched to paper trading mode' });
              }
            }}
            className={clsx(
              'relative w-14 h-7 rounded-full transition-colors',
              settings.paperTrading ? 'bg-warning' : 'bg-loss'
            )}
          >
            <div className={clsx(
              'absolute top-1 w-5 h-5 rounded-full bg-white transition-transform',
              settings.paperTrading ? 'left-1' : 'left-8'
            )} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}
