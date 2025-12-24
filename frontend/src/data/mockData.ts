// Mock data for the trading dashboard

export interface WatchlistItem {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: string;
  marketCap: string;
  signal?: 'buy' | 'sell' | 'hold';
  confidence?: number;
}

export interface Position {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
  openTime: string;
}

export interface Order {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit' | 'stop';
  quantity: number;
  price: number;
  status: 'pending' | 'filled' | 'cancelled';
  time: string;
}

export interface Trade {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
  pnl: number;
  time: string;
  strategy: string;
}

export interface BacktestRun {
  id: string;
  name: string;
  strategy: string;
  period: string;
  returns: number;
  sharpe: number;
  maxDrawdown: number;
  winRate: number;
  trades: number;
  status: 'completed' | 'running' | 'failed';
  createdAt: string;
}

export interface LogEntry {
  id: string;
  type: 'signal' | 'order' | 'fill' | 'error' | 'system';
  message: string;
  details?: string;
  timestamp: string;
}

export interface EquityPoint {
  date: string;
  value: number;
  benchmark?: number;
}

export const watchlist: WatchlistItem[] = [
  { symbol: 'BTC/USDT', name: 'Bitcoin', price: 97245.32, change: 2145.67, changePercent: 2.25, volume: '24.5B', marketCap: '1.9T', signal: 'buy', confidence: 0.78 },
  { symbol: 'ETH/USDT', name: 'Ethereum', price: 3456.78, change: -45.23, changePercent: -1.29, volume: '12.3B', marketCap: '415B', signal: 'hold', confidence: 0.52 },
  { symbol: 'SOL/USDT', name: 'Solana', price: 198.45, change: 12.34, changePercent: 6.63, volume: '4.2B', marketCap: '86B', signal: 'buy', confidence: 0.85 },
  { symbol: 'XRP/USDT', name: 'Ripple', price: 2.34, change: 0.08, changePercent: 3.54, volume: '2.1B', marketCap: '128B' },
  { symbol: 'BNB/USDT', name: 'BNB', price: 645.23, change: -12.45, changePercent: -1.89, volume: '1.8B', marketCap: '96B', signal: 'sell', confidence: 0.67 },
  { symbol: 'ADA/USDT', name: 'Cardano', price: 0.98, change: 0.04, changePercent: 4.26, volume: '890M', marketCap: '34B' },
];

export const positions: Position[] = [
  { id: '1', symbol: 'BTC/USDT', side: 'long', quantity: 0.5, entryPrice: 94500, currentPrice: 97245.32, pnl: 1372.66, pnlPercent: 2.90, openTime: '2024-12-23 14:30' },
  { id: '2', symbol: 'SOL/USDT', side: 'long', quantity: 25, entryPrice: 185.20, currentPrice: 198.45, pnl: 331.25, pnlPercent: 7.16, openTime: '2024-12-24 09:15' },
  { id: '3', symbol: 'ETH/USDT', side: 'short', quantity: 2, entryPrice: 3520.00, currentPrice: 3456.78, pnl: 126.44, pnlPercent: 1.80, openTime: '2024-12-24 11:45' },
];

export const recentOrders: Order[] = [
  { id: '1', symbol: 'BTC/USDT', side: 'buy', type: 'limit', quantity: 0.25, price: 96000, status: 'pending', time: '12:45:23' },
  { id: '2', symbol: 'ETH/USDT', side: 'sell', type: 'market', quantity: 1.5, price: 3456.78, status: 'filled', time: '12:42:15' },
  { id: '3', symbol: 'SOL/USDT', side: 'buy', type: 'stop', quantity: 10, price: 195.00, status: 'pending', time: '12:30:00' },
];

export const recentTrades: Trade[] = [
  { id: '1', symbol: 'BTC/USDT', side: 'sell', quantity: 0.3, price: 97100, pnl: 423.50, time: '11:23:45', strategy: 'Momentum v3' },
  { id: '2', symbol: 'ETH/USDT', side: 'buy', quantity: 2.0, price: 3480.25, pnl: -48.50, time: '10:15:30', strategy: 'MeanRevert v2' },
  { id: '3', symbol: 'SOL/USDT', side: 'sell', quantity: 15, price: 196.80, pnl: 178.50, time: '09:45:12', strategy: 'Momentum v3' },
  { id: '4', symbol: 'BNB/USDT', side: 'buy', quantity: 5, price: 650.00, pnl: -23.85, time: '09:12:00', strategy: 'Hybrid' },
];

export const backtestRuns: BacktestRun[] = [
  { id: '1', name: 'Momentum BTC Q4', strategy: 'Momentum v3', period: 'Oct - Dec 2024', returns: 34.5, sharpe: 2.1, maxDrawdown: -8.2, winRate: 62, trades: 145, status: 'completed', createdAt: '2024-12-20' },
  { id: '2', name: 'Mean Revert ETH', strategy: 'MeanRevert v2', period: 'Nov - Dec 2024', returns: 18.3, sharpe: 1.6, maxDrawdown: -12.4, winRate: 58, trades: 89, status: 'completed', createdAt: '2024-12-21' },
  { id: '3', name: 'Hybrid Multi-Asset', strategy: 'Hybrid', period: 'Dec 2024', returns: 0, sharpe: 0, maxDrawdown: 0, winRate: 0, trades: 0, status: 'running', createdAt: '2024-12-24' },
];

export const logs: LogEntry[] = [
  { id: '1', type: 'signal', message: 'BUY signal generated for BTC/USDT', details: 'Confidence: 78%, RSI: 32, MACD bullish crossover', timestamp: '12:45:23' },
  { id: '2', type: 'order', message: 'Limit order placed: BTC/USDT', details: 'Buy 0.25 @ $96,000', timestamp: '12:45:24' },
  { id: '3', type: 'fill', message: 'Order filled: ETH/USDT', details: 'Sold 1.5 @ $3,456.78', timestamp: '12:42:15' },
  { id: '4', type: 'signal', message: 'HOLD signal for ETH/USDT', details: 'Confidence: 52%, Mixed indicators', timestamp: '12:40:00' },
  { id: '5', type: 'system', message: 'Model updated: Momentum v3', details: 'New weights deployed', timestamp: '12:30:00' },
  { id: '6', type: 'error', message: 'Connection timeout', details: 'Reconnecting to Binance...', timestamp: '12:25:45' },
  { id: '7', type: 'system', message: 'Connection restored', timestamp: '12:25:48' },
];

export const equityHistory: EquityPoint[] = [
  { date: '2024-12-01', value: 10000, benchmark: 10000 },
  { date: '2024-12-02', value: 10250, benchmark: 10120 },
  { date: '2024-12-03', value: 10180, benchmark: 10080 },
  { date: '2024-12-04', value: 10420, benchmark: 10200 },
  { date: '2024-12-05', value: 10650, benchmark: 10150 },
  { date: '2024-12-06', value: 10580, benchmark: 10280 },
  { date: '2024-12-07', value: 10890, benchmark: 10350 },
  { date: '2024-12-08', value: 11200, benchmark: 10420 },
  { date: '2024-12-09', value: 11050, benchmark: 10380 },
  { date: '2024-12-10', value: 11320, benchmark: 10500 },
  { date: '2024-12-11', value: 11580, benchmark: 10620 },
  { date: '2024-12-12', value: 11420, benchmark: 10550 },
  { date: '2024-12-13', value: 11780, benchmark: 10680 },
  { date: '2024-12-14', value: 12100, benchmark: 10750 },
  { date: '2024-12-15', value: 12350, benchmark: 10820 },
  { date: '2024-12-16', value: 12180, benchmark: 10780 },
  { date: '2024-12-17', value: 12450, benchmark: 10900 },
  { date: '2024-12-18', value: 12720, benchmark: 10980 },
  { date: '2024-12-19', value: 12580, benchmark: 10920 },
  { date: '2024-12-20', value: 12890, benchmark: 11050 },
  { date: '2024-12-21', value: 13150, benchmark: 11120 },
  { date: '2024-12-22', value: 13420, benchmark: 11200 },
  { date: '2024-12-23', value: 13280, benchmark: 11150 },
  { date: '2024-12-24', value: 13650, benchmark: 11280 },
];

export const models = [
  { id: 'momentum-v3', name: 'Momentum v3', description: 'Trend-following strategy using RSI, MACD, and EMA crossovers', accuracy: 68, active: true },
  { id: 'meanrevert-v2', name: 'MeanRevert v2', description: 'Mean reversion strategy targeting oversold/overbought conditions', accuracy: 62, active: false },
  { id: 'hybrid', name: 'Hybrid', description: 'Combines momentum and mean reversion signals with ML weighting', accuracy: 71, active: false },
];

export const riskSettings = {
  maxDailyLoss: 500,
  maxPositionSize: 2000,
  maxPositions: 5,
  allowedSymbols: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT'],
  tradingHoursStart: '09:00',
  tradingHoursEnd: '17:00',
  paperTrading: true,
};

// Simulated price updates
export function generatePriceUpdate(currentPrice: number): number {
  const change = (Math.random() - 0.5) * currentPrice * 0.002;
  return Math.round((currentPrice + change) * 100) / 100;
}

// Generate OHLC candle data
export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export function generateCandleData(basePrice: number, count: number): Candle[] {
  const candles: Candle[] = [];
  let price = basePrice;
  const now = Date.now();

  for (let i = count; i > 0; i--) {
    const open = price;
    const change = (Math.random() - 0.48) * price * 0.015;
    const close = price + change;
    const high = Math.max(open, close) + Math.random() * price * 0.005;
    const low = Math.min(open, close) - Math.random() * price * 0.005;
    const volume = Math.random() * 1000000 + 500000;

    candles.push({
      time: now - i * 3600000, // 1 hour intervals
      open: Math.round(open * 100) / 100,
      high: Math.round(high * 100) / 100,
      low: Math.round(low * 100) / 100,
      close: Math.round(close * 100) / 100,
      volume: Math.round(volume),
    });

    price = close;
  }

  return candles;
}
