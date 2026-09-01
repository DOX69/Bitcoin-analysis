import React from 'react';
import type { BitcoinMetrics } from '@/lib/schemas';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

interface StatsPanelProps {
    metrics: BitcoinMetrics | null;
    loading?: boolean;
    currencySymbol?: string;
}

function formatCurrency(value: number, currencySymbol: string): string {
    if (value >= 1e9) return `${currencySymbol}${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `${currencySymbol}${(value / 1e6).toFixed(2)}M`;
    return `${currencySymbol}${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const StatsPanel: React.FC<StatsPanelProps> = ({ metrics, loading = false, currencySymbol = '$' }) => {
    return (
        <aside className="stats-panel" aria-labelledby="market-snapshot-title">
            <Card className="border-0 bg-transparent p-0 shadow-none ring-0">
                <CardHeader className="gap-3 p-0">
                    <div className="flex items-center justify-between gap-3">
                        <h2 id="market-snapshot-title" className="text-lg font-semibold text-white">Market snapshot</h2>
                        <Badge variant="outline" className="border-primary/30 bg-primary/10 text-primary">Daily</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">PostgreSQL, updated daily</p>
                </CardHeader>

                <CardContent className="p-0 pt-6">
                    <dl className="grid grid-cols-2 gap-x-4 gap-y-6">
                        {[
                            ['Current price', metrics ? formatCurrency(metrics.currentPrice, currencySymbol) : 'Unavailable'],
                            ['24h price change', metrics ? formatCurrency(metrics.change24h, currencySymbol) : 'Unavailable'],
                            ['24h high', metrics ? formatCurrency(metrics.high24h, currencySymbol) : 'Unavailable'],
                            ['24h low', metrics ? formatCurrency(metrics.low24h, currencySymbol) : 'Unavailable'],
                            ['24h change', metrics ? `${metrics.changePercent24h >= 0 ? '+' : ''}${metrics.changePercent24h.toFixed(2)}%` : 'Unavailable'],
                            ['RSI (14d)', metrics ? metrics.rsi.toFixed(1) : 'Unavailable'],
                        ].map(([label, value]) => (
                            <div key={label}>
                                <dt className="mb-1 text-xs text-muted-foreground">{label}</dt>
                                {loading ? <Skeleton className="h-6 w-full bg-muted/70" /> : <dd className="font-semibold tabular-nums text-white">{value}</dd>}
                            </div>
                        ))}
                    </dl>
                </CardContent>
            </Card>
        </aside>
    );
};

export default StatsPanel;
