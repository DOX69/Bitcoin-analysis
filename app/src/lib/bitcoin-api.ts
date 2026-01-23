
export interface BitcoinPrice {
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

export interface BitcoinMetrics {
    currentPrice: number;
    change24h: number;
    changePercent24h: number;
    volume24h: number;
    high24h: number;
    low24h: number;
    rsi: number;
}

export interface AggregatedData {
    period: string;
    avgPrice: number;
    maxPrice: number;
    minPrice: number;
    totalVolume: number;
}

export async function getCurrentBitcoinMetrics(): Promise<BitcoinMetrics> {
    const response = await fetch('/api/bitcoin?type=metrics');
    if (!response.ok) {
        throw new Error('Failed to fetch metrics');
    }
    return response.json();
}

export async function getHistoricalPrices(days: number = 30): Promise<BitcoinPrice[]> {
    const response = await fetch(`/api/bitcoin?type=history&days=${days}`);
    if (!response.ok) {
        throw new Error('Failed to fetch historical prices');
    }
    return response.json();
}

export async function getAggregatedData(
    period: 'weekly' | 'monthly' | 'quarterly' = 'weekly'
): Promise<AggregatedData[]> {
    const response = await fetch(`/api/bitcoin?type=aggregated&period=${period}`);
    if (!response.ok) {
        throw new Error('Failed to fetch aggregated data');
    }
    return response.json();
}
