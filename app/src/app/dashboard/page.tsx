
import {
    getCurrentBitcoinMetrics,
    getHistoricalPrices
} from '@/lib/bitcoin-data-server';
import DashboardClient from '@/components/dashboard/DashboardClient';

export const dynamic = 'force-dynamic';
export const revalidate = 60; // Revalidate every minute

interface PageProps {
    searchParams: Promise<{
        time?: string;
        start?: string;
        end?: string;
    }>;
}

export default async function Dashboard({ searchParams }: PageProps) {
    const params = await searchParams;
    const selectedTime = params.time || '6m';
    const startDate = params.start;
    const endDate = params.end;

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

    let metrics, historicalData;
    let errorDetail = null;
    let envCheck = {
        host: !!process.env.DATABRICKS_HOST || !!process.env.NEXT_PUBLIC_DATABRICKS_HOST,
        token: !!process.env.DATABRICKS_TOKEN || !!process.env.NEXT_PUBLIC_DATABRICKS_TOKEN,
        path: !!process.env.DATABRICKS_PATH || !!process.env.NEXT_PUBLIC_DATABRICKS_HTTP_PATH,
    };

    try {
        // Parallel data fetching on the server
        [metrics, historicalData] = await Promise.all([
            getCurrentBitcoinMetrics(),
            getHistoricalPrices(
                getDaysForFilter(selectedTime),
                selectedTime === 'custom' ? startDate : undefined,
                selectedTime === 'custom' ? endDate : undefined
            ),
        ]);
    } catch (e: any) {
        console.error("Dashboard Data Fetch Error:", e);
        errorDetail = {
            message: e.message,
            stack: e.stack,
            envCheck
        };
    }

    if (errorDetail) {
        return (
            <div className="min-h-screen bg-black text-white p-8 font-mono">
                <h1 className="text-2xl text-red-500 mb-4 font-bold">Dashboard Error (Debug Mode)</h1>

                <div className="border border-red-800 bg-red-900/20 p-4 rounded-lg mb-6">
                    <h2 className="text-lg font-bold mb-2">Error Message:</h2>
                    <p className="whitespace-pre-wrap text-red-200">{errorDetail.message}</p>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className="border border-gray-700 bg-gray-900 p-4 rounded-lg">
                        <h2 className="text-lg font-bold mb-2 text-blue-400">Environment Check:</h2>
                        <ul className="space-y-1">
                            <li>HOST: {errorDetail.envCheck.host ? '✅ Present' : '❌ MISSING'}</li>
                            <li>TOKEN: {errorDetail.envCheck.token ? '✅ Present' : '❌ MISSING'}</li>
                            <li>PATH: {errorDetail.envCheck.path ? '✅ Present' : '❌ MISSING'}</li>
                        </ul>
                        <p className="text-xs text-gray-500 mt-2">Note: Values are hidden, only presence is checked.</p>
                    </div>
                </div>

                <div className="border border-gray-800 bg-gray-900 p-4 rounded-lg overflow-auto">
                    <h2 className="text-lg font-bold mb-2 text-gray-400">Stack Trace:</h2>
                    <pre className="text-xs text-gray-500 whitespace-pre-wrap">{errorDetail.stack}</pre>
                </div>
            </div>
        );
    }

    return (
        <DashboardClient
            initialMetrics={metrics!}
            initialHistoricalData={historicalData!}
            selectedTime={selectedTime}
            startDate={startDate || ''}
            endDate={endDate || ''}
        />
    );
}
