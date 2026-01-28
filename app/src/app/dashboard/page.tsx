
import {
    getCurrentBitcoinMetrics,
    getHistoricalPrices,
    getForecastData,
    type Currency
} from '@/lib/bitcoin-data-server';
import DashboardClient from '@/components/dashboard/DashboardClient';

export const dynamic = 'force-dynamic';
export const revalidate = 60; // Revalidate every minute

interface PageProps {
    searchParams: Promise<{
        time?: string;
        start?: string;
        end?: string;
        currency?: string;
    }>;
}

export default async function Dashboard({ searchParams }: PageProps) {
    const params = await searchParams;
    const selectedTime = params.time || '6m';
    const startDate = params.start;
    const endDate = params.end;
    const selectedCurrency = (params.currency as Currency) || 'USD';

    const getDaysForFilter = (filter: string) => {
        switch (filter) {
            case '1w': return 7;
            case '1m': return 30;
            case '6m': return 180;
            case '1y': return 365;
            case 'ytd': {
                const now = new Date();
                const startOfYear = new Date(now.getFullYear(), 0, 1);
                const diff = now.getTime() - startOfYear.getTime();
                return Math.ceil(diff / (1000 * 60 * 60 * 24));
            }
            case 'all': return 3650;
            default: return 180;
        }
    };

    // Parallel data fetching on the server
    const [metrics, historicalData, forecastData] = await Promise.all([
        getCurrentBitcoinMetrics(selectedCurrency),
        getHistoricalPrices(
            getDaysForFilter(selectedTime),
            selectedTime === 'custom' ? startDate : undefined,
            selectedTime === 'custom' ? endDate : undefined,
            selectedCurrency
        ),
        getForecastData(selectedCurrency),
    ]);

    return (
        <DashboardClient
            initialMetrics={metrics}
            initialHistoricalData={historicalData}
            initialForecastData={forecastData}
            selectedTime={selectedTime}
            startDate={startDate || ''}
            endDate={endDate || ''}
            selectedCurrency={selectedCurrency}
        />
    );
}
