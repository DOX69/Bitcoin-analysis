/**
 * Component tests for MetricsCard
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import MetricsCard from '@/components/dashboard/cards/MetricsCard'; // Direct import from new location for unit test

describe('MetricsCard Component', () => {
    it('should render title and value correctly', () => {
        render(
            <MetricsCard
                title="Current Price"
                value="$42,500.00"
            />
        );

        // Text content is "Current Price", CSS transforms it to UPPERCASE
        expect(screen.getByText('Current Price')).toBeInTheDocument();
        expect(screen.getByText('$42,500.00')).toBeInTheDocument();
    });

    it('should display positive change with green color', () => {
        render(
            <MetricsCard
                title="Price"
                value="$43,000.00"
                change={500}
                changePercent={1.18}
            />
        );

        const changeElement = screen.getByText(/\$500.00/);
        // The color class is on the parent container
        expect(changeElement.parentElement).toHaveClass('text-green-400');
        expect(screen.getByText(/\+1.18%/)).toBeInTheDocument();
    });

    it('should display negative change with red color', () => {
        render(
            <MetricsCard
                title="Price"
                value="$42,000.00"
                change={-500}
                changePercent={-1.18}
            />
        );

        const changeElement = screen.getByText(/\$500.00/);
        expect(changeElement.parentElement).toHaveClass('text-red-400');
        expect(screen.getByText(/-1.18%/)).toBeInTheDocument();
    });

    it('should show loading state', () => {
        render(
            <MetricsCard
                title="Price"
                value="$0.00"
                loading={true}
            />
        );

        const loadingElements = screen.getAllByRole('generic').filter(el =>
            el.className.includes('loading-pulse')
        );
        expect(loadingElements.length).toBeGreaterThan(0);
    });

    it('should format numeric values correctly', () => {
        render(
            <MetricsCard
                title="Volume"
                value={28500000000}
            />
        );

        expect(screen.getByText('28,500,000,000.00')).toBeInTheDocument();
    });

    it('should handle string values', () => {
        render(
            <MetricsCard
                title="Status"
                value="Active"
            />
        );

        expect(screen.getByText('Active')).toBeInTheDocument();
    });
});
