
import { NextResponse } from 'next/server';
import { getCurrentBitcoinMetrics, getHistoricalPrices, getAggregatedData } from '@/lib/bitcoin-data-server';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const type = searchParams.get('type');

    try {
        if (type === 'metrics') {
            const data = await getCurrentBitcoinMetrics();
            return NextResponse.json(data);
        } else if (type === 'history') {
            const days = parseInt(searchParams.get('days') || '30');
            const startDate = searchParams.get('startDate') || undefined;
            const endDate = searchParams.get('endDate') || undefined;
            const data = await getHistoricalPrices(days, startDate, endDate);
            return NextResponse.json(data);
        } else if (type === 'aggregated') {
            const period = searchParams.get('period') as 'weekly' | 'monthly' | 'quarterly' || 'weekly';
            const data = await getAggregatedData(period);
            return NextResponse.json(data);
        }

        return NextResponse.json({ error: 'Invalid type parameter' }, { status: 400 });
    } catch (error) {
        console.error('API Error:', error);
        return NextResponse.json({ error: 'Failed to fetch data' }, { status: 500 });
    }
}
