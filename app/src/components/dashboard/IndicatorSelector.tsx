'use client';

import React from 'react';
import { BarChart3, ChevronDown } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuCheckboxItem,
    DropdownMenuContent,
    DropdownMenuGroup,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

interface IndicatorSelectorProps {
    selectedIndicators: Set<string>;
    onToggleIndicator: (indicator: string) => void;
}

const INDICATORS = [
    { id: 'rsi', label: 'RSI', description: 'Relative Strength Index' },
    { id: 'macd', label: 'MACD', description: 'Moving Average Convergence Divergence' },
    { id: 'sma', label: '3 SMA', description: '7, 50, 200-day Simple Moving Averages' },
    { id: 'ema', label: '3 EMA', description: '7, 50, 200-day Exponential Moving Averages' },
];

export default function IndicatorSelector({ selectedIndicators, onToggleIndicator }: IndicatorSelectorProps) {
    return (
        <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>
                <BarChart3
                    data-icon="inline-start"
                    className={cn(selectedIndicators.size > 0 ? 'text-primary' : 'text-muted-foreground')}
                />
                <span className={cn(selectedIndicators.size > 0 ? 'text-foreground' : 'text-muted-foreground')}>
                    Indicators
                </span>
                {selectedIndicators.size > 0 && <Badge className="ml-1">{selectedIndicators.size}</Badge>}
                <ChevronDown data-icon="inline-end" />
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end" className="w-72">
                <DropdownMenuGroup>
                    {INDICATORS.map((indicator) => {
                        const isSelected = selectedIndicators.has(indicator.id);

                        return (
                            <DropdownMenuCheckboxItem
                                key={indicator.id}
                                checked={isSelected}
                                onCheckedChange={() => onToggleIndicator(indicator.id)}
                                className="items-start py-3"
                            >
                                <div className="flex flex-col gap-1 text-left">
                                    <span className={cn('text-sm font-semibold', isSelected ? 'text-primary' : 'text-foreground')}>
                                        {indicator.label}
                                    </span>
                                    <span className="truncate text-[11px] text-muted-foreground">
                                        {indicator.description}
                                    </span>
                                </div>
                            </DropdownMenuCheckboxItem>
                        );
                    })}
                </DropdownMenuGroup>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
