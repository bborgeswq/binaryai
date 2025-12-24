import { useState } from 'react'
import { motion } from 'framer-motion'
import { Brain, Cpu, Activity, TrendingUp, TrendingDown, Sparkles, ChevronDown, ChevronUp, Check } from 'lucide-react'
import { models } from '../data/mockData'
import { useApp } from '../App'
import clsx from 'clsx'

// Mock features for explainability
const modelFeatures = {
  'momentum-v3': [
    { name: 'RSI (14)', importance: 0.28, value: 32.5, signal: 'bullish' },
    { name: 'MACD Histogram', importance: 0.24, value: 145.2, signal: 'bullish' },
    { name: 'EMA 9/21 Cross', importance: 0.18, value: 'Above', signal: 'bullish' },
    { name: 'Volume Profile', importance: 0.15, value: '1.4x avg', signal: 'neutral' },
    { name: 'Bollinger %B', importance: 0.10, value: 0.72, signal: 'neutral' },
    { name: 'ATR (14)', importance: 0.05, value: 2450, signal: 'neutral' },
  ],
  'meanrevert-v2': [
    { name: 'Z-Score', importance: 0.32, value: -1.8, signal: 'bullish' },
    { name: 'Bollinger %B', importance: 0.25, value: 0.12, signal: 'bullish' },
    { name: 'RSI (7)', importance: 0.20, value: 28.5, signal: 'bullish' },
    { name: 'Volume Delta', importance: 0.13, value: -0.3, signal: 'bearish' },
    { name: 'Price Distance', importance: 0.10, value: '-2.4%', signal: 'bullish' },
  ],
  'hybrid': [
    { name: 'Momentum Score', importance: 0.35, value: 0.72, signal: 'bullish' },
    { name: 'Reversion Score', importance: 0.30, value: 0.45, signal: 'neutral' },
    { name: 'ML Confidence', importance: 0.20, value: 0.78, signal: 'bullish' },
    { name: 'Regime Filter', importance: 0.15, value: 'Trending', signal: 'bullish' },
  ],
};

const confidenceHistory = [
  { time: '12:00', confidence: 0.65 },
  { time: '12:15', confidence: 0.72 },
  { time: '12:30', confidence: 0.68 },
  { time: '12:45', confidence: 0.78 },
  { time: '13:00', confidence: 0.75 },
  { time: '13:15', confidence: 0.82 },
];

export default function Models() {
  const { addToast } = useApp();
  const [activeModel, setActiveModel] = useState('momentum-v3');
  const [expandedModel, setExpandedModel] = useState<string | null>('momentum-v3');

  const handleActivateModel = (id: string) => {
    setActiveModel(id);
    addToast({ type: 'success', message: `Switched to ${models.find(m => m.id === id)?.name}` });
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
          <h1 className="text-2xl font-bold text-ink">AI Models</h1>
          <p className="text-ink-secondary text-sm mt-1">Manage and understand your trading models</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Model Selector */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-ink-secondary uppercase tracking-wider">Available Models</h3>
          {models.map((model) => (
            <div key={model.id} className="card overflow-hidden">
              <button
                onClick={() => setExpandedModel(expandedModel === model.id ? null : model.id)}
                className="w-full p-4 flex items-center justify-between text-left"
              >
                <div className="flex items-center gap-3">
                  <div className={clsx(
                    'p-2 rounded-lg',
                    activeModel === model.id ? 'bg-accent-muted' : 'bg-surface'
                  )}>
                    <Brain className={clsx(
                      'w-5 h-5',
                      activeModel === model.id ? 'text-accent' : 'text-ink-tertiary'
                    )} />
                  </div>
                  <div>
                    <p className="font-medium text-ink">{model.name}</p>
                    <p className="text-xs text-ink-tertiary mt-0.5">Accuracy: {model.accuracy}%</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {activeModel === model.id && (
                    <span className="badge-accent">Active</span>
                  )}
                  {expandedModel === model.id ? (
                    <ChevronUp className="w-4 h-4 text-ink-tertiary" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-ink-tertiary" />
                  )}
                </div>
              </button>

              {expandedModel === model.id && (
                <div className="px-4 pb-4 pt-2 border-t border-surface-border">
                  <p className="text-sm text-ink-secondary mb-4">{model.description}</p>
                  {activeModel !== model.id && (
                    <button
                      onClick={() => handleActivateModel(model.id)}
                      className="btn-primary w-full"
                    >
                      <Check className="w-4 h-4" />
                      Activate Model
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Explainability Panel */}
        <div className="col-span-2 space-y-6">
          {/* Current Signal */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-accent-muted rounded-lg">
                  <Cpu className="w-5 h-5 text-accent" />
                </div>
                <div>
                  <h3 className="font-semibold text-ink">
                    {models.find(m => m.id === activeModel)?.name}
                  </h3>
                  <p className="text-xs text-ink-tertiary">Current signal for BTC/USDT</p>
                </div>
              </div>
              <div className="text-right">
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-profit">BUY</span>
                  <TrendingUp className="w-6 h-6 text-profit" />
                </div>
                <p className="text-sm text-ink-secondary">78% confidence</p>
              </div>
            </div>

            {/* Confidence Meter */}
            <div className="mb-6">
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-ink-secondary">Model Confidence</span>
                <span className="font-mono text-ink">78%</span>
              </div>
              <div className="h-3 bg-surface-border rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-accent to-teal-400 rounded-full transition-all duration-500"
                  style={{ width: '78%' }}
                />
              </div>
              <div className="flex justify-between text-xs text-ink-faint mt-1">
                <span>Low</span>
                <span>Medium</span>
                <span>High</span>
              </div>
            </div>

            {/* What Changed */}
            <div className="p-4 bg-surface/50 rounded-lg">
              <div className="flex items-start gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
                <p className="text-sm text-ink">
                  <span className="font-medium">Recent signal change:</span> RSI crossed below 30 (oversold) while MACD histogram turned positive, indicating potential reversal.
                </p>
              </div>
            </div>
          </div>

          {/* Feature Importance */}
          <div className="card p-6">
            <h3 className="font-semibold text-ink mb-6">Feature Importance & Values</h3>
            <div className="space-y-4">
              {(modelFeatures[activeModel as keyof typeof modelFeatures] || []).map((feature, idx) => (
                <div key={idx} className="flex items-center gap-4">
                  <div className="w-32 text-sm text-ink-secondary">{feature.name}</div>
                  <div className="flex-1">
                    <div className="h-2 bg-surface-border rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent rounded-full"
                        style={{ width: `${feature.importance * 100}%` }}
                      />
                    </div>
                  </div>
                  <div className="w-20 text-sm font-mono text-ink text-right">
                    {typeof feature.value === 'number' ? feature.value.toFixed(1) : feature.value}
                  </div>
                  <div className={clsx(
                    'w-16 text-xs font-medium text-right',
                    feature.signal === 'bullish' && 'text-profit',
                    feature.signal === 'bearish' && 'text-loss',
                    feature.signal === 'neutral' && 'text-ink-tertiary'
                  )}>
                    {feature.signal}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Model Stats */}
          <div className="grid grid-cols-4 gap-4">
            <div className="card p-4">
              <p className="stat-label">Signals Today</p>
              <p className="stat-value text-ink">24</p>
            </div>
            <div className="card p-4">
              <p className="stat-label">Accuracy (7d)</p>
              <p className="stat-value text-profit">68%</p>
            </div>
            <div className="card p-4">
              <p className="stat-label">Avg Confidence</p>
              <p className="stat-value text-ink">72%</p>
            </div>
            <div className="card p-4">
              <p className="stat-label">Last Update</p>
              <p className="stat-value text-ink text-lg">2m ago</p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
