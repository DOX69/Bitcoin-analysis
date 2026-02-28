'use client';

import React from 'react';
import { BitcoinMetrics } from '@/lib/bitcoin-api';

interface StatsPanelProps {
    metrics: BitcoinMetrics | null;
    loading?: boolean;
}

const StatsPanel: React.FC<StatsPanelProps> = ({ metrics, loading = false }) => {
    // Format large numbers
    const formatCurrency = (value: number) => {
        if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
        if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
        if (value >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
        return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    };

    return (
        <aside className="stats-panel">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-white">Average Deviation Power</h3>
                <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-400">Breakdown</span>
                    <span className="text-sm text-gray-400">Single</span>
                    <span className="text-sm text-gray-400">Smart</span>
                    <span className="px-2 py-1 rounded-md bg-energy-orange/20 text-energy-orange text-xs font-medium">
                        Total
                    </span>
                </div>
            </div>

            {/* Direction Toggle */}
            <div className="flex gap-2 mb-6">
                <span className="text-sm text-gray-400">Direction</span>
                <button className="px-3 py-1 rounded-md bg-gray-700/50 text-gray-300 text-xs">Long</button>
                <button className="px-3 py-1 rounded-md bg-gray-700/50 text-gray-300 text-xs">Short</button>
                <button className="px-3 py-1 rounded-md bg-energy-orange/20 text-energy-orange text-xs font-medium">All</button>
            </div>

            {/* User Selector */}
            <div className="mb-6">
                <div className="flex items-center justify-between px-4 py-3 bg-gray-800/50 rounded-lg border border-gray-700">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-energy-orange to-energy-yellow flex items-center justify-center">
                            <span className="text-xs font-bold text-black">U</span>
                        </div>
                        <span className="text-sm font-medium text-white">User Profile</span>
                    </div>
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                {/* Deposit */}
                <div>
                    <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">Deposit</div>
                    {loading ? (
                        <div className="h-8 bg-gray-700/50 rounded animate-pulse" />
                    ) : (
                        <div className="text-xl font-bold text-white">
                            {metrics ? formatCurrency(metrics.currentPrice) : '$0.00'}
                        </div>
                    )}
                </div>

                {/* Positions */}
                <div>
                    <div className="flex items-center gap-1 text-xs text-gray-400 uppercase tracking-wide mb-1">
                        Positions (O/C)
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <div className="text-xl font-bold text-energy-orange">0/0</div>
                </div>

                {/* Win Rate */}
                <div>
                    <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">Win rate</div>
                    {loading ? (
                        <div className="h-8 bg-gray-700/50 rounded animate-pulse" />
                    ) : (
                        <div className="text-xl font-bold text-white">
                            {metrics?.rsi ? `${((metrics.rsi / 100) * 100).toFixed(1)}%` : '0.0%'}
                        </div>
                    )}
                </div>

                {/* Profit Factor */}
                <div>
                    <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">Profit factor</div>
                    <div className="text-xl font-bold text-white">0.00</div>
                </div>
            </div>

            {/* Risk Management */}
            <div className="mb-6">
                <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">Risk management</div>
                <div className="text-base font-medium text-gray-300">Disabled</div>
            </div>

            {/* PnL by Coin */}
            <div className="mb-6">
                <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">PnL by coin</div>
            </div>

            {/* View Details Link */}
            <a
                href="#"
                className="inline-flex items-center gap-1 text-sm text-energy-orange hover:text-energy-yellow smooth-transition"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                View details
            </a>
        </aside>
    );
};

export default StatsPanel;
