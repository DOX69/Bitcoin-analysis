
import { BitcoinMetrics, BitcoinPrice, AggregatedData } from '@/lib/schemas';
export type { BitcoinMetrics, BitcoinPrice, AggregatedData };

export async function getCurrentBitcoinMetrics(): Promise<BitcoinMetrics> {
    const response = await fetch('/api/bitcoin?type=metrics');
    if (!response.ok) throw new Error('Failed to fetch metrics');
    return response.json();
}

export async function getHistoricalPrices(
    days: number = 30,
    startDate?: string,
    endDate?: string
): Promise<BitcoinPrice[]> {
    let url = `/api/bitcoin?type=history&days=${days}`;
    if (startDate) url += `&startDate=${startDate}`;
    if (endDate) url += `&endDate=${endDate}`;

    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch historical prices');
    return response.json();
}

export async function getAggregatedData(
    period: 'weekly' | 'monthly' | 'quarterly' = 'weekly'
): Promise<AggregatedData[]> {
    const response = await fetch(`/api/bitcoin?type=aggregated&period=${period}`);
    if (!response.ok) throw new Error('Failed to fetch aggregated data');
    return response.json();
}
