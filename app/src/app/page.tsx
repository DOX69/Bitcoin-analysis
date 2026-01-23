'use client';

import { useEffect, useState } from 'react';
import MetricsCard from '@/components/MetricsCard';
import PriceChart from '@/components/PriceChart';
import VolatilityChart from '@/components/VolatilityChart';
import { getCurrentBitcoinMetrics, getHistoricalPrices, BitcoinMetrics, BitcoinPrice } from '@/lib/bitcoin-api';

export default function Home() {
  const [metrics, setMetrics] = useState<BitcoinMetrics | null>(null);
  const [historicalData, setHistoricalData] = useState<BitcoinPrice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);

        // Fetch current metrics and historical data
        const [metricsData, priceData] = await Promise.all([
          getCurrentBitcoinMetrics(),
          getHistoricalPrices(90), // Get 90 days of data
        ]);

        setMetrics(metricsData);
        setHistoricalData(priceData);
      } catch (err) {
        console.error('Error fetching Bitcoin data:', err);
        setError('Failed to load Bitcoin data. Using demo data.');

        // Still try to load with mock data
        const [metricsData, priceData] = await Promise.all([
          getCurrentBitcoinMetrics(),
          getHistoricalPrices(90),
        ]);
        setMetrics(metricsData);
        setHistoricalData(priceData);
      } finally {
        setLoading(false);
      }
    }

    fetchData();

    // Refresh data every 5 minutes
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-5xl font-bold gradient-text mb-4">
            Bitcoin Analysis Dashboard
          </h1>
          <p className="text-gray-400 text-lg">
            Real-time Bitcoin price analysis powered by Databricks
          </p>
          {error && (
            <div className="mt-4 px-4 py-2 bg-yellow-900/20 border border-yellow-500/30 rounded-lg text-yellow-400 text-sm">
              ⚠️ {error}
            </div>
          )}
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricsCard
            title="Current Price"
            value={metrics ? `$${metrics.currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00'}
            change={metrics?.change24h}
            changePercent={metrics?.changePercent24h}
            loading={loading}
          />

          <MetricsCard
            title="24h High"
            value={metrics ? `$${metrics.high24h.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00'}
            loading={loading}
          />

          <MetricsCard
            title="24h Low"
            value={metrics ? `$${metrics.low24h.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00'}
            loading={loading}
          />

          <MetricsCard
            title="24h Volume"
            value={metrics ? `$${(metrics.volume24h / 1e9).toFixed(2)}B` : '$0.00B'}
            loading={loading}
          />
        </div>

        {/* Price Chart */}
        <div className="mb-8">
          <PriceChart
            data={historicalData}
            loading={loading}
          />
        </div>

        {/* Volatility Chart */}
        <div>
          <VolatilityChart
            data={historicalData.slice(-30)} // Last 30 days for volatility
            rsi={metrics?.rsi}
            loading={loading}
          />
        </div>
      </div>
    </main>
  );
}
