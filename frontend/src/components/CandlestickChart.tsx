import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts';
import { api } from '../services/api';
import { AlertCircle, RefreshCw, Radio } from 'lucide-react';

interface CandlestickChartProps {
  symbol: string;
  timeframe?: string;
  height?: number;
}

export default function CandlestickChart({ symbol, timeframe = '1m', height = 400 }: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasData, setHasData] = useState(false);
  const [isLive, setIsLive] = useState(false);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    try {
      // Create chart with dark theme
      const chart = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: height,
        layout: {
          background: { color: '#0f1012' },
          textColor: '#71717a',
        },
        grid: {
          vertLines: { color: '#1e1f23' },
          horzLines: { color: '#1e1f23' },
        },
        crosshair: {
          mode: 1,
          vertLine: {
            color: '#14b8a6',
            width: 1,
            style: 2,
            labelBackgroundColor: '#14b8a6',
          },
          horzLine: {
            color: '#14b8a6',
            width: 1,
            style: 2,
            labelBackgroundColor: '#14b8a6',
          },
        },
        rightPriceScale: {
          borderColor: '#2e3035',
          scaleMargins: {
            top: 0.1,
            bottom: 0.1,
          },
        },
        timeScale: {
          borderColor: '#2e3035',
          timeVisible: true,
          secondsVisible: false,
        },
      });

      // Add candlestick series
      const candlestickSeries = chart.addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderUpColor: '#22c55e',
        borderDownColor: '#ef4444',
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444',
      });

      chartRef.current = chart;
      candlestickSeriesRef.current = candlestickSeries;

      // Handle resize
      const handleResize = () => {
        if (chartContainerRef.current && chartRef.current) {
          chartRef.current.applyOptions({
            width: chartContainerRef.current.clientWidth,
          });
        }
      };

      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        if (chartRef.current) {
          chartRef.current.remove();
          chartRef.current = null;
        }
      };
    } catch (err) {
      console.error('Failed to initialize chart:', err);
      setError('Failed to initialize chart');
    }
  }, [height]);

  // Fetch candles function
  const fetchCandles = useCallback(async () => {
    if (!candlestickSeriesRef.current) return;

    try {
      setLoading(true);

      // Format symbol for API (BTC/USDT -> BTCUSDT)
      const apiSymbol = symbol.replace('/', '');
      const response = await api.getOHLCV(apiSymbol, timeframe, 200);

      if (response.candles && response.candles.length > 0) {
        const formattedData: CandlestickData<Time>[] = response.candles.map((candle) => ({
          time: (candle.timestamp / 1000) as Time,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
        }));

        candlestickSeriesRef.current.setData(formattedData);
        setHasData(true);
        setError(null);

        // Fit content
        if (chartRef.current) {
          chartRef.current.timeScale().fitContent();
        }
      } else {
        setError('No chart data available');
      }

      setLoading(false);
    } catch (err: any) {
      console.error('Failed to fetch candles:', err);
      // Only show error if we don't already have data
      if (!hasData) {
        setError('Unable to load chart data. Binance testnet may be slow.');
      }
      setLoading(false);
    }
  }, [symbol, timeframe, hasData]);

  // Connect to real-time kline WebSocket
  const connectWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const apiSymbol = symbol.replace('/', '');
    const ws = new WebSocket(`ws://localhost:8000/ws/klines/${apiSymbol}?timeframe=${timeframe}`);

    ws.onopen = () => {
      console.log('Kline WebSocket connected');
      setIsLive(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'kline' && candlestickSeriesRef.current) {
          const candle = data.candle;
          const candleData: CandlestickData<Time> = {
            time: (candle.timestamp / 1000) as Time,
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close,
          };
          // Update the last candle in real-time
          candlestickSeriesRef.current.update(candleData);
        }
      } catch (e) {
        console.error('WebSocket parse error:', e);
      }
    };

    ws.onclose = () => {
      console.log('Kline WebSocket disconnected');
      setIsLive(false);
      // Reconnect after 3 seconds
      setTimeout(() => {
        if (hasData) {
          connectWebSocket();
        }
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('Kline WebSocket error:', error);
      setIsLive(false);
    };

    wsRef.current = ws;
  }, [symbol, timeframe, hasData]);

  // Fetch data on mount and symbol change
  useEffect(() => {
    fetchCandles();
  }, [fetchCandles]);

  // Connect WebSocket after initial data loads
  useEffect(() => {
    if (hasData) {
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [hasData, connectWebSocket]);

  const handleRetry = () => {
    setError(null);
    fetchCandles();
  };

  return (
    <div className="relative w-full" style={{ minHeight: height }}>
      {/* Live indicator */}
      {isLive && (
        <div className="absolute top-2 right-2 z-20 flex items-center gap-1.5 px-2 py-1 bg-profit/20 rounded text-xs text-profit font-medium">
          <Radio className="w-3 h-3 animate-pulse" />
          LIVE
        </div>
      )}
      {loading && !hasData && (
        <div className="absolute inset-0 flex items-center justify-center bg-canvas/80 z-10">
          <div className="flex items-center gap-2 text-ink-secondary">
            <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <span>Loading chart...</span>
          </div>
        </div>
      )}
      {error && !hasData && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-canvas z-10">
          <AlertCircle className="w-8 h-8 text-warning mb-3" />
          <p className="text-ink-secondary mb-2">{error}</p>
          <button
            onClick={handleRetry}
            className="flex items-center gap-2 px-4 py-2 bg-surface hover:bg-surface-hover rounded-lg text-sm text-ink transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      )}
      <div ref={chartContainerRef} className="w-full" style={{ height }} />
    </div>
  );
}
