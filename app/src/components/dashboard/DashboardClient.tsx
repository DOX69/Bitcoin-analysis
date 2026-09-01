'use client';

import React, { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ChartCandlestick, ChevronRight, Info, LineChart, TrendingDown, TrendingUp } from 'lucide-react';
import {
    DashboardHeader,
    StatsPanel,
    StatCard,
    DateRangePicker,
    PriceChart,
} from '@/components/dashboard';
import type { BitcoinMetrics, BitcoinPrice } from '@/lib/schemas';
import type { Currency } from '@/lib/bitcoin-data-server';
import { formatPriceWithCurrency } from '@/lib/format-utils';
import IndicatorSelector from '@/components/dashboard/IndicatorSelector';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface DashboardClientProps {
    initialMetrics: BitcoinMetrics;
    initialHistoricalData: BitcoinPrice[];
    selectedTime: string;
    startDate: string;
    endDate: string;
    selectedCurrency: Currency;
}

const TIME_FILTERS = [
    { label: '1W', value: '1w' },
    { label: '1M', value: '1m' },
    { label: '6M', value: '6m' },
    { label: '1Y', value: '1y' },
    { label: 'YTD', value: 'ytd' },
    { label: 'ALL', value: 'all' },
] as const;

const CURRENCY_SYMBOLS: Record<Currency, string> = {
    USD: '$',
    EUR: '€',
    CHF: 'Fr',
};

export default function DashboardClient({
    initialMetrics,
    initialHistoricalData,
    selectedTime: initialTime,
    selectedCurrency: initialCurrency,
}: DashboardClientProps) {
    const router = useRouter();
    const searchParams = useSearchParams();
    const startDate = searchParams.get('start') || '';
    const endDate = searchParams.get('end') || '';
    const dateRangeKey = `${startDate}:${endDate}`;
    const [selectedIndicators, setSelectedIndicators] = useState<Set<string>>(new Set());
    const [isRightPanelOpen, setIsRightPanelOpen] = useState(true);
    const [chartType, setChartType] = useState<'line' | 'candlestick'>('line');
    const [scaleType, setScaleType] = useState<'linear' | 'logarithmic'>('linear');

    const periodStats = initialHistoricalData.length > 0
        ? {
            start: initialHistoricalData[0],
            end: initialHistoricalData[initialHistoricalData.length - 1],
            high: Math.max(...initialHistoricalData.map((data) => data.high)),
            low: Math.min(...initialHistoricalData.map((data) => data.low)),
        }
        : null;

    const variation = periodStats
        ? ((periodStats.end.close - periodStats.start.open) / periodStats.start.open) * 100
        : 0;

    const handleTimeFilter = (value: string) => {
        const params = new URLSearchParams(searchParams.toString());
        params.set('time', value);
        params.delete('start');
        params.delete('end');
        router.push(`?${params.toString()}`);
    };

    const handleRangeChange = (start: string, end: string) => {
        const params = new URLSearchParams(searchParams.toString());
        if (start) params.set('start', start); else params.delete('start');
        if (end) params.set('end', end); else params.delete('end');
        if (start && end) params.set('time', 'custom');
        router.push(`?${params.toString()}`);
    };

    const handleCurrencyFilter = (value: Currency) => {
        const params = new URLSearchParams(searchParams.toString());
        params.set('currency', value);
        router.push(`?${params.toString()}`);
    };

    const handleToggleIndicator = (indicator: string) => {
        setSelectedIndicators((previous) => {
            const next = new Set(previous);
            if (next.has(indicator)) next.delete(indicator); else next.add(indicator);
            return next;
        });
    };

    const toggleItemClassName = 'min-h-11 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground';

    return (
        <div className="flex min-h-screen flex-col bg-background font-sans text-foreground">
            <DashboardHeader />

            <main className="flex flex-1 overflow-hidden">
                <div className="flex h-[calc(100vh-64px)] flex-1 flex-col overflow-hidden">
                    <div className="flex-1 overflow-y-auto p-4 md:p-6">
                        <div className="mb-5">
                            <div>
                                <h1 className="text-2xl font-semibold tracking-tight text-white">Bitcoin market dashboard</h1>
                                <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
                                    Price history and technical indicators for the selected period.
                                </p>
                            </div>
                        </div>

                        <div className="mb-6 grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto_auto]">
                            <section className="min-w-0 rounded-xl bg-card p-3" aria-labelledby="timeline-controls">
                                <h2 id="timeline-controls" className="mb-2 text-xs font-medium text-muted-foreground">Timeline</h2>
                                <div className="flex min-w-0 flex-wrap items-center gap-2">
                                    <ToggleGroup
                                        value={initialTime === 'custom' ? [] : [initialTime]}
                                        onValueChange={(values) => values[0] && handleTimeFilter(values[0])}
                                        variant="outline"
                                        size="sm"
                                        spacing={1}
                                        aria-label="Time range"
                                        className="max-w-full bg-muted/50 p-1"
                                    >
                                        {TIME_FILTERS.map((filter) => (
                                            <ToggleGroupItem key={filter.value} value={filter.value} className={toggleItemClassName}>
                                                {filter.label}
                                            </ToggleGroupItem>
                                        ))}
                                    </ToggleGroup>
                                <DateRangePicker
                                    key={dateRangeKey}
                                    startDate={startDate}
                                    endDate={endDate}
                                    onChange={handleRangeChange}
                                />
                                </div>
                            </section>

                            <section className="rounded-xl bg-card p-3" aria-labelledby="layer-controls">
                                <h2 id="layer-controls" className="mb-2 text-xs font-medium text-muted-foreground">Layers</h2>
                                <IndicatorSelector
                                    selectedIndicators={selectedIndicators}
                                    onToggleIndicator={handleToggleIndicator}
                                />
                            </section>

                            <section className="rounded-xl bg-card p-3" aria-labelledby="display-controls">
                                <h2 id="display-controls" className="mb-2 text-xs font-medium text-muted-foreground">Display</h2>
                                <div className="flex flex-wrap items-center gap-2">
                                <ToggleGroup
                                    value={[scaleType]}
                                    onValueChange={(values) => values[0] && setScaleType(values[0] as typeof scaleType)}
                                    variant="outline"
                                    size="sm"
                                    spacing={1}
                                    aria-label="Scale type"
                                    className="bg-muted/50 p-1"
                                >
                                    <ToggleGroupItem value="linear" className={toggleItemClassName}>Linear</ToggleGroupItem>
                                    <ToggleGroupItem value="logarithmic" className={toggleItemClassName}>Log</ToggleGroupItem>
                                </ToggleGroup>
                                <Tooltip>
                                    <TooltipTrigger render={<Button variant="ghost" size="icon" aria-label="Scale type information" />}>
                                        <Info />
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        Useful for viewing long-term growth where percentage changes matter more than dollar amounts.
                                    </TooltipContent>
                                </Tooltip>
                                <ToggleGroup
                                    value={[initialCurrency]}
                                    onValueChange={(values) => values[0] && handleCurrencyFilter(values[0] as Currency)}
                                    variant="outline"
                                    size="sm"
                                    spacing={1}
                                    aria-label="Currency"
                                    className="bg-muted/50 p-1"
                                >
                                    {(['USD', 'CHF', 'EUR'] as const).map((currency) => (
                                        <ToggleGroupItem key={currency} value={currency} className={toggleItemClassName}>
                                            {currency}
                                        </ToggleGroupItem>
                                    ))}
                                </ToggleGroup>
                                <ToggleGroup
                                    value={[chartType]}
                                    onValueChange={(values) => values[0] && setChartType(values[0] as typeof chartType)}
                                    variant="outline"
                                    size="sm"
                                    spacing={1}
                                    aria-label="Chart type"
                                    className="bg-muted/50 p-1"
                                >
                                    <ToggleGroupItem value="line" aria-label="Line Chart" className={toggleItemClassName}>
                                        <LineChart />
                                    </ToggleGroupItem>
                                    <ToggleGroupItem value="candlestick" aria-label="Candlestick Chart" className={toggleItemClassName}>
                                        <ChartCandlestick />
                                    </ToggleGroupItem>
                                </ToggleGroup>
                                </div>
                            </section>
                        </div>

                        <Card className="mb-6 bg-card">
                            <CardContent className="p-4 md:p-6">
                                <PriceChart
                                    data={initialHistoricalData}
                                    loading={false}
                                    showRsi={selectedIndicators.has('rsi')}
                                    showMacd={selectedIndicators.has('macd')}
                                    showSma={selectedIndicators.has('sma')}
                                    showEma={selectedIndicators.has('ema')}
                                    type={chartType}
                                    currencySymbol={CURRENCY_SYMBOLS[initialCurrency] || '$'}
                                    scaleType={scaleType}
                                />
                            </CardContent>
                        </Card>

                        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
                            <StatCard
                                title="Current Bitcoin price"
                                value={formatPriceWithCurrency(initialMetrics.currentPrice, initialCurrency)}
                                trend={initialMetrics.change24h >= 0 ? 'up' : 'down'}
                                subtitle={`24h change ${initialMetrics.changePercent24h >= 0 ? '+' : ''}${initialMetrics.changePercent24h.toFixed(2)}%`}
                            />
                            <StatCard
                                title={`Variation (${initialTime.toUpperCase()})`}
                                value={`${variation >= 0 ? '+' : ''}${variation.toFixed(2)}%`}
                                trend={variation >= 0 ? 'up' : 'down'}
                            />
                            <StatCard
                                title={`Period high (${initialTime.toUpperCase()})`}
                                value={periodStats ? formatPriceWithCurrency(periodStats.high, initialCurrency) : '-'}
                                trend="neutral"
                                icon={<TrendingUp />}
                            />
                            <StatCard
                                title={`Period low (${initialTime.toUpperCase()})`}
                                value={periodStats ? formatPriceWithCurrency(periodStats.low, initialCurrency) : '-'}
                                trend="neutral"
                                icon={<TrendingDown />}
                            />
                        </div>

                        <div className="mb-6 xl:hidden">
                            <StatsPanel
                                metrics={initialMetrics}
                                loading={false}
                                currencySymbol={CURRENCY_SYMBOLS[initialCurrency]}
                            />
                        </div>
                    </div>
                </div>

                <div className="hidden h-[calc(100vh-64px)] flex-row overflow-hidden xl:flex">
                    <div className="relative flex h-full w-3 flex-col items-center justify-center px-1 text-primary">
                        <Separator orientation="vertical" className="h-32 bg-current" />
                        <Button
                            variant="outline"
                            size="icon-xs"
                            onClick={() => setIsRightPanelOpen(!isRightPanelOpen)}
                            aria-label={isRightPanelOpen ? 'Close statistics panel' : 'Open statistics panel'}
                            className="absolute top-1/2 -translate-y-1/2 rounded-full border-primary bg-card hover:bg-primary hover:text-primary-foreground"
                        >
                            <ChevronRight className={cn('transition-transform', !isRightPanelOpen && 'rotate-180')} />
                        </Button>
                    </div>
                    {isRightPanelOpen && (
                        <div className="w-[360px] overflow-hidden">
                            <div className="h-full overflow-y-auto">
                                <StatsPanel
                                    metrics={initialMetrics}
                                    loading={false}
                                    currencySymbol={CURRENCY_SYMBOLS[initialCurrency]}
                                />
                            </div>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
