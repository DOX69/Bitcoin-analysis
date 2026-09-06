import React from 'react';
import { render, screen, within } from '@testing-library/react';
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
    it('names active lines and exposes their values outside the canvas', () => {
        render(<PriceChart showSma showEma showMacd data={[{
            date: '2026-08-29', open: 75, high: 80, low: 70, close: 78, volume: 10,
            rsi_status: 'Neutral', sma_7: 76, ema_7: 77, macd: 0, macd_signal: 1, macd_hist: -1,
        }]} />);
        const legend = screen.getByRole('list', { name: 'Active chart series' });
        expect(within(legend).getByText('SMA 7')).toBeInTheDocument();
        expect(within(legend).getByText('EMA 7')).toBeInTheDocument();
        const table = screen.getByRole('table', { name: 'Recent Bitcoin market data' });
        expect(within(table).getByRole('columnheader', { name: 'SMA 7' })).toBeInTheDocument();
        expect(within(table).getByRole('columnheader', { name: 'MACD' })).toBeInTheDocument();
        expect(within(table).getByText('$76.00')).toBeInTheDocument();
        expect(within(table).getByText('0.00')).toBeInTheDocument();
        expect(within(table).getAllByText('Unavailable').length).toBeGreaterThan(0);
    });

    it('preserves source RSI dates and values on long ranges', () => {
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
                        { date: '2020-01-02', open: 90, high: 100, low: 80, close: 95, volume: 10, rsi: 80, rsi_status: 'Overbought' },
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
                { x: Date.UTC(2020, 0, 1), y: 0 },
                { x: Date.UTC(2020, 0, 2), y: 80 },
                { x: Date.UTC(2022, 0, 1), y: 40 },
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


it('labels a monthly close by aggregation month, not an observation on the first', () => {
    render(<PriceChart data={[{ date: '2026-08-01', aggregation: 'monthly', open: 75, high: 80, low: 70, close: 78, volume: 0, rsi_status: 'Neutral' }]} />);
    expect(screen.getByText(/Period close .* Aug 2026 \(monthly aggregate\)/)).toBeInTheDocument();
    expect(screen.getByRole('rowheader', { name: 'Aug 2026 (monthly aggregate)' })).toBeInTheDocument();
    expect(screen.queryByText(/1 Aug 2026/)).not.toBeInTheDocument();
});


it('keeps source candle lows identical to the accessible table', () => {
    render(<PriceChart type="candlestick" data={[{
        date: '2017-04-01', open: 1000, high: 1200, low: 50, close: 1100, volume: 1, rsi_status: 'Neutral',
    }]} />);
    const chartData = JSON.parse(screen.getByTestId('chart-data').textContent ?? '{}');
    expect(chartData.datasets[0].data[0]).toEqual({x: Date.UTC(2017, 3, 1), o: 1000, h: 1200, l: 50, c: 1100});
    expect(within(screen.getByRole('table')).getByText('$50.00')).toBeInTheDocument();
});


it.each(['line', 'candlestick'] as const)('preserves all selected series and table columns for %s charts', (type) => {
    render(<PriceChart type={type} showRsi showSma showEma showMacd data={[{
        date: '2024-01-01', open: 100, high: 120, low: 90, close: 110, volume: 1,
        rsi: 0, rsi_status: 'Oversold', sma_7: 1, sma_50: 2, sma_200: 3,
        ema_7: 4, ema_50: 5, ema_200: 6, macd: 7, macd_signal: 8, macd_hist: 9,
    }]} />);
    const datasets = JSON.parse(screen.getByTestId('chart-data').textContent ?? '{}').datasets;
    expect(datasets.slice(1).map((series: { label: string }) => series.label)).toEqual([
        'RSI', 'SMA 7', 'SMA 50', 'SMA 200', 'EMA 7', 'EMA 50', 'EMA 200', 'MACD', 'Signal', 'Histogram',
    ]);
    expect(datasets.slice(1).map((series: { data: { y: number }[] }) => series.data[0].y)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    expect(within(screen.getByRole('table')).getAllByRole('columnheader').map(header => header.textContent)).toEqual([
        'Date', 'Close', 'High', 'Low', 'RSI', 'SMA 7', 'SMA 50', 'SMA 200', 'EMA 7', 'EMA 50', 'EMA 200', 'MACD', 'Signal', 'Histogram',
    ]);
    expect(datasets[2]).toMatchObject({ borderColor: 'rgba(56, 189, 248, 0.8)', borderWidth: 1 });
    expect(datasets[5]).toMatchObject({ borderColor: 'rgba(56, 189, 248, 0.6)', borderWidth: 2, borderDash: [2, 2] });
});
