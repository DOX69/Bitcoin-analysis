
import { NextResponse } from 'next/server';
import {
    getCurrentBitcoinMetrics,
    getHistoricalPrices,
    getAggregatedData,
    getForecastData
} from '@/lib/bitcoin-data-server';
import { BitcoinSearchParamsSchema } from '@/lib/schemas';
import { z } from 'zod';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);

    try {
        const params = BitcoinSearchParamsSchema.parse({
            type: searchParams.get('type'),
            days: searchParams.get('days'),
            startDate: searchParams.get('startDate'),
            endDate: searchParams.get('endDate'),
            period: searchParams.get('period'),
        });

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
            case 'forecast': {
                const data = await getForecastData();
                return NextResponse.json(data);
            }
            default:
                return NextResponse.json({ error: 'Unsupported type' }, { status: 400 });
        }
    } catch (error) {
        if (error instanceof z.ZodError) {
            return NextResponse.json({
                error: 'Validation failed',
                details: error.flatten().fieldErrors
            }, { status: 400 });
        }

        console.error('API Error:', error);
        return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
    }
}
