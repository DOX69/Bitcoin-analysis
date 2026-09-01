import React from 'react';
import { render, screen } from '@testing-library/react';
import DashboardClient from '../DashboardClient';

jest.mock('next/navigation', () => ({
    useRouter: () => ({ push: jest.fn() }),
    useSearchParams: () => new URLSearchParams(),
}));

jest.mock('@/components/dashboard', () => ({
    DashboardHeader: () => <div>Header</div>,
    StatsPanel: () => <div>Market snapshot</div>,
    StatCard: ({ title, value, subtitle }: { title: string; value: string; subtitle?: string }) => (
        <article>
            <h2>{title}</h2>
            <p>{value}</p>
            {subtitle && <p>{subtitle}</p>}
        </article>
    ),
    DateRangePicker: () => <button type="button">Date range</button>,
    PriceChart: () => <div>Price chart</div>,
}));

jest.mock('@/components/dashboard/IndicatorSelector', () => {
    function IndicatorSelector() {
        return <button type="button">Indicators</button>;
    }

    return IndicatorSelector;
});

const metrics = {
    currentPrice: 78623,
    change24h: 1000,
    changePercent24h: 1.29,
    volume24h: 42_000_000_000,
    high24h: 79_500,
    low24h: 76_100,
    rsi: 54.2,
};

const history = [
    { date: '2026-08-31', open: 75_000, high: 78_000, low: 74_000, close: 77_000, volume: 10, rsi_status: 'Neutral' },
    { date: '2026-09-01', open: 77_000, high: 80_000, low: 76_000, close: 78_623, volume: 11, rsi_status: 'Neutral' },
];

describe('DashboardClient market truth', () => {
    it('labels every KPI after the market value it renders', () => {
        render(
            <DashboardClient
                initialMetrics={metrics}
                initialHistoricalData={history}
                selectedTime="6m"
                startDate=""
                endDate=""
                selectedCurrency="USD"
            />,
        );

        expect(screen.getByRole('heading', { name: 'Bitcoin market dashboard' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Current Bitcoin price' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Period high (6M)' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Period low (6M)' })).toBeInTheDocument();
        expect(screen.queryByText(/PNL|ATH|ATL/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/PostgreSQL.*updated daily/i)).not.toBeInTheDocument();
    });
});
