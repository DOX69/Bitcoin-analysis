import type { IndicatorId } from '@/lib/indicators';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import IndicatorSelector from '@/components/dashboard/IndicatorSelector';
import '@testing-library/jest-dom';

describe('IndicatorSelector', () => {
    const mockOnToggle = jest.fn();
    const defaultIndicators = new Set<IndicatorId>();

    it('renders the multi-select dropdown button', () => {
        render(<IndicatorSelector selectedIndicators={defaultIndicators} onToggleIndicator={mockOnToggle} />);
        expect(screen.getByRole('button', { name: /indicators/i })).toBeInTheDocument();
    });

    it('shows options when clicked', () => {
        render(<IndicatorSelector selectedIndicators={defaultIndicators} onToggleIndicator={mockOnToggle} />);
        fireEvent.click(screen.getByRole('button', { name: /indicators/i }));

        expect(screen.getByText('RSI')).toBeInTheDocument();
        expect(screen.getByText('MACD')).toBeInTheDocument();
        expect(screen.getByText('3 SMA')).toBeInTheDocument();
        expect(screen.getByText('3 EMA')).toBeInTheDocument();
        expect(screen.getAllByRole('menuitemcheckbox').map(item => item.textContent)).toEqual([
            'RSIRelative Strength Index', 'MACDMoving Average Convergence Divergence',
            '3 SMA7, 50, 200-day Simple Moving Averages', '3 EMA7, 50, 200-day Exponential Moving Averages',
        ]);
    });

    it('calls onToggleIndicator when an option is clicked', () => {
        render(<IndicatorSelector selectedIndicators={defaultIndicators} onToggleIndicator={mockOnToggle} />);
        fireEvent.click(screen.getByRole('button', { name: /indicators/i }));
        fireEvent.click(screen.getByText('RSI'));

        expect(mockOnToggle).toHaveBeenCalledWith('rsi');
    });

    it('highlights selected indicators', () => {
        const selected = new Set<IndicatorId>(['rsi', 'macd']);
        render(<IndicatorSelector selectedIndicators={selected} onToggleIndicator={mockOnToggle} />);
        fireEvent.click(screen.getByRole('button', { name: /indicators/i }));

        expect(screen.getByRole('menuitemcheckbox', { name: /rsi/i })).toHaveAttribute('aria-checked', 'true');
        expect(screen.getByRole('menuitemcheckbox', { name: /macd/i })).toHaveAttribute('aria-checked', 'true');
    });
});
