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
import MobileChartSettings from '@/components/dashboard/MobileChartSettings';
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
                <div className="flex min-w-0 flex-1 flex-col md:h-[calc(100vh-64px)] md:overflow-hidden">
                    <div className="flex-1 overflow-y-auto p-4 md:p-6">
                        <div className="mb-5 hidden md:block">
                            <div>
                                <h1 className="text-balance text-2xl font-semibold tracking-tight text-white">Bitcoin market dashboard</h1>
                                <p className="mt-1 max-w-2xl text-pretty text-sm text-muted-foreground">
                                    Price history and technical indicators for the selected period.
                                </p>
                            </div>
                        </div>

                        <section className="mb-5 md:hidden" aria-label="Bitcoin price">
                            <h1 className="flex items-center gap-2 text-sm font-medium"><span className="flex size-6 items-center justify-center rounded-full bg-primary text-primary-foreground" aria-hidden="true">₿</span> Bitcoin <span className="text-muted-foreground">BTC</span></h1>
                            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                                <p className="text-[2rem] font-semibold leading-tight tracking-tight tabular-nums">{formatPriceWithCurrency(initialMetrics.currentPrice, initialCurrency)}</p>
                                <span className={cn('flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm font-semibold tabular-nums', variation >= 0 ? 'bg-success/15 text-success' : 'bg-destructive/15 text-destructive')}>
                                    {variation >= 0 ? <TrendingUp className="size-4" /> : <TrendingDown className="size-4" />}
                                    {variation >= 0 ? '+' : ''}{variation.toFixed(2)}%
                                </span>
                            </div>
                            <p className="mt-2 text-xs text-muted-foreground">{initialTime === 'custom' ? `${startDate} – ${endDate}` : `${initialTime.toUpperCase()} performance`} · {initialCurrency}</p>
                        </section>

                        <div className="mb-3 flex min-w-0 items-center gap-1 md:hidden" aria-label="Mobile chart controls">
                            <div className="min-w-0 flex-1 overflow-x-auto rounded-lg bg-muted/60 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                                <ToggleGroup value={initialTime === 'custom' ? [] : [initialTime]} onValueChange={(values) => values[0] && handleTimeFilter(values[0])} aria-label="Chart time range" spacing={0} className="w-full min-w-max p-1">
                                    {TIME_FILTERS.map((filter) => <ToggleGroupItem key={filter.value} value={filter.value} className="min-h-11 min-w-11 flex-1 px-2 text-xs aria-pressed:bg-background aria-pressed:text-primary">{filter.label}</ToggleGroupItem>)}
                                </ToggleGroup>
                            </div>
                            <Button variant="secondary" size="icon" className="size-11" aria-label={chartType === 'line' ? 'Switch to candlestick chart' : 'Switch to line chart'} onClick={() => setChartType(chartType === 'line' ? 'candlestick' : 'line')}>
                                {chartType === 'line' ? <ChartCandlestick className="size-5 text-primary" /> : <LineChart className="size-5 text-primary" />}
                            </Button>
                            <MobileChartSettings selectedIndicators={selectedIndicators} onToggleIndicator={handleToggleIndicator} scaleType={scaleType} onScaleChange={setScaleType} currency={initialCurrency} onCurrencyChange={handleCurrencyFilter} startDate={startDate} endDate={endDate} onRangeChange={handleRangeChange} />
                        </div>

                        <div className="mb-6 hidden gap-3 md:grid xl:grid-cols-2 2xl:grid-cols-[minmax(0,1fr)_auto_auto]">
                            <section className="control-surface" aria-labelledby="timeline-controls">
                                <h2 id="timeline-controls" className="mb-2 text-xs font-medium text-muted-foreground">Timeline</h2>
                                <div className="flex min-w-0 flex-wrap items-center gap-2">
                                    <ToggleGroup
                                        value={initialTime === 'custom' ? [] : [initialTime]}
                                        onValueChange={(values) => values[0] && handleTimeFilter(values[0])}
                                        variant="outline"
                                        size="sm"
                                        spacing={1}
                                        aria-label="Time range"
                                        className="max-w-full flex-wrap bg-muted/50 p-1"
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

                            <section className="control-surface" aria-labelledby="layer-controls">
                                <h2 id="layer-controls" className="mb-2 text-xs font-medium text-muted-foreground">Layers</h2>
                                <IndicatorSelector
                                    selectedIndicators={selectedIndicators}
                                    onToggleIndicator={handleToggleIndicator}
                                />
                            </section>

                            <section className="control-surface xl:col-span-2 2xl:col-span-1" aria-labelledby="display-controls">
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

                        <Card className="mb-5 -mx-2 bg-transparent py-0 ring-0 md:mx-0 md:mb-6 md:bg-card md:py-4 md:ring-1">
                            <CardContent className="px-0 py-0 md:p-6">
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

                        <section className="mb-5 rounded-xl bg-card p-4 md:hidden" aria-label="Period statistics">
                            <h2 className="mb-3 text-sm font-medium">Statistics <span className="ml-1 text-xs text-muted-foreground">{initialTime.toUpperCase()}</span></h2>
                            <dl className="grid grid-cols-3 divide-x divide-border text-xs">
                                <div className="pr-2"><dt className="text-muted-foreground">24h change</dt><dd className={cn('mt-2 font-semibold tabular-nums', initialMetrics.changePercent24h >= 0 ? 'text-success' : 'text-destructive')}>{initialMetrics.changePercent24h >= 0 ? '+' : ''}{initialMetrics.changePercent24h.toFixed(2)}%</dd></div>
                                <div className="px-2"><dt className="text-muted-foreground">Period high</dt><dd className="mt-2 font-semibold tabular-nums">{periodStats ? formatPriceWithCurrency(periodStats.high, initialCurrency) : '-'}</dd></div>
                                <div className="pl-2"><dt className="text-muted-foreground">Period low</dt><dd className="mt-2 font-semibold tabular-nums">{periodStats ? formatPriceWithCurrency(periodStats.low, initialCurrency) : '-'}</dd></div>
                            </dl>
                        </section>

                        <div className="mb-6 hidden gap-4 md:grid md:grid-cols-2 lg:grid-cols-4">
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

                        <div className="mb-6 xl:hidden max-md:[&_.stats-panel]:min-w-0 max-md:[&_.stats-panel]:max-w-none max-md:[&_.stats-panel]:rounded-xl">
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
                        <div className="w-[360px] overflow-hidden border-l border-border/60">
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
