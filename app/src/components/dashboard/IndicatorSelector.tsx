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
import { INDICATORS, DESKTOP_INDICATOR_ORDER, type IndicatorId } from '@/lib/indicators';
import { cn } from '@/lib/utils';

interface IndicatorSelectorProps {
    selectedIndicators: Set<IndicatorId>;
    onToggleIndicator: (indicator: IndicatorId) => void;
}

export default function IndicatorSelector({ selectedIndicators, onToggleIndicator }: IndicatorSelectorProps) {
    return (
        <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="outline" size="sm" className="min-h-11" />}>
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
                    {DESKTOP_INDICATOR_ORDER.map((id) => {
                        const indicator = INDICATORS[id];
                        const isSelected = selectedIndicators.has(id);

                        return (
                            <DropdownMenuCheckboxItem
                                key={id}
                                checked={isSelected}
                                onCheckedChange={() => onToggleIndicator(id)}
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
