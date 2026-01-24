'use client';

import { useEffect, useState } from 'react';
import { getCurrentBitcoinMetrics, getHistoricalPrices, BitcoinMetrics, BitcoinPrice } from '@/lib/bitcoin-api';
import {
    DashboardHeader,
    StatsPanel,
    StatCard
} from '@/components/dashboard';
import PriceChart from '@/components/PriceChart';

export default function Dashboard() {
    const [metrics, setMetrics] = useState<BitcoinMetrics | null>(null);
    const [historicalData, setHistoricalData] = useState<BitcoinPrice[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [selectedTime, setSelectedTime] = useState('6m');
    const [startDate, setStartDate] = useState('13 Jul 2025');
    const [endDate, setEndDate] = useState('13 Jul 2025');

    const timeFilters = [
        { label: '1W', value: '1w' },
        { label: '1M', value: '1m' },
        { label: '6M', value: '6m' },
        { label: '1Y', value: '1y' },
        { label: 'YTD', value: 'ytd' },
        { label: 'ALL', value: 'all' },
    ];

    const getDaysForFilter = (filter: string) => {
        switch (filter) {
            case '1w': return 7;
            case '1m': return 30;
            case '6m': return 180;
            case '1y': return 365;
            case 'ytd': {
                const now = new Date();
                const startOfYear = new Date(now.getFullYear(), 0, 1);
                const diff = now.getTime() - startOfYear.getTime();
                return Math.ceil(diff / (1000 * 60 * 60 * 24));
            }
            case 'all': return 3650;
            default: return 180;
        }
    };

    useEffect(() => {
        async function fetchData() {
            try {
                // Determine if this is initial load
                if (!metrics) setLoading(true);
                setError(null);

                // Fetch current metrics and historical data
                const [metricsData, priceData] = await Promise.all([
                    getCurrentBitcoinMetrics(),
                    getHistoricalPrices(getDaysForFilter(selectedTime)),
                ]);

                setMetrics(metricsData);
                setHistoricalData(priceData);

                // Update start/end dates based on data
                if (priceData.length > 0) {
                    const formatDate = (dateStr: string) => {
                        const d = new Date(dateStr);
                        return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
                    };
                    setStartDate(formatDate(priceData[0].date));
                    setEndDate(formatDate(priceData[priceData.length - 1].date));
                }
            } catch (err) {
                console.error('Error fetching Bitcoin data:', err);
                setError('Failed to load Bitcoin data.');
            } finally {
                setLoading(false);
            }
        }

        fetchData();

        // Refresh data every 60 seconds
        const interval = setInterval(fetchData, 60 * 1000);
        return () => clearInterval(interval);
    }, [selectedTime]);

    return (
        <div className="min-h-screen bg-[#141414] text-white font-sans flex flex-col">
            <DashboardHeader />

            <main className="flex-1 flex overflow-hidden">


                {/* Main Content */}
                <div className="flex-1 flex flex-col h-[calc(100vh-64px)] overflow-hidden">
                    <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
                        {/* Error Banner */}
                        {error && (
                            <div className="mb-6 px-4 py-3 bg-red-900/20 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center gap-2">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                                {error}
                            </div>
                        )}

                        {/* Top Chart Section */}
                        <div className="mb-6">
                            <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
                                <div className="flex gap-2">
                                    {timeFilters.map((filter) => (
                                        <button
                                            key={filter.value}
                                            onClick={() => setSelectedTime(filter.value)}
                                            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${selectedTime === filter.value
                                                ? 'bg-[#F7931A] text-black'
                                                : 'bg-gray-800/50 text-gray-400 hover:text-white hover:bg-gray-700'
                                                }`}
                                        >
                                            {filter.label}
                                        </button>
                                    ))}
                                </div>
                                <div className="flex gap-2 items-center">
                                    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/50 rounded-lg border border-gray-700">
                                        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                        </svg>
                                        <span className="text-sm text-gray-300">{startDate}</span>
                                        <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                        </svg>
                                    </div>
                                    <span className="text-gray-500">→</span>
                                    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/50 rounded-lg border border-gray-700">
                                        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                        </svg>
                                        <span className="text-sm text-gray-300">{endDate}</span>
                                        <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                        </svg>
                                    </div>
                                </div>
                            </div>

                            <div className="h-[420px] dashboard-chart-container relative">
                                <div className="absolute top-6 left-6 z-10">
                                    <h2 className="text-lg font-medium text-gray-400 mb-1">PNL - daily</h2>
                                    {metrics && (
                                        <div className="flex items-baseline gap-2">
                                            <span className="text-2xl font-bold text-white">
                                                ${metrics.currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                                            </span>
                                            <span className={`text-sm font-medium ${metrics.change24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                {metrics.change24h >= 0 ? '+' : ''}{metrics.changePercent24h.toFixed(2)}%
                                            </span>
                                        </div>
                                    )}
                                </div>

                                {/* Toggle Switch */}
                                <div className="absolute top-6 right-6 z-10 flex items-center gap-2">
                                    <span className="text-xs text-gray-400">EMA indicator</span>
                                    <div className="w-10 h-5 bg-blue-600 rounded-full relative cursor-pointer">
                                        <div className="absolute right-1 top-1 w-3 h-3 bg-white rounded-full shadow-sm" />
                                    </div>
                                </div>

                                <PriceChart
                                    data={historicalData}
                                    loading={loading}
                                />
                            </div>
                        </div>

                        {/* Metrics Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4 mb-6">
                            <StatCard
                                title="Total P&L"
                                value="$0.00"
                                trend="neutral"
                                subtitle="-0.00%"
                                loading={loading}
                            />
                            <StatCard
                                title="Total fees"
                                value="$0.00"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="Avg win"
                                value="-(-)"
                                trend="up"
                                trendColor="text-green-400"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="Avg loss"
                                value="-(-)"
                                trend="down"
                                trendColor="text-red-400"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="Volume"
                                value={metrics ? `$${(metrics.volume24h / 1e9).toFixed(2)}B` : '$0.00'}
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="Winning positions"
                                value="0"
                                trend="neutral"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                                    </svg>
                                }
                                loading={loading}
                            />

                            {/* Row 2 */}
                            <StatCard
                                title="Losing positions"
                                value="0"
                                trend="down"
                                trendColor="text-red-400"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="Positions (L/S)"
                                value="0/0/0"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="Positions (single/smart)"
                                value="0/0"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="Best position"
                                value="-"
                                trend="up"
                                trendColor="text-green-400"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11l5-5m0 0l5 5m-5-5v12" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="Worst position"
                                value="-"
                                trend="down"
                                trendColor="text-red-400"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="Avg duration"
                                value="-"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                }
                                loading={loading}
                            />

                            {/* Row 3 */}
                            <StatCard
                                title="Capital efficiency"
                                value="-"
                                trend="up"
                                trendColor="text-green-400"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="Avg efficiency / position"
                                value="-"
                                trend="up"
                                trendColor="text-green-400"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="Risk / Reward"
                                value="-"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                                    </svg>
                                }
                                loading={loading}
                            />
                            <StatCard
                                title="R2"
                                value="-"
                                icon={
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                    </svg>
                                }
                                loading={loading}
                            />
                        </div>
                    </div>
                </div>

                {/* Right Panel */}
                <div className="hidden xl:block h-[calc(100vh-64px)] overflow-y-auto">
                    <StatsPanel metrics={metrics} loading={loading} />
                </div>
            </main>
        </div>
    );
}
