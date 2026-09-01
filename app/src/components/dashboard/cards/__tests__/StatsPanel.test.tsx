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
                }}
            />,
        );

        expect(screen.getByRole('heading', { name: 'Market snapshot' })).toBeInTheDocument();
        expect(screen.getByText('Current price')).toBeInTheDocument();
        expect(screen.getByText('24h price change')).toBeInTheDocument();
        expect(screen.getByText('$1,000.00')).toBeInTheDocument();
        expect(screen.queryByText('24h volume')).not.toBeInTheDocument();
        expect(screen.getByText('RSI (14d)')).toBeInTheDocument();
        expect(screen.getByText('PostgreSQL, updated daily')).toBeInTheDocument();
        expect(screen.queryByText(/Deposit|Win rate|Profit factor|Positions/i)).not.toBeInTheDocument();
    });
});
