import React from 'react';
import { render, screen } from '@testing-library/react';
import PriceChart from '../PriceChart';

jest.mock('chart.js', () => ({
    Chart: { register: jest.fn() },
    CategoryScale: {},
    LinearScale: {},
    PointElement: {},
    LineElement: {},
    LineController: {},
    Title: {},
    Tooltip: {},
    Legend: {},
    Filler: {},
    TimeScale: {},
    TimeSeriesScale: {},
    LogarithmicScale: {},
}));

jest.mock('chartjs-chart-financial', () => ({
    CandlestickController: {},
    CandlestickElement: {},
}));

jest.mock('chartjs-adapter-date-fns', () => ({}));

jest.mock('react-chartjs-2', () => ({
    Chart: ({ data }: { data: unknown }) => (
        <pre data-testid="chart-data">{JSON.stringify(data)}</pre>
    ),
}));

describe('PriceChart calendar dates and RSI values', () => {
    it('groups date-only RSI values by their calendar month and preserves zero', () => {
        const previousTimezone = process.env.TZ;
        process.env.TZ = 'America/Los_Angeles';

        try {
            render(
                <PriceChart
                    data={[
                        {
                            date: '2020-01-01',
                            open: 90,
                            high: 100,
                            low: 80,
                            close: 95,
                            volume: 10,
                            rsi: 0,
                            rsi_status: 'Oversold',
                        },
                        {
                            date: '2022-01-01',
                            open: 110,
                            high: 120,
                            low: 100,
                            close: 115,
                            volume: 11,
                            rsi: 40,
                            rsi_status: 'Neutral',
                        },
                    ]}
                    showRsi
                />
            );

            const chartData = JSON.parse(screen.getByTestId('chart-data').textContent ?? '{}');
            expect(chartData.datasets[1].data).toEqual([
                { x: Date.UTC(2020, 0, 15), y: 0 },
                { x: Date.UTC(2022, 0, 15), y: 40 },
            ]);
        } finally {
            process.env.TZ = previousTimezone;
        }
    });

    it('uses a shadcn spinner while loading', () => {
        render(<PriceChart data={[]} loading />);

        expect(screen.getByRole('status', { name: 'Loading' })).toBeInTheDocument();
    });

    it('provides a synchronized table alternative to the canvas', () => {
        render(
            <PriceChart
                currencySymbol="$"
                data={[
                    {
                        date: '2026-08-31',
                        open: 75_000,
                        high: 78_000,
                        low: 74_000,
                        close: 77_000,
                        volume: 10,
                        rsi: 51.2,
                        rsi_status: 'Neutral',
                    },
                    {
                        date: '2026-09-01',
                        open: 77_000,
                        high: 80_000,
                        low: 76_000,
                        close: 78_623,
                        volume: 11,
                        rsi: 54.2,
                        rsi_status: 'Neutral',
                    },
                ]}
            />,
        );

        const table = screen.getByRole('table', { name: 'Recent Bitcoin market data' });
        expect(table).toBeInTheDocument();
        expect(table).not.toHaveClass('sr-only');
        expect(table.parentElement).toHaveClass('sr-only');
        expect(screen.getByRole('columnheader', { name: 'Close' })).toBeInTheDocument();
        expect(screen.getByText('$78,623.00')).toBeInTheDocument();
        expect(screen.getByText('54.2')).toBeInTheDocument();
    });
});
