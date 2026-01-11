'use client';

import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { ChevronDown } from 'lucide-react';
import type { Bar, Indicator } from '@/types';

export function PriceChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  const [symbol, setSymbol] = useState('USO');
  const [timeframe, setTimeframe] = useState('1D');

  // Map frontend timeframe values to Alpaca API format
  const mapTimeframe = (tf: string): string => {
    const map: Record<string, string> = {
      '1H': '1Hour',
      '4H': '4Hour',
      '1D': '1Day',
      '1W': '1Week',
    };
    return map[tf] || '1Day';
  };

  const { data: bars, refetch: refetchBars } = useApi<Bar[]>(
    () => apiClient.getBars(symbol, 390, mapTimeframe(timeframe)),
    30000,
    [symbol, timeframe]
  );

  const { data: indicators } = useApi<Indicator[]>(
    () => apiClient.getIndicators(symbol, '5m', 100),
    30000
  );

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1a1a1a' },
        textColor: '#808080',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.03)' },
        horzLines: { color: 'rgba(255,255,255,0.03)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 420,
      timeScale: {
        borderColor: 'rgba(255,255,255,0.06)',
        timeVisible: true,
      },
      rightPriceScale: {
        borderColor: 'rgba(255,255,255,0.06)',
      },
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#b1ffc2',
      downColor: '#f87171',
      borderUpColor: '#b1ffc2',
      borderDownColor: '#f87171',
      wickUpColor: '#b1ffc2',
      wickDownColor: '#f87171',
    });

    const volumeSeries = chart.addHistogramSeries({
      color: '#c2f4ff',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    });

    chart.priceScale('').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    volumeSeriesRef.current = volumeSeries;

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
      chart.remove();
    };
  }, []);

  useEffect(() => {
    if (!bars || !candlestickSeriesRef.current || !volumeSeriesRef.current) return;

    const candleData = bars.map((bar) => ({
      time: (new Date(bar.timestamp).getTime() / 1000) as UTCTimestamp,
      open: Number(bar.open),
      high: Number(bar.high),
      low: Number(bar.low),
      close: Number(bar.close),
    }));

    const volumeData = bars.map((bar) => ({
      time: (new Date(bar.timestamp).getTime() / 1000) as UTCTimestamp,
      value: Number(bar.volume),
      color: Number(bar.close) >= Number(bar.open) ? 'rgba(177,255,194,0.3)' : 'rgba(248,113,113,0.3)',
    }));

    candlestickSeriesRef.current.setData(candleData);
    volumeSeriesRef.current.setData(volumeData);

    chartRef.current?.timeScale().fitContent();
  }, [bars]);

  const handleSymbolChange = (newSymbol: string) => {
    setSymbol(newSymbol);
  };

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-medium">Price Chart</h2>
        <div className="flex items-center space-x-3">
          {/* Symbol Selector */}
          <div className="relative">
            <select
              value={symbol}
              onChange={(e) => handleSymbolChange(e.target.value)}
              className="appearance-none bg-surface border border-border rounded-lg px-3 py-1.5 pr-8 text-sm font-mono font-medium text-text-primary cursor-pointer hover:border-border-hover transition-colors"
            >
              <option value="USO">USO</option>
              <option value="UNG">UNG</option>
            </select>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-secondary pointer-events-none" strokeWidth={2} />
          </div>

          {/* Timeframe Selector */}
          <div className="flex space-x-1">
            {['1H', '4H', '1D', '1W'].map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={cn(
                  'px-2.5 py-1 text-xs font-mono rounded-full transition-all duration-150',
                  timeframe === tf
                    ? 'bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                )}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div ref={chartContainerRef} className="relative" />

      {/* Chart Stats */}
      {bars && bars.length > 0 && (
        <div className="mt-3 grid grid-cols-4 gap-2">
          <div className="border border-border rounded-lg p-2">
            <p className="text-[11px] text-text-secondary uppercase tracking-wide">Open</p>
            <p className="text-sm font-mono font-semibold tabular-nums mt-0.5">${Number(bars[bars.length - 1].open).toFixed(2)}</p>
          </div>
          <div className="border border-border rounded-lg p-2">
            <p className="text-[11px] text-text-secondary uppercase tracking-wide">High</p>
            <p className="text-sm font-mono font-semibold tabular-nums text-profit mt-0.5">${Number(bars[bars.length - 1].high).toFixed(2)}</p>
          </div>
          <div className="border border-border rounded-lg p-2">
            <p className="text-[11px] text-text-secondary uppercase tracking-wide">Low</p>
            <p className="text-sm font-mono font-semibold tabular-nums text-loss mt-0.5">${Number(bars[bars.length - 1].low).toFixed(2)}</p>
          </div>
          <div className="border border-border rounded-lg p-2">
            <p className="text-[11px] text-text-secondary uppercase tracking-wide">Close</p>
            <p className="text-sm font-mono font-semibold tabular-nums mt-0.5">${Number(bars[bars.length - 1].close).toFixed(2)}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(' ');
}
