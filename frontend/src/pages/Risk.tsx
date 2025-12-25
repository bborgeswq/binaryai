import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Shield, AlertTriangle, TrendingUp, Activity, Percent, Target, CheckCircle2 } from 'lucide-react'
import clsx from 'clsx'

interface RiskConfig {
  risk_per_trade: number;
  min_rr: number;
  max_positions: number;
  symbols: string[];
  paper_trading: boolean;
}

export default function Risk() {
  const [config, setConfig] = useState<RiskConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRiskConfig = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/strategy/status');
        const data = await response.json();

        if (data.status) {
          setConfig({
            risk_per_trade: data.status.risk_per_trade || 0.07,
            min_rr: data.status.min_rr || 2,
            max_positions: 3,
            symbols: data.status.symbols || ['BTC/USDT', 'ETH/USDT', 'XRP/USDT'],
            paper_trading: true // Binance testnet = paper trading
          });
        }
        setLoading(false);
      } catch (err) {
        setError('Could not connect to trading server');
        setLoading(false);
      }
    };

    fetchRiskConfig();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Activity className="w-6 h-6 text-accent animate-spin" />
        <span className="ml-3 text-ink-secondary">Loading risk configuration...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <AlertTriangle className="w-10 h-10 text-loss mb-4" />
        <p className="text-ink-secondary">{error}</p>
        <p className="text-ink-faint text-sm mt-2">Make sure the API server is running on port 8000</p>
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
      <div>
        <h1 className="text-2xl font-bold text-ink">Risk Controls</h1>
        <p className="text-ink-secondary text-sm mt-1">TJR Liquidity Sweep Strategy - Risk Management</p>
      </div>

      {/* Testnet Notice */}
      <div className="card p-4 border-warning/30 bg-warning-muted">
        <div className="flex items-start gap-3">
          <Shield className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-ink">Binance Testnet Mode</p>
            <p className="text-sm text-ink-secondary mt-1">
              All trades are simulated using Binance Testnet. No real funds are at risk.
              Configure your testnet API keys in the .env file.
            </p>
          </div>
        </div>
      </div>

      {/* Risk Parameters Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Risk Per Trade */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-loss-muted rounded-lg">
              <Percent className="w-5 h-5 text-loss" />
            </div>
            <h2 className="font-semibold text-ink">Risk Per Trade</h2>
          </div>
          <p className="text-3xl font-bold text-ink mb-2">
            {((config?.risk_per_trade || 0.07) * 100).toFixed(0)}%
          </p>
          <p className="text-sm text-ink-secondary">
            Maximum percentage of account balance risked on each trade.
            Stop loss is calculated to limit loss to this amount.
          </p>
        </div>

        {/* Minimum Risk:Reward */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-profit-muted rounded-lg">
              <Target className="w-5 h-5 text-profit" />
            </div>
            <h2 className="font-semibold text-ink">Minimum R:R</h2>
          </div>
          <p className="text-3xl font-bold text-ink mb-2">
            {config?.min_rr || 2}:1
          </p>
          <p className="text-sm text-ink-secondary">
            Minimum risk-to-reward ratio required before entering a trade.
            Trades with lower R:R are rejected by the strategy.
          </p>
        </div>

        {/* Max Concurrent Positions */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-accent-muted rounded-lg">
              <TrendingUp className="w-5 h-5 text-accent" />
            </div>
            <h2 className="font-semibold text-ink">Max Positions</h2>
          </div>
          <p className="text-3xl font-bold text-ink mb-2">
            {config?.max_positions || 3}
          </p>
          <p className="text-sm text-ink-secondary">
            Maximum number of concurrent open positions allowed.
            New trades are blocked if this limit is reached.
          </p>
        </div>
      </div>

      {/* Tracked Symbols */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">Allowed Trading Pairs</h2>
        <div className="grid grid-cols-3 gap-4">
          {(config?.symbols || ['BTC/USDT', 'ETH/USDT', 'XRP/USDT']).map((symbol) => (
            <div
              key={symbol}
              className="flex items-center justify-between p-4 bg-accent-muted rounded-lg border border-accent/30"
            >
              <span className="font-medium text-accent">{symbol}</span>
              <CheckCircle2 className="w-5 h-5 text-accent" />
            </div>
          ))}
        </div>
        <p className="text-sm text-ink-faint mt-4">
          These symbols are actively monitored by the TJR Liquidity Sweep strategy.
        </p>
      </div>

      {/* Strategy Risk Rules */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">TJR Strategy Risk Rules</h2>
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-profit-muted flex items-center justify-center text-profit font-semibold text-sm">1</div>
              <div>
                <p className="font-medium text-ink">Stop Loss Placement</p>
                <p className="text-sm text-ink-secondary">Always placed below the liquidity sweep low (for longs) or above the sweep high (for shorts)</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-profit-muted flex items-center justify-center text-profit font-semibold text-sm">2</div>
              <div>
                <p className="font-medium text-ink">Take Profit Target</p>
                <p className="text-sm text-ink-secondary">Targets opposite liquidity zone where price is expected to reach</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-profit-muted flex items-center justify-center text-profit font-semibold text-sm">3</div>
              <div>
                <p className="font-medium text-ink">Position Sizing</p>
                <p className="text-sm text-ink-secondary">Calculated based on 7% risk and distance to stop loss</p>
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-warning-muted flex items-center justify-center text-warning font-semibold text-sm">4</div>
              <div>
                <p className="font-medium text-ink">Confluence Required</p>
                <p className="text-sm text-ink-secondary">Must have Break of Structure + Order Block/FVG confirmation</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-warning-muted flex items-center justify-center text-warning font-semibold text-sm">5</div>
              <div>
                <p className="font-medium text-ink">Multi-Timeframe Alignment</p>
                <p className="text-sm text-ink-secondary">Higher timeframe bias must align with lower timeframe entry</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-warning-muted flex items-center justify-center text-warning font-semibold text-sm">6</div>
              <div>
                <p className="font-medium text-ink">No Entries During High Volatility</p>
                <p className="text-sm text-ink-secondary">Avoids trading during major news events or extreme moves</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Trading Mode Status */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-warning-muted">
              <Shield className="w-6 h-6 text-warning" />
            </div>
            <div>
              <h3 className="font-semibold text-ink">Paper Trading Mode</h3>
              <p className="text-sm text-ink-secondary mt-1">
                Using Binance Testnet - trades are simulated, no real funds are used.
              </p>
            </div>
          </div>
          <div className="px-4 py-2 bg-warning-muted rounded-lg">
            <span className="text-warning font-medium">TESTNET ACTIVE</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
