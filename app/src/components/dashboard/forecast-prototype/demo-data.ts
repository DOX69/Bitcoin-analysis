import type { BitcoinPrice } from '@/lib/schemas';
import type { PriceChartProjection } from '../charts/PriceChart';

const DAY = 86400000;
export const DEMO_DATE = '2026-09-08';
const end = Date.parse(DEMO_DATE);
const start = Date.parse('2024-01-01');
const iso = (time: number) => new Date(time).toISOString().slice(0, 10);
const value = (time: number) => {
    const day = (time - start) / DAY;
    if (day < 0) return 52000 * Math.exp(day * 0.0014) * (1 + 0.07 * Math.sin(day / 24));
    return 52000 + day * 48 + Math.sin(day / 24) * 7000 + Math.sin(day / 5) * 1400;
};
const rates = { USD: 1, EUR: 0.9, CHF: 0.82 };

// Throwaway fixtures for the real dashboard components, without a database dependency.
export function demoMarket(days: number, from: string | undefined, to: string | undefined, currency: keyof typeof rates) {
    const first = from ? Date.parse(from) : end - Math.min(days, 3650) * DAY;
    const last = to ? Math.min(Date.parse(to), end) : end;
    const rate = rates[currency];
    const history: BitcoinPrice[] = Array.from({ length: Math.max(0, Math.floor((last - first) / DAY) + 1) }, (_, i) => {
        const time = first + i * DAY;
        const close = value(time) * rate;
        const open = value(time - DAY) * rate;
        return { date: iso(time), open, close, high: Math.max(open, close) * 1.015, low: Math.min(open, close) * 0.985, volume: 24e9, rsi: 50 + 15 * Math.sin(i / 9), rsi_status: 'Neutral' };
    });
    const currentPrice = value(end) * rate;
    const previous = value(end - DAY) * rate;
    const displayedHistory = (last - first) / DAY > 1800 ? history.filter((row, i) => i === history.length - 1 || row.date.slice(0, 7) !== history[i + 1].date.slice(0, 7)).map(row => ({ ...row, aggregation: 'monthly' as const })) : history;
    return { history: displayedHistory, metrics: { observedAt: DEMO_DATE, dataAgeDays: 1, currentPrice, change24h: currentPrice - previous, changePercent24h: (currentPrice / previous - 1) * 100, high24h: currentPrice * 1.015, low24h: currentPrice * 0.985, volume24h: 24e9, rsi: 54 } };
}

export function demoProjection(data: BitcoinPrice[], currency: keyof typeof rates, model: string): PriceChartProjection {
    if (!data.length) return { emissions: [] };
    const from = Date.parse(data[0].date);
    const until = Date.parse(data[data.length - 1].date);
    const historical = until < end;
    const emissions = ['2026-06-01', '2026-08-03', '2026-09-07'].map((issued, index) => {
        const reference = Date.parse(issued) - DAY;
        const base = value(reference) * rates[currency];
        return { id: `${model}-${issued}`, issued, points: Array.from({ length: 52 }, (_, h) => {
            const week = h + 1;
            const phase = index * 0.85 + (model === 'alternative' ? 1.1 : 0);
            const cycle = 0.075 * (Math.sin(week / 4.5 + phase) - Math.sin(phase));
            const dip = -0.10 * Math.exp(-(((week - 19 - index * 3) / 5) ** 2));
            const variation = 0.018 * Math.sin(week * 1.7 + phase) + 0.012 * Math.cos(week * 0.83 + phase);
            const median = base * Math.exp(week * 0.002 + cycle + dip + variation);
            const spread = 0.028 + 0.022 * Math.sqrt(week);
            return { date: iso(reference + week * 7 * DAY), low: median * Math.exp(-spread), median, high: median * Math.exp(spread * 1.1) };
        }) };
    }).filter((emission) => !historical || Date.parse(emission.issued) <= until).map((emission) => ({ ...emission, points: emission.points.filter((point) => Date.parse(point.date) >= from && (!historical || Date.parse(point.date) <= until)) })).filter((emission) => emission.points.length > 0);
    return { emissions };
}
