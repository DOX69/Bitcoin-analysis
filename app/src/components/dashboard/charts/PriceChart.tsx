'use client';

import React, { useMemo } from 'react';
import {
    Chart as ChartJS,
    type ChartData,
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
import type { ScriptableContext, TooltipItem } from 'chart.js';
import { Chart } from 'react-chartjs-2';
import { BitcoinPrice } from '@/lib/schemas';
import {
    formatPrice,
    formatDate,
    getCalendarDateTimestamp,
    parseCalendarDate,
} from '@/lib/format-utils';
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
    showMacd?: boolean;
    showSma?: boolean;
    showEma?: boolean;
    scaleType?: 'linear' | 'logarithmic';
}

type SupportedChartType = 'line' | 'bar' | 'candlestick';
type ChartPoint = { x: number; y: number };
type FinancialChartPoint = { x: number; o: number; h: number; l: number; c: number };
type ChartDataPoint = ChartPoint | FinancialChartPoint;
type CandlestickColorSet = { up: string; down: string; unchanged: string };
type CandlestickDataset = {
    type: 'candlestick';
    label: string;
    data: FinancialChartPoint[];
    backgroundColors: CandlestickColorSet;
    borderColors: CandlestickColorSet;
    wickColors: CandlestickColorSet;
    yAxisID: string;
};
type LineScriptableContext = ScriptableContext<'line'>;
type BarScriptableContext = ScriptableContext<'bar'>;
type ChartTooltipItem = TooltipItem<SupportedChartType>;

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null;
}

function getNumberProperty(value: unknown, property: string): number | undefined {
    if (!isRecord(value)) return undefined;
    const propertyValue = value[property];
    return typeof propertyValue === 'number' ? propertyValue : undefined;
}

function getParsedY(item: ChartTooltipItem): number | undefined {
    return getNumberProperty(item.parsed, 'y');
}

function getRawX(value: unknown): number | undefined {
    return getNumberProperty(value, 'x');
}

const PriceChart: React.FC<PriceChartProps> = ({
    data,
    loading = false,
    showRsi = false,
    type = 'line',
    currencySymbol = '$',
    showMacd = false,
    showSma = false,
    showEma = false,
    scaleType = 'linear'
}) => {
    const { sanitizedData, shouldSmooth } = useMemo(() => {
        const sanitized = data.map((item: BitcoinPrice) => {
            const date = parseCalendarDate(item.date);
            const isProblematic = item.low <= 0 || (
                date.getUTCFullYear() === 2017 &&
                date.getUTCMonth() === 3 &&
                date.getUTCDate() === 1 &&
                item.low < 100
            );

            if (isProblematic) {
                const values = [item.open, item.high, item.close].sort((a, b) => a - b);
                const median = values[1];
                return { ...item, low: median };
            }
            return item;
        });

        let smooth = false;
        if (data.length > 1) {
            const start = getCalendarDateTimestamp(data[0].date);
            const end = getCalendarDateTimestamp(data[data.length - 1].date);
            const yearsDiff = (end - start) / (1000 * 60 * 60 * 24 * 365);
            smooth = yearsDiff >= 2;
        }

        return { sanitizedData: sanitized, shouldSmooth: smooth };
    }, [data]);

    const rsiPoints = useMemo(() => {
        if (!shouldSmooth) {
            return sanitizedData.filter(item => item.rsi !== null && item.rsi !== undefined).map((item: BitcoinPrice) => ({
                x: getCalendarDateTimestamp(item.date),
                y: item.rsi!
            }));
        }

        const monthlyGroups: Record<string, { sum: number, count: number, date: number }> = {};
        sanitizedData.forEach((item: BitcoinPrice) => {
            if (item.rsi === null || item.rsi === undefined) return;

            const d = parseCalendarDate(item.date);
            const year = d.getUTCFullYear();
            const month = d.getUTCMonth();
            const key = `${year}-${month}`;
            if (!monthlyGroups[key]) {
                monthlyGroups[key] = {
                    sum: 0,
                    count: 0,
                    date: Date.UTC(year, month, 15)
                };
            }
            monthlyGroups[key].sum += item.rsi;
            monthlyGroups[key].count += 1;
        });

        return Object.values(monthlyGroups)
            .sort((a, b) => a.date - b.date)
            .map(m => ({
                x: m.date,
                y: m.sum / m.count
            }));
    }, [sanitizedData, shouldSmooth]);

    const candlestickDataset: CandlestickDataset = {
        type: 'candlestick',
        label: `Bitcoin Price (${currencySymbol})`,
        data: sanitizedData.map((item) => ({
            x: getCalendarDateTimestamp(item.date),
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
    };

    const chartData: ChartData<SupportedChartType, ChartDataPoint[]> = {
        datasets: [
            ...(type === 'line' ? [{
                type: 'line' as const,
                label: `Bitcoin Price (${currencySymbol})`,
                data: sanitizedData.map((item) => ({
                    x: getCalendarDateTimestamp(item.date),
                    y: item.close
                })),
                borderColor: 'rgba(255, 107, 53, 1)',
                borderWidth: 1.5,
                backgroundColor: (context: LineScriptableContext) => {
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
            }] : [candlestickDataset]),
            ...(showRsi ? [{
                type: 'line' as const,
                label: 'RSI',
                data: rsiPoints,
                borderColor: '#ffffff',
                borderWidth: 1.5,
                backgroundColor: (context: LineScriptableContext) => {
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
            ...(showSma ? [
                {
                    type: 'line' as const,
                    label: 'SMA 7',
                    data: sanitizedData.filter(item => item.sma_7 !== null && item.sma_7 !== undefined).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item.sma_7! })),
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
                    data: sanitizedData.filter(item => item.sma_50 !== null && item.sma_50 !== undefined).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item.sma_50! })),
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
                    data: sanitizedData.filter(item => item.sma_200 !== null && item.sma_200 !== undefined).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item.sma_200! })),
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
                    data: sanitizedData.filter(item => item.ema_7 !== null && item.ema_7 !== undefined).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item.ema_7! })),
                    borderColor: 'rgba(56, 189, 248, 0.6)',
                    borderDash: [2, 2],
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1,
                    yAxisID: 'y',
                    spanGaps: false,
                },
                {
                    type: 'line' as const,
                    label: 'EMA 50',
                    data: sanitizedData.filter(item => item.ema_50 !== null && item.ema_50 !== undefined).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item.ema_50! })),
                    borderColor: 'rgba(168, 85, 247, 0.6)',
                    borderDash: [2, 2],
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1,
                    yAxisID: 'y',
                    spanGaps: false,
                },
                {
                    type: 'line' as const,
                    label: 'EMA 200',
                    data: sanitizedData.filter(item => item.ema_200 !== null && item.ema_200 !== undefined).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item.ema_200! })),
                    borderColor: 'rgba(236, 72, 153, 0.6)',
                    borderDash: [2, 2],
                    borderWidth: 2,
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
                    data: sanitizedData.filter(item => item.macd !== null && item.macd !== undefined).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item.macd! })),
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
                    data: sanitizedData.filter(item => item.macd_signal !== null && item.macd_signal !== undefined).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item.macd_signal! })),
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
                    data: sanitizedData.filter(item => item.macd_hist !== null && item.macd_hist !== undefined).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item.macd_hist! })),
                    backgroundColor: (context: BarScriptableContext) => {
                        const value = getNumberProperty(context.raw, 'y');
                        return value !== undefined && value >= 0
                            ? 'rgba(34, 197, 94, 0.5)'
                            : 'rgba(239, 68, 68, 0.5)';
                    },
                    barPercentage: 0.8,
                    categoryPercentage: 0.9,
                    yAxisID: 'y2',
                }
            ] : [])
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
                filter: function (tooltipItem: ChartTooltipItem, index: number, tooltipItems: ChartTooltipItem[]) {
                    // Deduplicate: only show first item for each dataset label
                    const label = tooltipItem.dataset.label;
                    const firstIndex = tooltipItems.findIndex((item) => item.dataset.label === label);
                    return index === firstIndex;
                },
                callbacks: {
                    title: function (context: ChartTooltipItem[]) {
                        const firstItem = context[0];
                        const rawTimestamp = getRawX(firstItem?.raw);
                        if (rawTimestamp !== undefined) {
                            return formatDate(new Date(rawTimestamp).toISOString());
                        }
                        return formatDate(firstItem?.label ?? '');
                    },
                    label: function (context: ChartTooltipItem) {
                        const value = getParsedY(context);
                        const label = context.dataset.label ?? '';
                        if (label === 'RSI') {
                            return value === undefined ? 'RSI: n/a' : `RSI: ${Math.round(value)}`;
                        }
                        if (['MACD', 'Signal', 'Histogram'].includes(label)) {
                            return value === undefined
                                ? `${label}: n/a`
                                : `${label}: ${value.toFixed(2)}`;
                        }
                        if (['SMA 7', 'SMA 50', 'SMA 200', 'EMA 7', 'EMA 50', 'EMA 200'].includes(label)) {
                            return value === undefined
                                ? `${label}: n/a`
                                : `${label}: ${currencySymbol}${formatPrice(value)}`;
                        }
                        if (context.dataset.type === 'candlestick') {
                            const raw = context.raw;
                            return [
                                `O: ${currencySymbol}${formatPrice(getNumberProperty(raw, 'o') ?? 0)}`,
                                `H: ${currencySymbol}${formatPrice(getNumberProperty(raw, 'h') ?? 0)}`,
                                `L: ${currencySymbol}${formatPrice(getNumberProperty(raw, 'l') ?? 0)}`,
                                `C: ${currencySymbol}${formatPrice(getNumberProperty(raw, 'c') ?? 0)}`
                            ];
                        }
                        return value === undefined ? `${currencySymbol}n/a` : currencySymbol + formatPrice(value);
                    },
                },
            },
        },
        scales: {
            x: {
                type: 'timeseries' as const,
                offset: true,
                time: {
                    unit: shouldSmooth ? ('month' as const) : ('day' as const),
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
                stackWeight: (showRsi ? 1 : 0) + (showMacd ? 2 : 0) + 3,
                grid: {
                    display: false,
                },
                ticks: {
                    color: '#6b7280',
                    font: {
                        size: 11,
                    },
                    callback: function (value: number | string) {
                        return currencySymbol + formatPrice(Number(value));
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
                    stackWeight: 2,
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
            mode: 'x' as const,
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
                    <Chart
                        type={type === 'candlestick' ? 'candlestick' : 'line'}
                        data={chartData}
                        options={options}
                    />
                </div>
            )}
        </>
    );
};

export default PriceChart;
