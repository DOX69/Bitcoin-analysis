
'use client';

import React, { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
    DashboardHeader,
    StatsPanel,
    StatCard,
    DatePicker
} from '@/components/dashboard';
import PriceChart from '@/components/PriceChart';
import type { BitcoinMetrics, BitcoinPrice } from '@/lib/schemas';
import type { Currency } from '@/lib/bitcoin-data-server';
import { formatPriceWithCurrency } from '@/lib/format-utils';

interface DashboardClientProps {
    initialMetrics: BitcoinMetrics;
    initialHistoricalData: BitcoinPrice[];
    selectedTime: string;
    startDate: string;
    endDate: string;
    selectedCurrency: Currency;
}

export default function DashboardClient({
    initialMetrics,
    initialHistoricalData,
    selectedTime: initialTime,
    selectedCurrency: initialCurrency,
}: DashboardClientProps) {
    const router = useRouter();
    const searchParams = useSearchParams();

    // States that don't necessarily need to be in URL (UI preferences)
    const [showRsi, setShowRsi] = useState(false);
    const [isRightPanelOpen, setIsRightPanelOpen] = useState(true);
    const [chartType, setChartType] = useState<'line' | 'candlestick'>('line');

    // Stats calculated from data
    const periodStats = initialHistoricalData.length > 0 ? {
        start: initialHistoricalData[0],
        end: initialHistoricalData[initialHistoricalData.length - 1],
        high: Math.max(...initialHistoricalData.map(d => d.high)),
        low: Math.min(...initialHistoricalData.map(d => d.low)),
    } : null;

    const variation = periodStats ? ((periodStats.end.close - periodStats.start.open) / periodStats.start.open) * 100 : 0;

    const handleTimeFilter = (value: string) => {
        const params = new URLSearchParams(searchParams.toString());
        params.set('time', value);
        params.delete('start');
        params.delete('end');
        router.push(`?${params.toString()}`);
    };

    const handleDateChange = (type: 'start' | 'end', value: string) => {
        const params = new URLSearchParams(searchParams.toString());
        params.set(type, value);
        params.set('time', 'custom');
        router.push(`?${params.toString()}`);
    };

    const handleCurrencyFilter = (value: Currency) => {
        const params = new URLSearchParams(searchParams.toString());
        params.set('currency', value);
        router.push(`?${params.toString()}`);
    };

    const timeFilters = [
        { label: '1W', value: '1w' },
        { label: '1M', value: '1m' },
        { label: '6M', value: '6m' },
        { label: '1Y', value: '1y' },
        { label: 'YTD', value: 'ytd' },
        { label: 'ALL', value: 'all' },
    ];

    return (
        <div className="min-h-screen bg-[#141414] text-white font-sans flex flex-col">
            <DashboardHeader />

            <main className="flex-1 flex overflow-hidden">
                <div className="flex-1 flex flex-col h-[calc(100vh-64px)] overflow-hidden">
                    <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
                        {/* Filters Row */}
                        <div className="mb-6">
                            <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
                                <div className="flex gap-2">
                                    {timeFilters.map((filter) => (
                                        <button
                                            key={filter.value}
                                            onClick={() => handleTimeFilter(filter.value)}
                                            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${initialTime === filter.value
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
                                        value={searchParams.get('start') || ''}
                                        onChange={(val) => handleDateChange('start', val)}
                                    />
                                    <span className="text-gray-500">→</span>
                                    <DatePicker
                                        label="End Date"
                                        value={searchParams.get('end') || ''}
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
                                <div className="flex gap-2 items-center">
                                    <div className="flex bg-gray-800/50 rounded-lg p-1 gap-1">
                                        {(['USD', 'CHF', 'EUR'] as const).map((currency) => (
                                            <button
                                                key={currency}
                                                onClick={() => handleCurrencyFilter(currency)}
                                                className={`px-2 py-1 rounded-md text-xs font-medium transition-all ${initialCurrency === currency
                                                    ? 'bg-[#F7931A] text-black'
                                                    : 'text-gray-400 hover:text-white'
                                                    }`}
                                            >
                                                {currency}
                                            </button>
                                        ))}
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
                        </div>

                        {/* Chart Container */}
                        <div className="h-[420px] dashboard-chart-container relative mb-6">
                            <PriceChart
                                data={initialHistoricalData}
                                loading={false}
                                showRsi={showRsi}
                                type={chartType}
                                currencySymbol={{
                                    'USD': '$',
                                    'EUR': '€',
                                    'GBP': '£',
                                    'CHF': 'Fr'
                                }[initialCurrency] || '$'}
                            />
                        </div>

                        {/* Metrics Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                            <StatCard
                                title="PNL - Daily"
                                value={formatPriceWithCurrency(initialMetrics.currentPrice, initialCurrency)}
                                trend={initialMetrics.change24h >= 0 ? 'up' : 'down'}
                                trendColor={initialMetrics.change24h >= 0 ? 'text-green-400' : 'text-red-400'}
                                subtitle={`${initialMetrics.change24h >= 0 ? '+' : ''}${initialMetrics.changePercent24h.toFixed(2)}%`}
                                icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
                            />
                            <StatCard
                                title={`Variation (${initialTime.toUpperCase()})`}
                                value={`${variation >= 0 ? '+' : ''}${variation.toFixed(2)}%`}
                                trend={variation >= 0 ? 'up' : 'down'}
                                trendColor={variation >= 0 ? 'text-green-400' : 'text-red-400'}
                            />
                            <StatCard
                                title={`ATH (${initialTime.toUpperCase()})`}
                                value={periodStats ? formatPriceWithCurrency(periodStats.high, initialCurrency) : '-'}
                                trend="neutral"
                                icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
                            />
                            <StatCard
                                title={`ATL (${initialTime.toUpperCase()})`}
                                value={periodStats ? formatPriceWithCurrency(periodStats.low, initialCurrency) : '-'}
                                trend="neutral"
                                icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" /></svg>}
                            />
                        </div>
                    </div>
                </div>

                {/* Collapsible Right Panel */}
                <div className="hidden xl:flex flex-row h-[calc(100vh-64px)] overflow-hidden">
                    <div className="h-full flex flex-col justify-center items-center px-1 relative w-3 text-[#F7931A]">
                        <div className={`w-[1px] bg-currentColor transition-all ${isRightPanelOpen ? 'h-32' : 'h-16 opacity-30'}`} />
                        <button
                            onClick={() => setIsRightPanelOpen(!isRightPanelOpen)}
                            className="absolute z-10 p-0.5 rounded-full bg-[#1c1c1c] border border-[#F7931A] hover:bg-[#F7931A] hover:text-black transition-all"
                            style={{ top: '50%', transform: 'translateY(-50%)' }}
                        >
                            <svg className={`w-3 h-3 transition-transform ${isRightPanelOpen ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" /></svg>
                        </button>
                    </div>
                    <div className={`transition-all duration-300 overflow-hidden ${isRightPanelOpen ? 'w-[360px]' : 'w-0'}`}>
                        <div className="h-full overflow-y-auto">
                            <StatsPanel metrics={initialMetrics} loading={false} />
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
