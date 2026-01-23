'use client';

import React, { useState, useEffect } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { BitcoinPrice } from '@/lib/bitcoin-api';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

interface PriceChartProps {
    data: BitcoinPrice[];
    loading?: boolean;
}

type TimeRange = '7d' | '30d' | '90d' | '1y';

const PriceChart: React.FC<PriceChartProps> = ({ data, loading = false }) => {
    const [timeRange, setTimeRange] = useState<TimeRange>('30d');
    const [filteredData, setFilteredData] = useState<BitcoinPrice[]>(data);

    useEffect(() => {
        const daysMap: Record<TimeRange, number> = {
            '7d': 7,
            '30d': 30,
            '90d': 90,
            '1y': 365,
        };

        const days = daysMap[timeRange];
        const filtered = data.slice(-days);
        setFilteredData(filtered);
    }, [data, timeRange]);

    const chartData = {
        labels: filteredData.map((item) => item.date),
        datasets: [
            {
                label: 'Bitcoin Price (USD)',
                data: filteredData.map((item) => item.close),
                borderColor: 'rgba(255, 107, 53, 1)',
                backgroundColor: (context: any) => {
                    const ctx = context.chart.ctx;
                    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                    gradient.addColorStop(0, 'rgba(255, 107, 53, 0.3)');
                    gradient.addColorStop(0.5, 'rgba(247, 183, 49, 0.2)');
                    gradient.addColorStop(1, 'rgba(255, 165, 0, 0.0)');
                    return gradient;
                },
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: '#ffa500',
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false,
            },
            tooltip: {
                mode: 'index' as const,
                intersect: false,
                backgroundColor: 'rgba(20, 20, 20, 0.95)',
                titleColor: '#fff',
                bodyColor: '#a0a0a0',
                borderColor: 'rgba(255, 165, 0, 0.3)',
                borderWidth: 1,
                padding: 12,
                displayColors: false,
                callbacks: {
                    label: function (context: any) {
                        return `$${context.parsed.y.toLocaleString('en-US', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                        })}`;
                    },
                },
            },
        },
        scales: {
            x: {
                grid: {
                    display: false,
                },
                ticks: {
                    color: '#666',
                    maxTicksLimit: 8,
                },
            },
            y: {
                grid: {
                    color: 'rgba(255, 165, 0, 0.05)',
                },
                ticks: {
                    color: '#666',
                    callback: function (value: any) {
                        return '$' + value.toLocaleString('en-US');
                    },
                },
            },
        },
        interaction: {
            mode: 'nearest' as const,
            axis: 'x' as const,
            intersect: false,
        },
    };

    return (
        <div className="glass-card rounded-xl p-6 gradient-border">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold gradient-text">Price Chart</h2>

                <div className="flex gap-2">
                    {(['7d', '30d', '90d', '1y'] as TimeRange[]).map((range) => (
                        <button
                            key={range}
                            onClick={() => setTimeRange(range)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium smooth-transition ${timeRange === range
                                    ? 'bg-gradient-to-r from-energy-orange to-energy-yellow text-black'
                                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                                }`}
                        >
                            {range}
                        </button>
                    ))}
                </div>
            </div>

            {loading ? (
                <div className="h-[400px] flex items-center justify-center">
                    <div className="loading-pulse text-gray-400">Loading chart...</div>
                </div>
            ) : (
                <div className="h-[400px]">
                    <Line data={chartData} options={options} />
                </div>
            )}
        </div>
    );
};

export default PriceChart;
