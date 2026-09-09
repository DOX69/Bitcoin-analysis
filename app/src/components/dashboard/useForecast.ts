'use client';

import { useEffect, useState } from 'react';
import { z } from 'zod';
import type { Currency } from '@/lib/bitcoin-data-server';
import type { PriceChartProjection } from './charts/PriceChart';

const date = z.iso.date();
const point = z.object({ horizonWeeks: z.number().int().min(1).max(52), targetDate: date, q25: z.number().positive(), q50: z.number().positive(), q75: z.number().positive() }).refine(p => p.q25 <= p.q50 && p.q50 <= p.q75);
const responseSchema = z.object({
    status: z.enum(['available', 'absent', 'stale', 'withdrawn', 'invalid']),
    model: z.object({ id: z.string(), name: z.string() }).nullable(),
    emissions: z.array(z.object({ id: z.string(), emissionDate: date, originWeek: date, originDate: date, status: z.enum(['valid', 'invalidated', 'delayed']), points: z.array(point), fx: z.record(z.string(), z.object({ rate: z.number().positive(), date })) })),
}).refine(value => value.emissions.every(emission => emission.status === 'invalidated' || (emission.points.length === 52 && emission.points.every((p, i) => p.horizonWeeks === i + 1 && Date.parse(p.targetDate) === Date.parse(emission.originDate) + (i + 1) * 7 * 86400000))));

type Response = z.infer<typeof responseSchema>;
type Status = Response['status'] | 'loading' | 'error';

export function useForecast(enabled: boolean, currency: Currency, start: string, end: string) {
    const key = `${currency}:${start}:${end}`;
    const [result, setResult] = useState<{ key: string; status: Status; response?: Response } | null>(null);
    useEffect(() => {
        if (!enabled) return;
        const controller = new AbortController();
        const params = new URLSearchParams({ currency });
        if (end) params.set('asOf', end);
        fetch(`/api/forecast?${params}`, { signal: controller.signal }).then(async response => {
            if (!response.ok) throw new Error('Forecast request failed');
            const parsed = responseSchema.safeParse(await response.json());
            if (!controller.signal.aborted) setResult(parsed.success ? { key, status: parsed.data.status, response: parsed.data } : { key, status: 'invalid' });
        }).catch(() => { if (!controller.signal.aborted) setResult({ key, status: 'error' }); });
        return () => controller.abort();
    }, [enabled, currency, start, end, key]);
    const current = enabled && result?.key === key ? result : null;
    const response = current?.response;
    const emissions = (response?.emissions ?? []).filter(e => !end || e.emissionDate <= end).sort((a, b) => b.emissionDate.localeCompare(a.emissionDate)).slice(0, 3);
    const historicalEnd = end && end < new Date().toISOString().slice(0, 10) ? end : '';
    const projection: PriceChartProjection = { emissions: ['available', 'stale'].includes(current?.status ?? '') ? emissions.filter(e => e.status !== 'invalidated').map(e => ({ id: e.id, issued: e.emissionDate, points: e.points.filter(p => (!start || p.targetDate >= start) && (!historicalEnd || p.targetDate <= historicalEnd)).map(p => ({ date: p.targetDate, low: p.q25, median: p.q50, high: p.q75 })) })).filter(e => e.points.length > 0) : [] };
    return { status: current?.status ?? (enabled ? 'loading' : 'absent'), model: response?.model ?? null, emissions, projection };
}

