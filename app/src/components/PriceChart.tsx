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
    TimeScale,
    TimeSeriesScale
} from 'chart.js';
import { Chart } from 'react-chartjs-2';
import { BitcoinPrice } from '@/lib/schemas';
import { formatPrice, formatDate, formatTooltipTime } from '@/lib/format-utils';
import { CandlestickController, CandlestickElement } from 'chartjs-chart-financial';
import 'chartjs-adapter-date-fns'; // Import date adapter for potential time scale usage

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
    CandlestickController,
    CandlestickElement,
    TimeScale,
    TimeSeriesScale
);

interface PriceChartProps {
    data: BitcoinPrice[];
    loading?: boolean;
    showRsi?: boolean;
    type?: 'line' | 'candlestick';
}

const PriceChart: React.FC<PriceChartProps> = ({ data, loading = false, showRsi = false, type = 'line' }) => {
    const chartData = {
        datasets: [
            ...(type === 'line' ? [{
                type: 'line' as const,
                label: 'Bitcoin Price (USD)',
                data: data.map((item) => ({
                    x: new Date(item.date).getTime(),
                    y: item.close
                })),
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
                yAxisID: 'y',
            }] : [{
                type: 'candlestick' as const,
                label: 'Bitcoin Price (USD)',
                data: data.map((item) => ({
                    x: new Date(item.date).getTime(),
                    o: item.open,
                    h: item.high,
                    l: item.low,
                    c: item.close
                })),
                backgroundColors: {
                    up: '#F7931A',
                    down: '#ffffff',
                    unchanged: '#F7931A',
                },
                borderColors: {
                    up: '#F7931A',
                    down: '#ffffff',
                    unchanged: '#F7931A',
                },
                wickColors: {
                    up: '#F7931A',
                    down: '#ffffff',
                    unchanged: '#F7931A',
                },
                yAxisID: 'y',
            }]),
            ...(showRsi ? [{
                type: 'line' as const,
                label: 'RSI',
                data: data.map((item) => ({
                    x: new Date(item.date).getTime(),
                    y: item.rsi || 50
                })),
                borderColor: '#ffffff',
                borderWidth: 1.5,
                backgroundColor: (context: any) => {
                    const ctx = context.chart.ctx;
                    const chartArea = context.chart.chartArea;
                    if (!chartArea) return 'transparent';

                    const rsiHeight = showRsi ? chartArea.height * 0.25 : 0;
                    const rsiBottom = chartArea.bottom;
                    const rsiTop = chartArea.bottom - rsiHeight;

                    const gradient = ctx.createLinearGradient(0, rsiBottom, 0, rsiTop);
                    gradient.addColorStop(0, 'rgba(255, 165, 0, 0.4)');
                    gradient.addColorStop(0.3, 'rgba(255, 165, 0, 0.1)');
                    gradient.addColorStop(0.35, 'rgba(255, 255, 255, 0)');
                    gradient.addColorStop(0.65, 'rgba(255, 255, 255, 0)');
                    gradient.addColorStop(0.7, 'rgba(234, 88, 12, 0.1)');
                    gradient.addColorStop(1, 'rgba(234, 88, 12, 0.5)');
                    return gradient;
                },
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointHoverBackgroundColor: '#ffffff',
                yAxisID: 'y1',
            }] : [])
        ],
    };

    const options: any = {
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
                    size: 16,
                    weight: 'bold' as const,
                    family: "'Inter', sans-serif",
                },
                bodyFont: {
                    size: 13,
                    family: "'Inter', sans-serif",
                },
                titleColor: '#ffffff',
                bodyColor: '#9ca3af',
                borderColor: 'rgba(255, 165, 0, 0.3)',
                borderWidth: 1,
                callbacks: {
                    title: function (context: any) {
                        const raw = context[0].raw;
                        if (raw && raw.x) {
                            return formatDate(new Date(raw.x).toISOString());
                        }
                        return formatDate(context[0].label);
                    },
                    label: function (context: any) {
                        if (context.dataset.label === 'RSI') {
                            return `RSI: ${Math.round(context.parsed.y)}`;
                        }
                        if (context.dataset.type === 'candlestick') {
                            const raw = context.raw;
                            return [
                                `O: ${formatPrice(raw.o)}`,
                                `H: ${formatPrice(raw.h)}`,
                                `L: ${formatPrice(raw.l)}`,
                                `C: ${formatPrice(raw.c)}`
                            ];
                        }
                        return '$' + formatPrice(context.parsed.y);
                    },
                },
            },
        },
        scales: {
            x: {
                type: 'timeseries',
                offset: true,
                grid: {
                    display: false,
                    drawBorder: false,
                },
                ticks: {
                    color: '#6b7280',
                    maxTicksLimit: 8,
                    autoSkip: true,
                    font: {
                        size: 11,
                    },
                },
            },
            y: {
                type: 'linear' as const,
                display: true,
                position: 'right' as const,
                stack: 'demo',
                stackWeight: showRsi ? 3 : 1,
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
            ...(showRsi ? {
                y1: {
                    type: 'linear' as const,
                    display: true,
                    position: 'right' as const,
                    stack: 'demo',
                    stackWeight: 1,
                    min: 0,
                    max: 100,
                    offset: false,
                    grid: {
                        display: true,
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false,
                    },
                    ticks: {
                        color: '#6b7280',
                        stepSize: 50,
                        font: {
                            size: 10,
                        }
                    }
                }
            } : {})
        },
        interaction: {
            mode: 'index',
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
                <div className="h-full w-full" key={`${type}-${showRsi}-${data.length}`}>
                    <Chart type={type === 'candlestick' ? 'candlestick' : 'line'} data={chartData as any} options={options} />
                </div>
            )}
        </>
    );
};

export default PriceChart;
