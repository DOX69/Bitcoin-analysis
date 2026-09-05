'use client';

import { Dialog } from '@base-ui/react/dialog';
import { useState, useTransition } from 'react';
import { SlidersHorizontal, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Input } from '@/components/ui/input';
import type { Currency } from '@/lib/bitcoin-data-server';
import { cn } from '@/lib/utils';

interface MobileChartSettingsProps {
    selectedIndicators: Set<string>;
    onToggleIndicator: (indicator: string) => void;
    scaleType: 'linear' | 'logarithmic';
    onScaleChange: (scale: 'linear' | 'logarithmic') => void;
    currency: Currency;
    onCurrencyChange: (currency: Currency) => void;
    startDate: string;
    endDate: string;
    onRangeChange: (start: string, end: string) => void;
}

const indicators = [
    { id: 'sma', label: 'SMA', detail: 'Simple averages · 7, 50, 200 days' },
    { id: 'ema', label: 'EMA', detail: 'Exponential averages · 7, 50, 200 days' },
    { id: 'rsi', label: 'RSI', detail: 'Relative Strength Index' },
    { id: 'macd', label: 'MACD', detail: 'Momentum and signal' },
];

function MobileDateRange({ startDate, endDate, onRangeChange, pending }: Pick<MobileChartSettingsProps, 'startDate' | 'endDate' | 'onRangeChange'> & { pending: boolean }) {
    const [start, setStart] = useState(startDate);
    const [end, setEnd] = useState(endDate);

    return (
        <form className="space-y-3 py-4" onSubmit={(event) => { event.preventDefault(); onRangeChange(start, end); }}>
            <div className="grid grid-cols-2 gap-3">
                <label className="min-w-0 text-xs text-muted-foreground">From<Input type="date" aria-label="Start date" value={start} max={end || undefined} onChange={(event) => setStart(event.target.value)} required className="mt-2 min-h-11 min-w-0 w-full text-base [color-scheme:dark]" /></label>
                <label className="min-w-0 text-xs text-muted-foreground">To<Input type="date" aria-label="End date" value={end} min={start || undefined} onChange={(event) => setEnd(event.target.value)} required className="mt-2 min-h-11 min-w-0 w-full text-base [color-scheme:dark]" /></label>
            </div>
            {start && end && start > end && <p role="alert" className="text-sm text-destructive">End date must be on or after start date.</p>}
            <Button type="submit" className="min-h-11 w-full" disabled={pending || !start || !end || start > end}>{pending ? 'Applying dates…' : 'Apply dates'}</Button>
        </form>
    );
}

export default function MobileChartSettings(props: MobileChartSettingsProps) {
    const [open, setOpen] = useState(false);
    const [pending, startTransition] = useTransition();
    const applyDates = (start: string, end: string) => {
        startTransition(() => {
            props.onRangeChange(start, end);
            setOpen(false);
        });
    };
    const itemClassName = 'min-h-11 px-3 aria-pressed:bg-primary aria-pressed:text-primary-foreground';

    return (
        <Dialog.Root open={open} onOpenChange={setOpen}>
            <Dialog.Trigger render={<Button variant="ghost" size="icon" className="relative size-11" aria-label="Chart settings" />}>
                <SlidersHorizontal className="size-5" />
                {props.selectedIndicators.size > 0 && (
                    <span className="absolute right-0 top-0 flex size-4 items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
                        <span className="sr-only">Active indicators: </span>{props.selectedIndicators.size}
                    </span>
                )}
            </Dialog.Trigger>
            <Dialog.Portal>
                <Dialog.Backdrop className="fixed inset-0 z-50 bg-black/60 transition-opacity duration-200 data-[starting-style]:opacity-0 data-[ending-style]:opacity-0" />
                <Dialog.Popup className="fixed inset-x-0 bottom-0 z-50 mx-auto flex max-h-[90dvh] max-w-lg flex-col rounded-t-2xl bg-card text-foreground outline-none transition-transform duration-200 ease-out data-[starting-style]:translate-y-full data-[ending-style]:translate-y-full">
                    <div aria-hidden="true" className="mx-auto mb-2 mt-3 h-1 w-10 shrink-0 rounded-full bg-muted-foreground/40" />
                    <div className="relative px-6 pb-5 pt-3 text-center">
                        <Dialog.Title className="text-xl font-semibold">Chart settings</Dialog.Title>
                        <Dialog.Description className="mt-1 text-sm text-muted-foreground">Choose your indicators and display.</Dialog.Description>
                        <Dialog.Close render={<Button variant="ghost" size="icon" className="absolute right-2 top-0 size-11" aria-label="Close chart settings" />}><X /></Dialog.Close>
                    </div>
                    <div className="overflow-y-auto overscroll-contain px-5 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
                        <h2 className="mb-2 text-sm font-medium text-muted-foreground">Indicators</h2>
                        <div className="divide-y divide-border rounded-xl bg-background px-4">
                            {indicators.map((indicator) => (
                                <button key={indicator.id} type="button" role="switch" aria-label={indicator.label} aria-checked={props.selectedIndicators.has(indicator.id)} onClick={() => props.onToggleIndicator(indicator.id)} className="flex min-h-16 w-full items-center justify-between gap-3 rounded-lg py-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring">
                                    <span><span className="block text-sm font-medium">{indicator.label}</span><span className="text-xs text-muted-foreground">{indicator.detail}</span></span>
                                    <span aria-hidden="true" className={cn('flex h-6 w-10 shrink-0 items-center rounded-full p-0.5 transition-colors', props.selectedIndicators.has(indicator.id) ? 'bg-primary' : 'bg-muted')}>
                                        <span className={cn('size-5 rounded-full bg-foreground transition-transform', props.selectedIndicators.has(indicator.id) && 'translate-x-4')} />
                                    </span>
                                </button>
                            ))}
                        </div>
                        <h2 className="mb-2 mt-5 text-sm font-medium text-muted-foreground">Display</h2>
                        <div className="divide-y divide-border rounded-xl bg-background px-4">
                            <div className="flex min-h-16 flex-wrap items-center justify-between gap-2 py-2">
                                <span className="text-sm">Scale</span>
                                <ToggleGroup value={[props.scaleType]} onValueChange={(values) => values[0] && props.onScaleChange(values[0] as typeof props.scaleType)} aria-label="Chart scale" spacing={0} className="bg-muted p-1">
                                    <ToggleGroupItem value="linear" className={itemClassName}>Linear</ToggleGroupItem>
                                    <ToggleGroupItem value="logarithmic" className={itemClassName}>Log</ToggleGroupItem>
                                </ToggleGroup>
                            </div>
                            <p className="py-2 text-xs text-muted-foreground">Linear compares price amounts. Log compares percentage changes.</p>
                            <div className="flex min-h-16 flex-wrap items-center justify-between gap-2 py-2">
                                <span className="text-sm">Currency</span>
                                <ToggleGroup value={[props.currency]} onValueChange={(values) => values[0] && props.onCurrencyChange(values[0] as Currency)} aria-label="Chart currency" spacing={0} className="bg-muted p-1">
                                    {(['USD', 'CHF', 'EUR'] as const).map((currency) => <ToggleGroupItem key={currency} value={currency} className={itemClassName}>{currency}</ToggleGroupItem>)}
                                </ToggleGroup>
                            </div>
                        </div>
                        <h2 className="mt-6 text-sm font-medium text-muted-foreground">Custom dates</h2>
                        <MobileDateRange key={`${props.startDate}:${props.endDate}`} startDate={props.startDate} endDate={props.endDate} onRangeChange={applyDates} pending={pending} />
                    </div>
                </Dialog.Popup>
            </Dialog.Portal>
        </Dialog.Root>
    );
}
