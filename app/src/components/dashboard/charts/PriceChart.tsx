'use client';

import React from 'react';
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
import type { Scale, ScriptableContext, TooltipItem } from 'chart.js';
import { Chart } from 'react-chartjs-2';
import { INDICATORS } from '@/lib/indicators';
import { BitcoinPrice } from '@/lib/schemas';
import {
    formatPrice,
    formatPriceDate,
    getCalendarDateTimestamp,
} from '@/lib/format-utils';
import { CandlestickController, CandlestickElement } from 'chartjs-chart-financial';
import { Spinner } from '@/components/ui/spinner';
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

function formatAccessiblePrice(value: number, currencySymbol: string): string {
    return `${currencySymbol}${value.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    })}`;
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
    const useMonthlyTicks = data.length > 1 &&
        getCalendarDateTimestamp(data[data.length - 1].date) - getCalendarDateTimestamp(data[0].date) >= 2 * 365 * 24 * 60 * 60 * 1000;
    const rsiPoints = data.filter(item => item.rsi != null).map(item => ({
        x: getCalendarDateTimestamp(item.date),
        y: item.rsi!,
    }));

    const candlestickDataset: CandlestickDataset = {
        type: 'candlestick',
        label: `Bitcoin Price (${currencySymbol})`,
        data: data.map((item) => ({
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
                data: data.map((item) => ({
                    x: getCalendarDateTimestamp(item.date),
                    y: item.close
                })),
                borderColor: '#F7931A',
                borderWidth: 1.5,
                backgroundColor: (context: LineScriptableContext) => {
                    const ctx = context.chart.ctx;
                    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                    gradient.addColorStop(0, 'rgba(247, 147, 26, 0.15)');
                    gradient.addColorStop(0.5, 'rgba(247, 183, 49, 0.05)');
                    gradient.addColorStop(1, 'rgba(255, 165, 0, 0.0)');
                    return gradient;
                },
                fill: true,
                tension: 0.4,
                pointRadius: data.length === 1 ? 4 : 0,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: '#FFA42D',
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2,
                yAxisID: 'y',
            }] : [candlestickDataset]),
            ...(showRsi ? [{
                type: 'line' as const,
                label: INDICATORS.rsi.series[0].label,
                data: rsiPoints,
                borderColor: INDICATORS.rsi.series[0].color,
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
            ...(['sma', 'ema'] as const).flatMap((id) => {
                if (!(id === 'sma' ? showSma : showEma)) return [];
                return INDICATORS[id].series.map((series) => ({
                    type: 'line' as const,
                    label: series.label,
                    data: data.filter(item => item[series.key] != null).map(item => ({
                        x: getCalendarDateTimestamp(item.date), y: item[series.key]!,
                    })),
                    borderColor: series.color,
                    ...(id === 'ema' ? { borderDash: [2, 2] } : {}),
                    borderWidth: id === 'ema' ? 2 : 1,
                    pointRadius: 0,
                    tension: 0.1,
                    yAxisID: 'y',
                    spanGaps: false,
                }));
            }),
            ...(showMacd ? [
                {
                    type: 'line' as const,
                    label: INDICATORS.macd.series[0].label,
                    data: data.filter(item => item[INDICATORS.macd.series[0].key] != null).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item[INDICATORS.macd.series[0].key]! })),
                    borderColor: INDICATORS.macd.series[0].color,
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.4,
                    yAxisID: 'y2',
                    spanGaps: false,
                },
                {
                    type: 'line' as const,
                    label: INDICATORS.macd.series[1].label,
                    data: data.filter(item => item[INDICATORS.macd.series[1].key] != null).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item[INDICATORS.macd.series[1].key]! })),
                    borderColor: INDICATORS.macd.series[1].color,
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.4,
                    yAxisID: 'y2',
                    spanGaps: false,
                },
                {
                    type: 'bar' as const,
                    label: INDICATORS.macd.series[2].label,
                    data: data.filter(item => item[INDICATORS.macd.series[2].key] != null).map(item => ({ x: getCalendarDateTimestamp(item.date), y: item[INDICATORS.macd.series[2].key]! })),
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
                            return formatPriceDate({ date: new Date(rawTimestamp).toISOString(), aggregation: data[0]?.aggregation });
                        }
                        return formatPriceDate({ date: firstItem?.label ?? '', aggregation: data[0]?.aggregation });
                    },
                    label: function (context: ChartTooltipItem) {
                        const value = getParsedY(context);
                        const label = context.dataset.label ?? '';
                        if (label === 'RSI') {
                            return value === undefined ? 'RSI: n/a' : `RSI: ${Math.round(value)}`;
                        }
                        if (INDICATORS.macd.series.some(series => series.label === label)) {
                            return value === undefined
                                ? `${label}: n/a`
                                : `${label}: ${value.toFixed(2)}`;
                        }
                        if ([...INDICATORS.sma.series, ...INDICATORS.ema.series].some(series => series.label === label)) {
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
                    unit: useMonthlyTicks ? ('month' as const) : ('day' as const),
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
                    color: '#b8b8b8',
                    maxTicksLimit: 8,
                    autoSkip: true,
                    font: {
                        size: 11,
                    },
                },
            },
            y: {
                type: scaleType,
                afterBuildTicks: (axis: Scale) => {
                    if (scaleType !== 'logarithmic') return;
                    const minimumGap = Math.log10(axis.max / axis.min) / 5;
                    let previous = -Infinity;
                    axis.ticks = axis.ticks.filter(({ value }) => {
                        const position = Math.log10(value);
                        if (position - previous < minimumGap) return false;
                        previous = position;
                        return true;
                    });
                },
                display: true,
                position: 'right' as const,
                stack: 'demo',
                stackWeight: (showRsi ? 1 : 0) + (showMacd ? 2 : 0) + 3,
                grid: {
                    display: false,
                },
                ticks: {
                    color: '#b8b8b8',
                    maxTicksLimit: 6,
                    autoSkipPadding: 16,
                    font: {
                        size: 11,
                    },
                    callback: function (value: number | string, index: number) {
                        if (index === 0 && (showRsi || showMacd)) return '';
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
                        color: '#b8b8b8',
                        stepSize: 50,
                        callback: (value: number | string) => showMacd && Number(value) === 0 ? '' : value,
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
                        color: '#b8b8b8',
                        maxTicksLimit: 4,
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

    const indicatorColumns = [
        ...(showSma ? INDICATORS.sma.series : []),
        ...(showEma ? INDICATORS.ema.series : []),
        ...(showMacd ? INDICATORS.macd.series : []),
    ];

    return (
        <>
            {loading ? (
                <div className="flex h-full items-center justify-center gap-2">
                    <Spinner className="text-primary" />
                    <span className="text-muted-foreground">Loading chart...</span>
                </div>
            ) : (
                <div className="w-full" key={`${type}-${showRsi}-${data.length}`}>
                    {(showSma || showEma || showRsi || showMacd) && (
                        <ul aria-label="Active chart series" className="mb-3 flex flex-wrap gap-x-4 gap-y-2 px-2 text-xs text-muted-foreground md:px-0">
                            {chartData.datasets.map((dataset) => (
                                <li key={dataset.label} className="flex items-center gap-1.5">
                                    <span aria-hidden="true" className="w-4 shrink-0 border-t-2" style={{ borderColor: typeof dataset.borderColor === 'string' ? dataset.borderColor : '#b8b8b8', borderTopStyle: 'borderDash' in dataset && dataset.borderDash?.length ? 'dashed' : 'solid' }} />
                                    {dataset.label}
                                </li>
                            ))}
                        </ul>
                    )}
                    <div className="h-[var(--mobile-chart-height)] w-full md:h-[360px]" style={{ '--mobile-chart-height': `${320 + (showRsi ? 90 : 0) + (showMacd ? 110 : 0)}px` } as React.CSSProperties} aria-hidden="true">
                        <Chart
                            type={type === 'candlestick' ? 'candlestick' : 'line'}
                            data={chartData}
                            options={options}
                        />
                    </div>
                    {data.length > 0 && (
                        <>
                            <div className="sr-only md:not-sr-only md:mt-3 md:flex md:flex-wrap md:gap-x-5 md:gap-y-1 md:border-t md:border-border md:pt-3 md:text-xs md:text-muted-foreground">
                                <span>Period close · {formatPriceDate(data[data.length - 1])} <strong className="font-semibold tabular-nums text-foreground">{currencySymbol || '$'}{formatPrice(data[data.length - 1].close)}</strong></span>
                                <span>Period high <strong className="font-semibold tabular-nums text-foreground">{currencySymbol || '$'}{formatPrice(Math.max(...data.map((item) => item.high)))}</strong></span>
                                <span>Period low <strong className="font-semibold tabular-nums text-foreground">{currencySymbol || '$'}{formatPrice(Math.min(...data.map((item) => item.low)))}</strong></span>
                            </div>
                            <div className="sr-only">
                                <table aria-label="Recent Bitcoin market data">
                                    <caption>Ten most recent Bitcoin market records for the selected filters.</caption>
                                    <thead>
                                        <tr>
                                            <th scope="col">Date</th>
                                            <th scope="col">Close</th>
                                            <th scope="col">High</th>
                                            <th scope="col">Low</th>
                                            <th scope="col">RSI</th>
                                            {indicatorColumns.map((column) => <th key={column.key} scope="col">{column.label}</th>)}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.slice(-10).reverse().map((item) => (
                                            <tr key={item.date}>
                                                <th scope="row">{formatPriceDate(item)}</th>
                                                <td>{formatAccessiblePrice(item.close, currencySymbol || '$')}</td>
                                                <td>{formatAccessiblePrice(item.high, currencySymbol || '$')}</td>
                                                <td>{formatAccessiblePrice(item.low, currencySymbol || '$')}</td>
                                                <td>{item.rsi == null ? 'Unavailable' : item.rsi.toFixed(1)}</td>
                                                {indicatorColumns.map((column) => {
                                                    const value = item[column.key];
                                                    return <td key={column.key}>{typeof value !== 'number' ? 'Unavailable' : column.price ? formatAccessiblePrice(value, currencySymbol || '$') : value.toFixed(2)}</td>;
                                                })}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </div>
            )}
        </>
    );
};

export default PriceChart;
