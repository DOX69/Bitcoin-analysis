'use client';

import React, { useState } from 'react';
import { ChevronDown, Eye, Info } from 'lucide-react';
import type { BitcoinMetrics } from '@/lib/schemas';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface StatsPanelProps {
    metrics: BitcoinMetrics | null;
    loading?: boolean;
}

type Direction = 'long' | 'short' | 'all';

function formatCurrency(value: number): string {
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    if (value >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
}

const StatsPanel: React.FC<StatsPanelProps> = ({ metrics, loading = false }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [direction, setDirection] = useState<Direction>('all');

    return (
        <aside className="stats-panel transition-all duration-300">
            <Card className="border-0 bg-transparent p-0 shadow-none ring-0">
                <CardHeader className="gap-4 p-0">
                    <div className="flex items-center justify-between gap-4">
                        <CardTitle className="text-lg text-white">Average Deviation Power</CardTitle>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <span>Breakdown</span>
                            <span>Single</span>
                            <span>Smart</span>
                            <Badge>Total</Badge>
                        </div>
                    </div>
                    <Separator />
                </CardHeader>

                <CardContent className="p-0 pt-6">
                    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
                        <CollapsibleTrigger
                            render={<Button variant="outline" className="h-auto w-full justify-between px-4 py-3" />}
                        >
                            <span className="flex items-center gap-3">
                                <span className="flex size-8 items-center justify-center rounded-full bg-gradient-to-br from-energy-orange to-energy-yellow text-xs font-bold text-black">U</span>
                                <span className="text-sm font-medium text-foreground">User Profile</span>
                            </span>
                            <ChevronDown className={cn('text-muted-foreground transition-transform duration-300', isOpen && 'rotate-180')} />
                        </CollapsibleTrigger>

                        <CollapsibleContent className="pt-6">
                            <div className="flex items-center justify-between gap-3">
                                <span className="text-sm text-muted-foreground">Direction</span>
                                <ToggleGroup
                                    value={[direction]}
                                    onValueChange={(values) => values[0] && setDirection(values[0] as Direction)}
                                    variant="outline"
                                    size="sm"
                                    spacing={1}
                                    aria-label="Position direction"
                                >
                                    <ToggleGroupItem value="long" className="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">Long</ToggleGroupItem>
                                    <ToggleGroupItem value="short" className="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">Short</ToggleGroupItem>
                                    <ToggleGroupItem value="all" className="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">All</ToggleGroupItem>
                                </ToggleGroup>
                            </div>

                            <dl className="mt-6 grid grid-cols-2 gap-4">
                                <div>
                                    <dt className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Deposit</dt>
                                    {loading ? <Skeleton className="h-8 w-full bg-muted/70" /> : <dd className="text-xl font-bold text-white">{metrics ? formatCurrency(metrics.currentPrice) : '$0.00'}</dd>}
                                </div>
                                <div>
                                    <dt className="mb-1 flex items-center gap-1 text-xs uppercase tracking-wide text-muted-foreground">
                                        Positions (O/C)
                                        <Tooltip>
                                            <TooltipTrigger render={<Button variant="ghost" size="icon-xs" aria-label="Positions information" />}>
                                                <Info />
                                            </TooltipTrigger>
                                            <TooltipContent>Open and closed positions.</TooltipContent>
                                        </Tooltip>
                                    </dt>
                                    <dd className="text-xl font-bold text-primary">0/0</dd>
                                </div>
                                <div>
                                    <dt className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Win rate</dt>
                                    {loading ? <Skeleton className="h-8 w-full bg-muted/70" /> : <dd className="text-xl font-bold text-white">{metrics?.rsi ? `${metrics.rsi.toFixed(1)}%` : '0.0%'}</dd>}
                                </div>
                                <div>
                                    <dt className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Profit factor</dt>
                                    <dd className="text-xl font-bold text-white">0.00</dd>
                                </div>
                            </dl>

                            <div className="mt-6">
                                <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Risk management</div>
                                <Badge variant="outline">Disabled</Badge>
                            </div>
                            <div className="mt-6">
                                <div className="text-xs uppercase tracking-wide text-muted-foreground">PnL by coin</div>
                            </div>
                            <a href="#" className="mt-6 inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80">
                                <Eye data-icon="inline-start" />
                                View details
                            </a>
                        </CollapsibleContent>
                    </Collapsible>
                </CardContent>
            </Card>
        </aside>
    );
};

export default StatsPanel;
