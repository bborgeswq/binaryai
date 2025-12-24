import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, Shield, Eye, EyeOff, CheckCircle2, AlertTriangle, ArrowRight, Loader2 } from 'lucide-react'
import clsx from 'clsx'

interface OnboardingProps {
  onComplete: () => void;
}

export default function Onboarding({ onComplete }: OnboardingProps) {
  const [step, setStep] = useState(1);
  const [showApiKey, setShowApiKey] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);
  const [accepted, setAccepted] = useState(false);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    // Simulate API test
    await new Promise(resolve => setTimeout(resolve, 1500));
    setTestResult('success');
    setTesting(false);
  };

  const handleComplete = () => {
    localStorage.setItem('vertex_api_key', apiKey);
    localStorage.setItem('vertex_api_secret', '••••••••');
    onComplete();
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-canvas via-canvas to-canvas-elevated" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-gradient-radial from-accent/10 via-transparent to-transparent opacity-50" />
      <div className="absolute inset-0 bg-grid-pattern opacity-30" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-md"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-accent to-teal-400 mb-4 glow-accent">
            <Zap className="w-8 h-8 text-canvas" />
          </div>
          <h1 className="text-3xl font-bold text-ink">Welcome to Vertex</h1>
          <p className="text-ink-secondary mt-2">AI-Powered Trading Platform</p>
        </div>

        {/* Progress */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={clsx(
                'h-1.5 rounded-full transition-all duration-300',
                s === step ? 'w-8 bg-accent' : s < step ? 'w-4 bg-accent/50' : 'w-4 bg-surface-border'
              )}
            />
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* Step 1: Paper Trading Notice */}
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="card p-6 space-y-6"
            >
              <div className="flex items-start gap-4 p-4 bg-warning-muted rounded-lg border border-warning/20">
                <AlertTriangle className="w-6 h-6 text-warning flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-ink mb-1">Paper Trading Only</h3>
                  <p className="text-sm text-ink-secondary">
                    This platform runs in paper trading mode by default. No real funds will be used.
                    All trades are simulated for learning and testing purposes.
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-profit flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-ink-secondary">Practice trading strategies risk-free</p>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-profit flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-ink-secondary">Test AI models before going live</p>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-profit flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-ink-secondary">Full backtest and analysis tools included</p>
                </div>
              </div>

              <button
                onClick={() => setStep(2)}
                className="btn-primary w-full py-3"
              >
                Continue <ArrowRight className="w-4 h-4" />
              </button>
            </motion.div>
          )}

          {/* Step 2: API Connection */}
          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="card p-6 space-y-6"
            >
              <div>
                <h2 className="text-lg font-semibold text-ink mb-1">Connect Exchange</h2>
                <p className="text-sm text-ink-secondary">Enter your Binance Testnet API credentials</p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="label">API Key</label>
                  <div className="relative">
                    <input
                      type={showApiKey ? 'text' : 'password'}
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Enter your API key"
                      className="input pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-tertiary hover:text-ink"
                    >
                      {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="label">API Secret</label>
                  <div className="relative">
                    <input
                      type={showSecret ? 'text' : 'password'}
                      value={apiSecret}
                      onChange={(e) => setApiSecret(e.target.value)}
                      placeholder="Enter your API secret"
                      className="input pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowSecret(!showSecret)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-tertiary hover:text-ink"
                    >
                      {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  onClick={handleTestConnection}
                  disabled={!apiKey || !apiSecret || testing}
                  className="btn-secondary w-full py-2.5"
                >
                  {testing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Testing Connection...
                    </>
                  ) : testResult === 'success' ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-profit" />
                      Connection Successful
                    </>
                  ) : (
                    'Test Connection'
                  )}
                </button>
              </div>

              <div className="flex gap-3">
                <button onClick={() => setStep(1)} className="btn-ghost flex-1">
                  Back
                </button>
                <button
                  onClick={() => setStep(3)}
                  disabled={testResult !== 'success'}
                  className="btn-primary flex-1"
                >
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}

          {/* Step 3: Risk Disclaimer */}
          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="card p-6 space-y-6"
            >
              <div className="flex items-start gap-4 p-4 bg-loss-muted rounded-lg border border-loss/20">
                <Shield className="w-6 h-6 text-loss flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-ink mb-1">Risk Disclaimer</h3>
                  <p className="text-sm text-ink-secondary">
                    Trading involves significant risk. Please read and acknowledge the following before proceeding.
                  </p>
                </div>
              </div>

              <div className="space-y-3 text-sm text-ink-secondary max-h-48 overflow-y-auto pr-2">
                <p>• Cryptocurrency trading is highly volatile and may result in significant losses.</p>
                <p>• Past performance of AI models does not guarantee future results.</p>
                <p>• Never invest more than you can afford to lose.</p>
                <p>• This platform is provided "as-is" without any warranties.</p>
                <p>• You are solely responsible for your trading decisions.</p>
                <p>• We recommend starting with paper trading to understand the system.</p>
              </div>

              <label className="flex items-start gap-3 cursor-pointer group">
                <div className="relative mt-0.5">
                  <input
                    type="checkbox"
                    checked={accepted}
                    onChange={(e) => setAccepted(e.target.checked)}
                    className="sr-only"
                  />
                  <div className={clsx(
                    'w-5 h-5 rounded border-2 transition-all',
                    accepted
                      ? 'bg-accent border-accent'
                      : 'border-surface-border group-hover:border-ink-tertiary'
                  )}>
                    {accepted && <CheckCircle2 className="w-4 h-4 text-canvas" />}
                  </div>
                </div>
                <span className="text-sm text-ink-secondary">
                  I understand the risks involved and accept full responsibility for my trading activities.
                </span>
              </label>

              <div className="flex gap-3">
                <button onClick={() => setStep(2)} className="btn-ghost flex-1">
                  Back
                </button>
                <button
                  onClick={handleComplete}
                  disabled={!accepted}
                  className="btn-primary flex-1"
                >
                  Get Started <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
