import { NextResponse } from 'next/server';
import { readForecast } from '@/lib/forecast-server';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
    const params = new URL(request.url).searchParams;
    const currency = params.get('currency') ?? 'USD';
    const asOf = params.get('asOf') ?? new Date().toISOString().slice(0, 10);
    if (!['USD', 'EUR', 'CHF'].includes(currency) || !/^\d{4}-\d{2}-\d{2}$/.test(asOf) || !Number.isFinite(Date.parse(asOf)) || new Date(asOf).toISOString().slice(0, 10) !== asOf) {
        return NextResponse.json({ error: 'Invalid forecast parameters' }, { status: 400 });
    }
    try {
        return NextResponse.json(await readForecast(currency, asOf), { headers: { 'Cache-Control': 'no-store' } });
    } catch {
        return NextResponse.json({ error: 'Forecast unavailable' }, { status: 503 });
    }
}
