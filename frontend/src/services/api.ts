/**
 * API Service for connecting to the Python trading backend
 * Replaces all mock data with real API calls
 */

const API_BASE = 'http://localhost:8000';

export interface ConnectionStatus {
  connected: boolean;
  exchange: string;
  testnet: boolean;
  message: string;
}

export interface AccountInfo {
  equity: number;
  available_balance: number;
  currency: string;
  positions_count: number;
}

export interface MarketData {
  symbol: string;
  price: number;
  change_24h: number;
  change_percent: number;
  high_24h: number;
  low_24h: number;
  volume_24h: number;
  timestamp: string;
}

export interface Position {
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
}

export interface TradeRecord {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  exit_price: number | null;
  pnl: number | null;
  status: string;
  strategy: string;
  entry_time: string;
  exit_time: string | null;
}

export interface AgentStatus {
  running: boolean;
  strategy: string;
  symbols: string[];
  risk_percent: number;
  last_signal: {
    symbol: string;
    signal: string;
    entry: number;
    stop_loss: number;
    take_profit: number;
    confidence: number;
  } | null;
}

export interface Signal {
  symbol: string;
  signal: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  risk_reward: number;
  confidence: number;
  reasoning: string;
  setup_type: string;
}

export interface Activity {
  type: string;
  symbol: string;
  title: string;
  description: string;
  timestamp: string;
}

export interface Stats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  period_days: number;
}

export interface LiquidityZone {
  price_low: number;
  price_high: number;
  type: string;
  strength: number;
  swept: boolean;
}

export interface OrderBlock {
  high: number;
  low: number;
  type: string;
  strength: number;
  mitigated: boolean;
}

export interface Candle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

class TradingAPI {
  private baseUrl: string;
  private ws: WebSocket | null = null;
  private priceCallbacks: ((prices: Record<string, { price: number; change: number }>) => void)[] = [];

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Connection status
  async getStatus(): Promise<ConnectionStatus> {
    return this.fetch<ConnectionStatus>('/api/status');
  }

  // Account
  async getAccount(): Promise<AccountInfo> {
    return this.fetch<AccountInfo>('/api/account');
  }

  // Market data
  async getMarketData(symbol: string): Promise<MarketData> {
    return this.fetch<MarketData>(`/api/market/${symbol}`);
  }

  async getAllPrices(): Promise<{ prices: Record<string, MarketData>; timestamp: string }> {
    return this.fetch('/api/market/prices');
  }

  async getOHLCV(symbol: string, timeframe: string = '1h', limit: number = 100): Promise<{ candles: Candle[]; symbol: string; timeframe: string }> {
    return this.fetch(`/api/ohlcv/${symbol}?timeframe=${timeframe}&limit=${limit}`);
  }

  // Positions
  async getPositions(): Promise<Position[]> {
    return this.fetch<Position[]>('/api/positions');
  }

  // Trades
  async getTrades(limit: number = 20): Promise<TradeRecord[]> {
    return this.fetch<TradeRecord[]>(`/api/trades?limit=${limit}`);
  }

  // Stats
  async getStats(): Promise<Stats> {
    return this.fetch<Stats>('/api/stats');
  }

  // Agent control
  async getAgentStatus(): Promise<AgentStatus> {
    return this.fetch<AgentStatus>('/api/agent/status');
  }

  async startAgent(): Promise<{ message: string; status: string }> {
    return this.fetch('/api/agent/start', { method: 'POST' });
  }

  async stopAgent(): Promise<{ message: string; status: string }> {
    return this.fetch('/api/agent/stop', { method: 'POST' });
  }

  // Signals
  async getCurrentSignals(): Promise<{ signals: Signal[]; timestamp: string }> {
    return this.fetch('/api/signals/current');
  }

  // Activity
  async getActivity(): Promise<{ activities: Activity[] }> {
    return this.fetch('/api/activity');
  }

  // Strategy info
  async getStrategyStatus(): Promise<{ status: Record<string, unknown>; timestamp: string }> {
    return this.fetch('/api/strategy/status');
  }

  async getLiquidityZones(symbol: string): Promise<{
    symbol: string;
    liquidity_zones: LiquidityZone[];
    order_blocks: OrderBlock[];
    fair_value_gaps: { high: number; low: number; type: string; filled: boolean }[];
    timestamp: string;
  }> {
    return this.fetch(`/api/strategy/zones/${symbol}`);
  }

  // WebSocket for real-time prices
  connectPriceStream(onPrice: (prices: Record<string, { price: number; change: number }>) => void): void {
    if (this.ws) {
      this.ws.close();
    }

    this.priceCallbacks.push(onPrice);

    this.ws = new WebSocket(`ws://localhost:8000/ws/prices`);

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'prices') {
          this.priceCallbacks.forEach(cb => cb(data.data));
        }
      } catch (e) {
        console.error('WebSocket parse error:', e);
      }
    };

    this.ws.onclose = () => {
      // Reconnect after 5 seconds
      setTimeout(() => {
        if (this.priceCallbacks.length > 0) {
          this.connectPriceStream(this.priceCallbacks[this.priceCallbacks.length - 1]);
        }
      }, 5000);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  disconnectPriceStream(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.priceCallbacks = [];
  }
}

// Export singleton instance
export const api = new TradingAPI();

// Export types for use in components
export type { TradingAPI };
