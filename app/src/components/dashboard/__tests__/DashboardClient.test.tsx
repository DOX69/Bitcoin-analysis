import React from 'react';
import { fireEvent, render, screen, within, waitFor } from '@testing-library/react';
import DashboardClient from '../DashboardClient';

const mockPush = jest.fn();

jest.mock('next/navigation', () => ({
    useRouter: () => ({ push: mockPush }),
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
    PriceChart: ({ type, showRsi, showSma, showEma, scaleType }: { type: string; showRsi: boolean; showSma: boolean; showEma: boolean; scaleType: string }) => (
        <div data-testid="price-chart" data-type={type} data-rsi={showRsi} data-sma={showSma} data-ema={showEma} data-scale={scaleType}>Price chart</div>
    ),
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
    beforeEach(() => mockPush.mockClear());

    it('applies a valid custom date range from the drawer', async () => {
        render(<DashboardClient initialMetrics={metrics} initialHistoricalData={history} selectedTime="6m" startDate="" endDate="" selectedCurrency="USD" />);
        fireEvent.click(screen.getByRole('button', { name: 'Chart settings' }));
        const drawer = await screen.findByRole('dialog', { name: 'Chart settings' });
        const apply = within(drawer).getByRole('button', { name: 'Apply dates' });
        expect(apply).toBeDisabled();
        fireEvent.change(within(drawer).getByLabelText('Start date'), { target: { value: '2026-08-20' } });
        fireEvent.change(within(drawer).getByLabelText('End date'), { target: { value: '2026-08-10' } });
        expect(apply).toBeDisabled();
        fireEvent.change(within(drawer).getByLabelText('End date'), { target: { value: '2026-08-29' } });
        fireEvent.click(apply);
        expect(mockPush).toHaveBeenCalledWith('?start=2026-08-20&end=2026-08-29&time=custom');
    });

    it('switches chart type and preserves drawer indicator choices after closing', async () => {
        render(<DashboardClient initialMetrics={metrics} initialHistoricalData={history} selectedTime="6m" startDate="" endDate="" selectedCurrency="USD" />);
        fireEvent.click(screen.getByRole('button', { name: 'Switch to candlestick chart' }));
        expect(screen.getByTestId('price-chart')).toHaveAttribute('data-type', 'candlestick');
        fireEvent.click(screen.getByRole('button', { name: 'Switch to line chart' }));
        expect(screen.getByTestId('price-chart')).toHaveAttribute('data-type', 'line');
        fireEvent.click(screen.getByRole('button', { name: 'Chart settings' }));
        const drawer = await screen.findByRole('dialog', { name: 'Chart settings' });
        fireEvent.click(within(drawer).getByRole('switch', { name: 'RSI' }));
        fireEvent.click(within(drawer).getByRole('switch', { name: 'SMA' }));
        fireEvent.click(within(drawer).getByRole('switch', { name: 'EMA' }));
        fireEvent.click(within(drawer).getByRole('button', { name: 'Log' }));
        fireEvent.click(within(drawer).getByRole('button', { name: 'Close chart settings' }));
        await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
        expect(screen.getByTestId('price-chart')).toHaveAttribute('data-rsi', 'true');
        expect(screen.getByTestId('price-chart')).toHaveAttribute('data-sma', 'true');
        expect(screen.getByTestId('price-chart')).toHaveAttribute('data-ema', 'true');
        expect(screen.getByTestId('price-chart')).toHaveAttribute('data-scale', 'logarithmic');
        fireEvent.click(screen.getByRole('button', { name: /Chart settings/ }));
        expect(await screen.findByRole('switch', { name: 'RSI' })).toHaveAttribute('aria-checked', 'true');
    });

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
