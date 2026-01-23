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
import { formatPrice, formatDate, formatTooltipTime } from '@/lib/format-utils';

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
                borderWidth: 1.5,
                backgroundColor: (context: any) => {
                    const ctx = context.chart.ctx;
                    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                    gradient.addColorStop(0, 'rgba(255, 107, 53, 0.15)');
                    gradient.addColorStop(0.5, 'rgba(247, 183, 49, 0.05)');
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
                backgroundColor: 'rgba(28, 28, 28, 0.95)',
                padding: 15,
                displayColors: false,
                cornerRadius: 12,
                titleFont: {
                    size: 18,
                    weight: 'bold' as const,
                    family: "'Inter', sans-serif",
                },
                bodyFont: {
                    size: 14,
                    family: "'Inter', sans-serif",
                },
                titleColor: '#ffffff',
                bodyColor: '#9ca3af',
                borderColor: 'rgba(255, 165, 0, 0.3)',
                borderWidth: 1,
                callbacks: {
                    title: function (context: any) {
                        const value = context[0].parsed.y;
                        return formatPrice(value);
                    },
                    label: function (context: any) {
                        const date = formatDate(context.label);
                        const time = formatTooltipTime();
                        return [date, time];
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
                    color: '#6b7280',
                    maxTicksLimit: 12,
                    font: {
                        size: 11,
                    },
                    callback: function (this: any, value: any) {
                        const label = this.getLabelForValue(value);
                        const date = new Date(label);
                        const day = date.getDate();
                        const month = date.getMonth();

                        if (day === 1 && month === 0) {
                            return date.getFullYear().toString();
                        }

                        if (day === 1) {
                            return date.toLocaleDateString('fr-FR', { month: 'short' }).replace('.', '');
                        }

                        return day.toString();
                    },
                },
            },
            y: {
                position: 'right' as const,
                grid: {
                    display: false,
                },
                ticks: {
                    color: '#6b7280',
                    font: {
                        size: 11,
                    },
                    callback: function (value: any) {
                        return formatPrice(value);
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
        <>
            {loading ? (
                <div className="h-full flex items-center justify-center">
                    <div className="loading-pulse text-gray-400">Loading chart...</div>
                </div>
            ) : (
                <div className="h-full w-full">
                    <Line data={chartData} options={options} />
                </div>
            )}
        </>
    );
};

export default PriceChart;
