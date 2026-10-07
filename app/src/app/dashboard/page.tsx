
import {
    getCurrentBitcoinMetrics,
    getHistoricalPrices
} from '@/lib/bitcoin-data-server';
import Link from 'next/link';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { DashboardSearchParamsSchema } from '@/lib/schemas';
import DashboardClient from '@/components/dashboard/DashboardClient';
import { demoMarket } from '@/components/dashboard/forecast-prototype/demo-data';

export const dynamic = 'force-dynamic';
export const revalidate = 60; // Revalidate every minute

interface PageProps {
    searchParams: Promise<{
        time?: string;
        start?: string;
        end?: string;
        currency?: string;
        variant?: string;
    }>;
}

export default async function Dashboard({ searchParams }: PageProps) {
    const params = await searchParams;
    const prototypeVariant = process.env.NODE_ENV === 'development' && params.variant === 'A' ? 'A' as const : undefined;
    const validation = DashboardSearchParamsSchema.safeParse({
        time: params.time,
        currency: params.currency,
        startDate: params.start,
        endDate: params.end,
    });
    if (!validation.success) {
        return (
            <main className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
                <Alert variant="destructive" className="max-w-md gap-4 p-8">
                    <AlertTitle>Invalid dashboard filters</AlertTitle>
                    <AlertDescription>
                        <p>Choose a supported time range and currency. Custom ranges need two valid dates, with the end on or after the start.</p>
                        <Link href="/dashboard" className="mt-4 inline-block underline">Reset filters</Link>
                    </AlertDescription>
                </Alert>
            </main>
        );
    }
    const { time: selectedTime, startDate, endDate, currency: selectedCurrency } = validation.data;

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

    // The prototype uses the real dashboard with clearly identified demo inputs.
    const demo = prototypeVariant ? demoMarket(getDaysForFilter(selectedTime), startDate, endDate, selectedCurrency) : undefined;
    const [metrics, historicalData] = demo ? [demo.metrics, demo.history] : await Promise.all([
        getCurrentBitcoinMetrics(selectedCurrency),
        getHistoricalPrices(
            getDaysForFilter(selectedTime),
            selectedTime === 'custom' ? startDate : undefined,
            selectedTime === 'custom' ? endDate : undefined,
            selectedCurrency
        ),
    ]);

    return (
        <DashboardClient
            initialMetrics={metrics}
            initialHistoricalData={historicalData}
            selectedTime={selectedTime}
            startDate={startDate || ''}
            endDate={endDate || ''}
            selectedCurrency={selectedCurrency}
            prototypeVariant={prototypeVariant}
        />
    );
}
