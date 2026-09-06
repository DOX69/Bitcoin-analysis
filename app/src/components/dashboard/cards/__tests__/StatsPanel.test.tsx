import React from 'react';
import { render, screen } from '@testing-library/react';
import StatsPanel from '../StatsPanel';

describe('StatsPanel', () => {
    it('shows only canonical market metrics', () => {
        render(
            <StatsPanel
                metrics={{
                    currentPrice: 78_623,
                    change24h: 1_000,
                    changePercent24h: 1.29,
                    volume24h: 42_000_000_000,
                    high24h: 79_500,
                    low24h: 76_100,
                    rsi: 54.2,
                    observedAt: '2026-08-29',
                    dataAgeDays: 7,
                }}
            />,
        );

        expect(screen.getByRole('heading', { name: 'Market snapshot' })).toBeInTheDocument();
        expect(screen.getByText('Latest observed price')).toBeInTheDocument();
        expect(screen.getByText('24h price change')).toBeInTheDocument();
        expect(screen.getByText('$1,000.00')).toBeInTheDocument();
        expect(screen.queryByText('24h volume')).not.toBeInTheDocument();
        expect(screen.getByText('RSI (14d)')).toBeInTheDocument();
        expect(screen.getByText('29 Aug 2026')).toBeInTheDocument();
        expect(screen.getByText('7 days old')).toBeInTheDocument();
        expect(screen.queryByText('PostgreSQL, updated daily')).not.toBeInTheDocument();
        expect(screen.queryByText(/Deposit|Win rate|Profit factor|Positions/i)).not.toBeInTheDocument();
    });
});


it('keeps a current-day candle visible when RSI is unavailable', () => {
    render(<StatsPanel metrics={{ observedAt: '2026-09-06', dataAgeDays: 0, currentPrice: 100, high24h: 110, low24h: 90, change24h: 2, changePercent24h: 2, volume24h: 10, rsi: null }} />);
    expect(screen.getByText('Daily candle')).toBeInTheDocument();
    expect(screen.getByText('Latest observed price')).toBeInTheDocument();
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.getByText('$100.00')).toBeInTheDocument();
});
