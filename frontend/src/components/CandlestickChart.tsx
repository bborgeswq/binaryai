import { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts';
import { api } from '../services/api';

interface CandlestickChartProps {
  symbol: string;
  timeframe?: string;
  height?: number;
}

export default function CandlestickChart({ symbol, timeframe = '1h', height = 400 }: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

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
  }, [height]);

  // Fetch and update data
  useEffect(() => {
    const fetchCandles = async () => {
      if (!candlestickSeriesRef.current) return;

      try {
        setLoading(true);
        setError(null);

        // Format symbol for API (BTC/USDT -> BTCUSDT)
        const apiSymbol = symbol.replace('/', '');
        const response = await api.getOHLCV(apiSymbol, timeframe, 200);

        if (response.candles && response.candles.length > 0) {
          const formattedData: CandlestickData<Time>[] = response.candles.map((candle) => ({
            time: (candle.timestamp / 1000) as Time, // Convert ms to seconds
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close,
          }));

          candlestickSeriesRef.current.setData(formattedData);

          // Fit content
          if (chartRef.current) {
            chartRef.current.timeScale().fitContent();
          }
        }

        setLoading(false);
      } catch (err: any) {
        console.error('Failed to fetch candles:', err);
        setError(err.message || 'Failed to load chart data');
        setLoading(false);
      }
    };

    fetchCandles();

    // Refresh candles every 30 seconds
    const interval = setInterval(fetchCandles, 30000);

    return () => clearInterval(interval);
  }, [symbol, timeframe]);

  // Update with real-time price
  useEffect(() => {
    const updateWithLatestPrice = (prices: Record<string, { price: number; change: number }>) => {
      if (!candlestickSeriesRef.current) return;

      const symbolKey = symbol.replace('/', '');
      const priceData = prices[symbolKey];

      if (priceData) {
        // Update the last candle with current price
        const now = Math.floor(Date.now() / 1000);
        candlestickSeriesRef.current.update({
          time: now as Time,
          open: priceData.price,
          high: priceData.price,
          low: priceData.price,
          close: priceData.price,
        });
      }
    };

    api.connectPriceStream(updateWithLatestPrice);

    return () => {
      api.disconnectPriceStream();
    };
  }, [symbol]);

  return (
    <div className="relative w-full">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-canvas/80 z-10">
          <div className="flex items-center gap-2 text-ink-secondary">
            <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <span>Loading chart...</span>
          </div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-canvas/80 z-10">
          <div className="text-center">
            <p className="text-loss mb-2">{error}</p>
            <p className="text-ink-faint text-sm">Make sure the API server is running</p>
          </div>
        </div>
      )}
      <div ref={chartContainerRef} className="w-full" />
    </div>
  );
}
