'use client';

import React from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    LineElement,
    PointElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { BitcoinPrice } from '@/lib/bitcoin-api';

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    LineElement,
    PointElement,
    Title,
    Tooltip,
    Legend
);

interface VolatilityChartProps {
    data: BitcoinPrice[];
    rsi?: number;
    loading?: boolean;
}

const VolatilityChart: React.FC<VolatilityChartProps> = ({
    data,
    rsi = 50,
    loading = false
}) => {
    // Calculate daily volatility (high - low)
    const volatilityData = data.map((item) => item.high - item.low);

    const chartData = {
        labels: data.map((item) => item.date),
        datasets: [
            {
                label: 'Daily Volatility',
                data: volatilityData,
                backgroundColor: volatilityData.map((value) => {
                    const maxVolatility = Math.max(...volatilityData);
                    const intensity = value / maxVolatility;
                    return `rgba(255, ${107 + intensity * 100}, 53, ${0.5 + intensity * 0.3})`;
                }),
                borderColor: 'rgba(255, 107, 53, 1)',
                borderWidth: 1,
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
                backgroundColor: 'rgba(20, 20, 20, 0.95)',
                titleColor: '#fff',
                bodyColor: '#a0a0a0',
                borderColor: 'rgba(255, 165, 0, 0.3)',
                borderWidth: 1,
                padding: 12,
                displayColors: false,
                callbacks: {
                    label: function (context: any) {
                        return `Volatility: $${context.parsed.y.toLocaleString('en-US', {
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
    };

    // RSI indicator color
    const getRSIColor = (rsi: number) => {
        if (rsi > 70) return 'text-red-400';
        if (rsi < 30) return 'text-green-400';
        return 'text-yellow-400';
    };

    const getRSILabel = (rsi: number) => {
        if (rsi > 70) return 'Overbought';
        if (rsi < 30) return 'Oversold';
        return 'Neutral';
    };

    return (
        <div className="glass-card rounded-xl p-6 gradient-border">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold gradient-text">Volatility Analysis</h2>

                <div className="flex items-center gap-4">
                    <div className="text-right">
                        <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                            RSI (14)
                        </div>
                        <div className={`text-2xl font-bold ${getRSIColor(rsi)}`}>
                            {rsi.toFixed(1)}
                        </div>
                        <div className={`text-xs font-medium ${getRSIColor(rsi)}`}>
                            {getRSILabel(rsi)}
                        </div>
                    </div>
                </div>
            </div>

            {loading ? (
                <div className="h-[300px] flex items-center justify-center">
                    <div className="loading-pulse text-gray-400">Loading volatility data...</div>
                </div>
            ) : (
                <div className="h-[300px]">
                    <Bar data={chartData} options={options} />
                </div>
            )}
        </div>
    );
};

export default VolatilityChart;
