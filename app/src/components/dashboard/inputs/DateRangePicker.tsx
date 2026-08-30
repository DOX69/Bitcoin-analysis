'use client';

import React, { useState } from 'react';
import {
    endOfMonth,
    format,
    isValid,
    startOfDay,
    startOfMonth,
    subDays,
    subMonths,
    subYears,
} from 'date-fns';
import { CalendarDays, X } from 'lucide-react';
import type { DateRange } from 'react-day-picker';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';

interface DateRangePickerProps {
    startDate: string;
    endDate: string;
    onChange: (start: string, end: string) => void;
}

type PresetId =
    | 'today'
    | 'yesterday'
    | 'last7'
    | 'last30'
    | 'thisMonth'
    | 'lastMonth'
    | 'last2Year'
    | 'last3Year'
    | 'last5Year'
    | 'last10Year'
    | 'last12Year';

const PRESETS: ReadonlyArray<{ label: string; id: PresetId }> = [
    { label: 'Today', id: 'today' },
    { label: 'Yesterday', id: 'yesterday' },
    { label: 'Last 7 days', id: 'last7' },
    { label: 'Last 30 days', id: 'last30' },
    { label: 'This Month', id: 'thisMonth' },
    { label: 'Last Month', id: 'lastMonth' },
    { label: 'Last 2 Years', id: 'last2Year' },
    { label: 'Last 3 Years', id: 'last3Year' },
    { label: 'Last 5 Years', id: 'last5Year' },
    { label: 'Last 10 Years', id: 'last10Year' },
    { label: 'Last 12 Years', id: 'last12Year' },
];

function parseDate(value: string): Date | undefined {
    if (!value) return undefined;

    const date = new Date(`${value}T00:00:00`);
    return isValid(date) ? date : undefined;
}

function formatRange(start: Date | undefined, end: Date | undefined): string {
    if (!start || !end) return '';
    return `${format(start, 'yyyy-MM-dd')} ~ ${format(end, 'yyyy-MM-dd')}`;
}

function getPresetRange(type: PresetId, today: Date): DateRange {
    switch (type) {
        case 'today':
            return { from: today, to: today };
        case 'yesterday': {
            const yesterday = subDays(today, 1);
            return { from: yesterday, to: yesterday };
        }
        case 'last7':
            return { from: subDays(today, 6), to: today };
        case 'last30':
            return { from: subDays(today, 29), to: today };
        case 'thisMonth':
            return { from: startOfMonth(today), to: endOfMonth(today) };
        case 'lastMonth': {
            const lastMonth = subMonths(today, 1);
            return { from: startOfMonth(lastMonth), to: endOfMonth(lastMonth) };
        }
        case 'last2Year':
            return { from: subYears(today, 2), to: today };
        case 'last3Year':
            return { from: subYears(today, 3), to: today };
        case 'last5Year':
            return { from: subYears(today, 5), to: today };
        case 'last10Year':
            return { from: subYears(today, 10), to: today };
        case 'last12Year':
            return { from: subYears(today, 12), to: today };
    }
}

function getCommittedRange(startDate: string, endDate: string): DateRange {
    return {
        from: parseDate(startDate),
        to: parseDate(endDate),
    };
}

const DateRangePicker: React.FC<DateRangePickerProps> = ({ startDate, endDate, onChange }) => {
    const committedRange = getCommittedRange(startDate, endDate);
    const [isOpen, setIsOpen] = useState(false);
    const [range, setRange] = useState<DateRange>(committedRange);
    const [viewDate, setViewDate] = useState<Date>(committedRange.from ?? new Date());
    const [inputValue, setInputValue] = useState(formatRange(committedRange.from, committedRange.to));

    const resetDraft = () => {
        const nextRange = getCommittedRange(startDate, endDate);
        setRange(nextRange);
        setViewDate(nextRange.from ?? new Date());
        setInputValue(formatRange(nextRange.from, nextRange.to));
    };

    const handleOpenChange = (nextOpen: boolean) => {
        if (!nextOpen) resetDraft();
        setIsOpen(nextOpen);
    };

    const handleDateSelect = (nextRange: DateRange | undefined) => {
        const selectedRange: DateRange = nextRange ?? { from: undefined };
        setRange(selectedRange);
        setInputValue(formatRange(selectedRange.from, selectedRange.to));
    };

    const handleApply = () => {
        if (!range.from || !range.to) return;

        const nextStart = format(range.from, 'yyyy-MM-dd');
        const nextEnd = format(range.to, 'yyyy-MM-dd');
        onChange(nextStart, nextEnd);
        setInputValue(`${nextStart} ~ ${nextEnd}`);
        setIsOpen(false);
    };

    const handleCancel = () => {
        resetDraft();
        setIsOpen(false);
    };

    const selectPreset = (type: PresetId) => {
        const nextRange = getPresetRange(type, startOfDay(new Date()));
        setRange(nextRange);
        setViewDate(nextRange.from ?? new Date());
        setInputValue(formatRange(nextRange.from, nextRange.to));
    };

    const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const value = event.target.value;
        setInputValue(value);

        const [start, end] = value.split('~').map((part) => parseDate(part.trim()));
        if (start && end) {
            setRange({ from: start, to: end });
            setViewDate(start);
        }
    };

    const clearRange = (event: React.MouseEvent) => {
        event.stopPropagation();
        onChange('', '');
        setRange({ from: undefined });
        setInputValue('');
        setIsOpen(false);
    };

    return (
        <Popover open={isOpen} onOpenChange={handleOpenChange}>
            <PopoverTrigger
                render={<div className="flex w-72 items-center gap-2 rounded-lg border border-input bg-card px-3 py-1.5 transition-colors hover:border-primary/50" />}
                nativeButton={false}
            >
                <CalendarDays className="text-muted-foreground" />
                <Input
                    type="text"
                    value={inputValue}
                    onChange={handleInputChange}
                    placeholder="YYYY-MM-DD ~ YYYY-MM-DD"
                    aria-label="Date range"
                    className="h-7 border-0 bg-transparent p-0 text-sm text-foreground shadow-none focus-visible:ring-0"
                />
                {(startDate || inputValue) && (
                    <Button type="button" variant="ghost" size="icon-xs" aria-label="Clear date range" onClick={clearRange}>
                        <X />
                    </Button>
                )}
            </PopoverTrigger>

            <PopoverContent align="start" className="w-auto overflow-hidden p-0">
                <div className="flex">
                    <div className="flex w-32 flex-col gap-1 bg-background p-2">
                        {PRESETS.map((preset) => (
                            <Button
                                key={preset.id}
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="justify-start text-xs text-muted-foreground"
                                onClick={() => selectPreset(preset.id)}
                            >
                                {preset.label}
                            </Button>
                        ))}
                    </div>

                    <Separator orientation="vertical" />

                    <div className="flex flex-col">
                        <Calendar
                            mode="range"
                            selected={range}
                            onSelect={handleDateSelect}
                            month={viewDate}
                            onMonthChange={setViewDate}
                            numberOfMonths={2}
                            captionLayout="dropdown"
                            startMonth={new Date(new Date().getFullYear() - 25, 0)}
                            endMonth={new Date(new Date().getFullYear() + 25, 11)}
                            className="rounded-none"
                        />
                        <Separator />
                        <div className="flex items-center justify-end gap-2 p-3">
                            <Button type="button" variant="ghost" size="sm" onClick={handleCancel}>
                                Cancel
                            </Button>
                            <Button type="button" size="sm" disabled={!range.from || !range.to} onClick={handleApply}>
                                Apply
                            </Button>
                        </div>
                    </div>
                </div>
            </PopoverContent>
        </Popover>
    );
};

export default DateRangePicker;
