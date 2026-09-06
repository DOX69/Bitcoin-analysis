
import { NextResponse } from 'next/server';
import {
    getCurrentBitcoinMetrics,
    getHistoricalPrices,
    getAggregatedData
} from '@/lib/bitcoin-data-server';
import { BitcoinSearchParamsSchema } from '@/lib/schemas';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);

    const validation = BitcoinSearchParamsSchema.safeParse({
        type: searchParams.get('type'),
        days: searchParams.get('days') ?? undefined,
        startDate: searchParams.get('startDate') ?? undefined,
        endDate: searchParams.get('endDate') ?? undefined,
        period: searchParams.get('period') ?? undefined,
    });
    if (!validation.success) {
        return NextResponse.json({ error: 'Validation failed', details: validation.error.flatten().fieldErrors }, { status: 400 });
    }
    const params = validation.data;
    try {
        switch (params.type) {
            case 'metrics': {
                const data = await getCurrentBitcoinMetrics();
                return NextResponse.json(data);
            }
            case 'history': {
                const data = await getHistoricalPrices(params.days, params.startDate, params.endDate);
                return NextResponse.json(data);
            }
            case 'aggregated': {
                const data = await getAggregatedData(params.period);
                return NextResponse.json(data);
            }
            default:
                return NextResponse.json({ error: 'Unsupported type' }, { status: 400 });
        }
    } catch (error) {
        console.error('API Error:', error);
        return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
    }
}
