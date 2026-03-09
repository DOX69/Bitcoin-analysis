'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    LineController,
    Title,
    Tooltip,
    Legend,
    Filler,
    TimeScale,

    TimeSeriesScale,
    LogarithmicScale
} from 'chart.js';
import { Chart } from 'react-chartjs-2';
import { BitcoinPrice, BitcoinForecast } from '@/lib/schemas';
import { formatPrice, formatDate, formatTooltipTime } from '@/lib/format-utils';
import { CandlestickController, CandlestickElement } from 'chartjs-chart-financial';
import 'chartjs-adapter-date-fns'; // Import date adapter for potential time scale usage

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    LineController,
    Title,
    Tooltip,
    Legend,
    Filler,
    CandlestickController,
    CandlestickElement,
    TimeScale,
    TimeScale,
    TimeSeriesScale,
    LogarithmicScale
);

interface PriceChartProps {
    data: BitcoinPrice[];
    loading?: boolean;
    showRsi?: boolean;
    type?: 'line' | 'candlestick';
    currencySymbol?: string;
    forecastData?: BitcoinForecast[];
    showForecast?: boolean;
    showMacd?: boolean;
    showSma?: boolean;
    showEma?: boolean;
    scaleType?: 'linear' | 'logarithmic';
}

const PriceChart: React.FC<PriceChartProps> = ({
    data,
    loading = false,
    showRsi = false,
    type = 'line',
    currencySymbol = '$',
    forecastData = [],
    showForecast = false,
    showMacd = false,
    showSma = false,
    showEma = false,
    scaleType = 'linear'
}) => {
    const { sanitizedData, shouldSmooth } = useMemo(() => {
        const sanitized = data.map((item: BitcoinPrice) => {
            const isProblematic = item.low <= 0 || (new Date(item.date).getFullYear() === 2017 && new Date(item.date).getMonth() === 3 && new Date(item.date).getDate() === 1 && item.low < 100);

            if (isProblematic) {
                const values = [item.open, item.high, item.close].sort((a, b) => a - b);
                const median = values[1];
                return { ...item, low: median };
            }
            return item;
        });

        let smooth = false;
        if (data.length > 1) {
            const start = new Date(data[0].date);
            const end = new Date(data[data.length - 1].date);
            const yearsDiff = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24 * 365);
            smooth = yearsDiff >= 2;
        }

        return { sanitizedData: sanitized, shouldSmooth: smooth };
    }, [data]);

    const rsiPoints = useMemo(() => {
        if (!shouldSmooth) {
            return sanitizedData.filter(item => item.rsi !== null && item.rsi !== undefined).map((item: BitcoinPrice) => ({
                x: new Date(item.date).getTime(),
                y: item.rsi
            }));
        }

        const monthlyGroups: Record<string, { sum: number, count: number, date: number }> = {};
        sanitizedData.forEach((item: BitcoinPrice) => {
            const d = new Date(item.date);
            const key = `${d.getFullYear()}-${d.getMonth()}`;
            if (!monthlyGroups[key]) {
                monthlyGroups[key] = {
                    sum: 0,
                    count: 0,
                    date: new Date(d.getFullYear(), d.getMonth(), 15).getTime()
                };
            }
            monthlyGroups[key].sum += (item.rsi || 50);
            monthlyGroups[key].count += 1;
        });

        return Object.values(monthlyGroups)
            .sort((a, b) => a.date - b.date)
            .map(m => ({
                x: m.date,
                y: m.sum / m.count
            }));
    }, [sanitizedData, shouldSmooth]);

    const chartData = {
        datasets: [
            ...(type === 'line' ? [{
                type: 'line' as const,
                label: `Bitcoin Price (${currencySymbol})`,
                data: sanitizedData.map((item) => ({
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
                label: `Bitcoin Price (${currencySymbol})`,
                data: sanitizedData.map((item) => ({
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
                data: rsiPoints,
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
            }] : []),
            ...(type === 'line' && showForecast && forecastData.length > 0 ? [
                // Forecast - Regular
                {
                    type: 'line' as const,
                    label: 'Forecast',
                    data: forecastData.map((item) => ({
                        x: new Date(item.date_prices).getTime(),
                        y: item.predicted_close_usd
                    })),
                    borderColor: 'rgba(255, 107, 53, 1)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointHitRadius: 20,
                    yAxisID: 'y',
                },
                // Forecast - Upper
                {
                    type: 'line' as const,
                    label: 'Forecast Upper',
                    data: forecastData.map((item) => ({
                        x: new Date(item.date_prices).getTime(),
                        y: item.predicted_close_usd_upper
                    })),
                    borderColor: 'rgba(255, 255, 255, 0.5)', // White with opacity for bounds
                    borderWidth: 1,
                    borderDash: [3, 3],
                    fill: false,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    pointHitRadius: 20,
                    yAxisID: 'y',
                },
                // Forecast - Lower
                {
                    type: 'line' as const,
                    label: 'Forecast Lower',
                    data: forecastData.map((item) => ({
                        x: new Date(item.date_prices).getTime(),
                        y: item.predicted_close_usd_lower
                    })),
                    borderColor: 'rgba(255, 255, 255, 0.5)', // White with opacity for bounds
                    borderWidth: 1,
                    borderDash: [3, 3],
                    fill: false,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    pointHitRadius: 20,
                    yAxisID: 'y',
                }
            ] : []),
            ...(showSma ? [
                {
                    type: 'line' as const,
                    label: 'SMA 7',
                    data: sanitizedData.filter(item => item.sma_7 !== null && item.sma_7 !== undefined).map(item => ({ x: new Date(item.date).getTime(), y: item.sma_7 })),
                    borderColor: 'rgba(56, 189, 248, 0.8)', // cyan
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.1,
                    yAxisID: 'y',
                    spanGaps: false,
                },
                {
                    type: 'line' as const,
                    label: 'SMA 50',
                    data: sanitizedData.filter(item => item.sma_50 !== null && item.sma_50 !== undefined).map(item => ({ x: new Date(item.date).getTime(), y: item.sma_50 })),
                    borderColor: 'rgba(168, 85, 247, 0.8)', // purple
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.1,
                    yAxisID: 'y',
                    spanGaps: false,
                },
                {
                    type: 'line' as const,
                    label: 'SMA 200',
                    data: sanitizedData.filter(item => item.sma_200 !== null && item.sma_200 !== undefined).map(item => ({ x: new Date(item.date).getTime(), y: item.sma_200 })),
                    borderColor: 'rgba(236, 72, 153, 0.8)', // pink
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.1,
                    yAxisID: 'y',
                    spanGaps: false,
                }
            ] : []),
            ...(showEma ? [
                {
                    type: 'line' as const,
                    label: 'EMA 7',
                    data: sanitizedData.filter(item => item.ema_7 !== null && item.ema_7 !== undefined).map(item => ({ x: new Date(item.date).getTime(), y: item.ema_7 })),
                    borderColor: 'rgba(56, 189, 248, 0.6)',
                    borderDash: [2, 2],
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.1,
                    yAxisID: 'y',
                    spanGaps: false,
                },
                {
                    type: 'line' as const,
                    label: 'EMA 50',
                    data: sanitizedData.filter(item => item.ema_50 !== null && item.ema_50 !== undefined).map(item => ({ x: new Date(item.date).getTime(), y: item.ema_50 })),
                    borderColor: 'rgba(168, 85, 247, 0.6)',
                    borderDash: [2, 2],
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.1,
                    yAxisID: 'y',
                    spanGaps: false,
                },
                {
                    type: 'line' as const,
                    label: 'EMA 200',
                    data: sanitizedData.filter(item => item.ema_200 !== null && item.ema_200 !== undefined).map(item => ({ x: new Date(item.date).getTime(), y: item.ema_200 })),
                    borderColor: 'rgba(236, 72, 153, 0.6)',
                    borderDash: [2, 2],
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.1,
                    yAxisID: 'y',
                    spanGaps: false,
                }
            ] : []),
            ...(showMacd ? [
                {
                    type: 'line' as const,
                    label: 'MACD',
                    data: sanitizedData.filter(item => item.macd !== null && item.macd !== undefined).map(item => ({ x: new Date(item.date).getTime(), y: item.macd })),
                    borderColor: '#3b82f6', // blue-500
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.4,
                    yAxisID: 'y2',
                    spanGaps: false,
                },
                {
                    type: 'line' as const,
                    label: 'Signal',
                    data: sanitizedData.filter(item => item.macd_signal !== null && item.macd_signal !== undefined).map(item => ({ x: new Date(item.date).getTime(), y: item.macd_signal })),
                    borderColor: '#f97316', // orange-500
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.4,
                    yAxisID: 'y2',
                    spanGaps: false,
                },
                {
                    type: 'bar' as const,
                    label: 'Histogram',
                    data: sanitizedData.filter(item => item.macd_hist !== null && item.macd_hist !== undefined).map(item => ({ x: new Date(item.date).getTime(), y: item.macd_hist })),
                    backgroundColor: (context: any) => {
                        const val = context.raw?.y;
                        return val >= 0 ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)';
                    },
                    barPercentage: 0.8,
                    categoryPercentage: 0.9,
                    yAxisID: 'y2',
                }
            ] : [])
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
                mode: 'x' as const,
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
                filter: function (tooltipItem: any, index: number, tooltipItems: any[]) {
                    // Deduplicate: only show first item for each dataset label
                    const label = tooltipItem.dataset.label;
                    const firstIndex = tooltipItems.findIndex((item: any) => item.dataset.label === label);
                    return index === firstIndex;
                },
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
                        if (['MACD', 'Signal', 'Histogram'].includes(context.dataset.label)) {
                            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`;
                        }
                        if (['SMA 7', 'SMA 50', 'SMA 200', 'EMA 7', 'EMA 50', 'EMA 200'].includes(context.dataset.label)) {
                            return `${context.dataset.label}: ${currencySymbol}${formatPrice(context.parsed.y)}`;
                        }
                        if (context.dataset.type === 'candlestick') {
                            const raw = context.raw;
                            return [
                                `O: ${currencySymbol}${formatPrice(raw.o)}`,
                                `H: ${currencySymbol}${formatPrice(raw.h)}`,
                                `L: ${currencySymbol}${formatPrice(raw.l)}`,
                                `C: ${currencySymbol}${formatPrice(raw.c)}`
                            ];
                        }
                        if (context.dataset.label && context.dataset.label.includes('Forecast')) {
                            return `${context.dataset.label.replace('Forecast', '').trim() || 'Forecast'}: ${currencySymbol}${formatPrice(context.parsed.y)}`;
                        }
                        return currencySymbol + formatPrice(context.parsed.y);
                    },
                },
            },
        },
        scales: {
            x: {
                type: 'timeseries',
                offset: true,
                time: {
                    unit: shouldSmooth ? 'month' : 'day',
                    displayFormats: {
                        day: 'MMM d',
                        month: 'MMM yyyy'
                    },
                    tooltipFormat: 'MMM d, yyyy'
                },
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
                type: scaleType,
                display: true,
                position: 'right' as const,
                stack: 'demo',
                stackWeight: (showRsi ? 1 : 0) + (showMacd ? 1 : 0) + 3,
                grid: {
                    display: false,
                },
                ticks: {
                    color: '#6b7280',
                    font: {
                        size: 11,
                    },
                    callback: function (value: any) {
                        return currencySymbol + formatPrice(value);
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
            } : {}),
            ...(showMacd ? {
                y2: {
                    type: 'linear' as const,
                    display: true,
                    position: 'right' as const,
                    stack: 'demo',
                    stackWeight: 1,
                    grid: {
                        display: true,
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false,
                    },
                    ticks: {
                        color: '#6b7280',
                        font: {
                            size: 10,
                        }
                    }
                }
            } : {})
        },
        interaction: {
            mode: 'x',
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
