import React from 'react';
import { render, screen } from '@testing-library/react';
import Dashboard from '../page';
import { getCurrentBitcoinMetrics, getHistoricalPrices } from '@/lib/bitcoin-data-server';

jest.mock('@/lib/bitcoin-data-server', () => ({
    getCurrentBitcoinMetrics: jest.fn().mockResolvedValue({}),
    getHistoricalPrices: jest.fn().mockResolvedValue([]),
}));
jest.mock('@/components/dashboard/DashboardClient', () => ({
    __esModule: true, default: () => <div>Valid dashboard</div>,
}));

describe('dashboard URL filters', () => {
    beforeEach(() => jest.clearAllMocks());

    it.each([
        { currency: 'GBP' }, { time: 'unknown' }, { time: 'custom' },
        { time: 'custom', start: '2024-01-01' },
        { time: 'custom', start: '2024-02-30', end: '2024-03-01' },
        { time: 'custom', start: '2024-03-02', end: '2024-03-01' },
        { time: '6m', start: 'bad', end: 'bad' },
    ])('shows invalid filters without querying data: %p', async params => {
        render(await Dashboard({ searchParams: Promise.resolve(params) }));
        expect(screen.getByRole('alert')).toHaveTextContent('Invalid dashboard filters');
        expect(screen.getByRole('link', { name: 'Reset filters' })).toHaveAttribute('href', '/dashboard');
        expect(getCurrentBitcoinMetrics).not.toHaveBeenCalled();
        expect(getHistoricalPrices).not.toHaveBeenCalled();
    });

    it('preserves the default six-month USD view', async () => {
        await Dashboard({ searchParams: Promise.resolve({}) });
        expect(getCurrentBitcoinMetrics).toHaveBeenCalledWith('USD');
        expect(getHistoricalPrices).toHaveBeenCalledWith(180, undefined, undefined, 'USD');
    });

    it('preserves the twelve-year custom preset and currency', async () => {
        await Dashboard({ searchParams: Promise.resolve({ time: 'custom', start: '2014-09-06', end: '2026-09-06', currency: 'EUR' }) });
        expect(getHistoricalPrices).toHaveBeenCalledWith(180, '2014-09-06', '2026-09-06', 'EUR');
    });
});
