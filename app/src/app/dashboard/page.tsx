'use client';

import { useEffect, useState } from 'react';
import { getCurrentBitcoinMetrics, getHistoricalPrices, BitcoinMetrics, BitcoinPrice } from '@/lib/bitcoin-api';
import {
    DashboardHeader,
    StatsPanel,
    StatCard,
    DatePicker
} from '@/components/dashboard';
import PriceChart from '@/components/PriceChart';

export default function Dashboard() {
    const [metrics, setMetrics] = useState<BitcoinMetrics | null>(null);
    const [historicalData, setHistoricalData] = useState<BitcoinPrice[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [selectedTime, setSelectedTime] = useState('6m');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [apiDateRange, setApiDateRange] = useState<{ start?: string, end?: string }>({});
    const [showRsi, setShowRsi] = useState(false);
    const [isRightPanelOpen, setIsRightPanelOpen] = useState(true);
    const [chartType, setChartType] = useState<'line' | 'candlestick'>('line');

    const periodStats = historicalData.length > 0 ? {
        start: historicalData[0],
        end: historicalData[historicalData.length - 1],
        high: Math.max(...historicalData.map(d => d.high)),
        low: Math.min(...historicalData.map(d => d.low)),
    } : null;

    const variation = periodStats ? ((periodStats.end.close - periodStats.start.open) / periodStats.start.open) * 100 : 0;


    const handleDateChange = (type: 'start' | 'end', value: string) => {
        const newRange = { ...apiDateRange, [type]: value };
        setApiDateRange(newRange);
        if (newRange.start && newRange.end) {
            setSelectedTime('custom');
        }
    };

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
                    getHistoricalPrices(
                        getDaysForFilter(selectedTime),
                        selectedTime === 'custom' ? apiDateRange.start : undefined,
                        selectedTime === 'custom' ? apiDateRange.end : undefined
                    ),
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
    }, [selectedTime, apiDateRange]);

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
                                            onClick={() => {
                                                setApiDateRange({}); // Clear custom range when using presets
                                                setSelectedTime(filter.value);
                                            }}
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
                                    <DatePicker
                                        label="Start Date"
                                        value={apiDateRange.start || ''}
                                        onChange={(val) => handleDateChange('start', val)}
                                    />
                                    <span className="text-gray-500">→</span>
                                    <DatePicker
                                        label="End Date"
                                        value={apiDateRange.end || ''}
                                        onChange={(val) => handleDateChange('end', val)}
                                    />
                                    <div className="flex items-center gap-2 ml-4">
                                        <span className="text-xs text-gray-400">RSI</span>
                                        <div
                                            className={`w-9 h-5 rounded-full relative cursor-pointer transition-colors ${showRsi ? 'bg-[#F7931A]' : 'bg-gray-700'}`}
                                            onClick={() => setShowRsi(!showRsi)}
                                        >
                                            <div
                                                className={`absolute top-1 w-3 h-3 bg-white rounded-full shadow-sm transition-all ${showRsi ? 'right-1' : 'left-1'}`}
                                            />
                                        </div>
                                    </div>
                                </div>
                                <div className="flex bg-gray-800/50 rounded-lg p-1 gap-1">
                                    <button
                                        onClick={() => setChartType('line')}
                                        className={`p-1.5 rounded-md transition-all ${chartType === 'line' ? 'bg-[#F7931A] text-black' : 'text-gray-400 hover:text-white'}`}
                                        title="Line Chart"
                                    >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                                        </svg>
                                    </button>
                                    <button
                                        onClick={() => setChartType('candlestick')}
                                        className={`p-1.5 rounded-md transition-all ${chartType === 'candlestick' ? 'bg-[#F7931A] text-black' : 'text-gray-400 hover:text-white'}`}
                                        title="Candlestick Chart"
                                    >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                        </svg>
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="h-[420px] dashboard-chart-container relative">
                            <PriceChart
                                data={historicalData}
                                loading={loading}
                                showRsi={showRsi}
                                type={chartType}
                            />
                        </div>

                        {/* Metrics Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                            {/* Card 1: PNL - Daily (Moved from chart) */}
                            <StatCard
                                title="PNL - Daily"
                                value={metrics ? `$${metrics.currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00'}
                                trend={metrics ? (metrics.change24h >= 0 ? 'up' : 'down') : 'neutral'}
                                trendColor={metrics ? (metrics.change24h >= 0 ? 'text-green-400' : 'text-red-400') : 'text-gray-400'}
                                subtitle={metrics ? `${metrics.change24h >= 0 ? '+' : ''}${metrics.changePercent24h.toFixed(2)}%` : '0.00%'}
                                loading={loading}
                                icon={
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                }
                            />

                            {/* Card 2: Variation (Dynamic) */}
                            <StatCard
                                title={`Variation (${selectedTime.toUpperCase()})`}
                                value={`${variation >= 0 ? '+' : ''}${variation.toFixed(2)}%`}
                                trend={variation >= 0 ? 'up' : 'down'}
                                trendColor={variation >= 0 ? 'text-green-400' : 'text-red-400'}
                                loading={loading}
                            />

                            {/* Card 3: ATH (Dynamic) */}
                            <StatCard
                                title={`ATH (${selectedTime.toUpperCase()})`}
                                value={periodStats ? `$${periodStats.high.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '-'}
                                loading={loading}
                                trend="neutral"
                                icon={
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                                    </svg>
                                }
                            />

                            {/* Card 4: ATL (Dynamic) */}
                            <StatCard
                                title={`ATL (${selectedTime.toUpperCase()})`}
                                value={periodStats ? `$${periodStats.low.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '-'}
                                loading={loading}
                                trend="neutral"
                                icon={
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                                    </svg>
                                }
                            />
                        </div>
                    </div>
                </div>

                {/* Collapsible Right Panel Section */}
                <div className="hidden xl:flex flex-row h-[calc(100vh-64px)] overflow-hidden">
                    {/* Toggle Button & Separator */}
                    <div className="h-full flex flex-col justify-center items-center px-1 relative w-3">
                        {/* The 'Orange Scroll Bar' - decorative vertical line */}
                        <div className={`w-[1.5px] rounded-full bg-[#ff6b35] transition-all duration-300 ${isRightPanelOpen ? 'h-[120px]' : 'h-[60px] opacity-50'}`} />

                        {/* Toggle Button centered on the line */}
                        <button
                            onClick={() => setIsRightPanelOpen(!isRightPanelOpen)}
                            className="absolute z-10 p-0.5 rounded-full bg-[#2a2a2a] border border-[#ff6b35] text-[#ff6b35] hover:bg-[#ff6b35] hover:text-black transition-all shadow-lg"
                            style={{ top: '50%', transform: 'translateY(-50%)' }}
                        >
                            <svg
                                className={`w-3 h-3 transition-transform duration-300 ${isRightPanelOpen ? 'rotate-0' : 'rotate-180'}`}
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
                            </svg>
                        </button>
                    </div>

                    {/* Panel Container */}
                    <div
                        className={`transition-all duration-300 ease-in-out overflow-hidden ${isRightPanelOpen ? 'w-[360px] opacity-100' : 'w-0 opacity-0'}`}
                    >
                        <div className="h-full overflow-y-auto">
                            <StatsPanel metrics={metrics} loading={loading} />
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
