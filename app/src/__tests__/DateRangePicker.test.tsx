import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import DateRangePicker from '../components/dashboard/inputs/DateRangePicker';

describe('DateRangePicker Component', () => {
    it('should render the input trigger', () => {
        render(<DateRangePicker startDate="" endDate="" onChange={() => { }} />);
        expect(screen.getByPlaceholderText('YYYY-MM-DD ~ YYYY-MM-DD')).toBeInTheDocument();
    });

    it('should open the popup when input is clicked', () => {
        render(<DateRangePicker startDate="" endDate="" onChange={() => { }} />);
        const input = screen.getByPlaceholderText('YYYY-MM-DD ~ YYYY-MM-DD');
        fireEvent.click(input);

        expect(screen.getByRole('dialog')).toBeInTheDocument();

        // Sidebar items
        expect(screen.getByText('Today')).toBeInTheDocument();
        expect(screen.getByText('Last 5 Years')).toBeInTheDocument();

        // Check for Apply button
        expect(screen.getByText('Apply')).toBeInTheDocument();
    });

    it('initializes from the current range when the parent remounts it', () => {
        const { rerender } = render(
            <DateRangePicker
                key="first-range"
                startDate="2026-01-01"
                endDate="2026-01-07"
                onChange={() => { }}
            />,
        );

        expect(screen.getByDisplayValue('2026-01-01 ~ 2026-01-07')).toBeInTheDocument();

        rerender(
            <DateRangePicker
                key="second-range"
                startDate="2026-02-01"
                endDate="2026-02-07"
                onChange={() => { }}
            />,
        );

        expect(screen.getByDisplayValue('2026-02-01 ~ 2026-02-07')).toBeInTheDocument();
    });

    it('restores the committed range when canceling a draft', () => {
        const onChange = jest.fn();
        render(
            <DateRangePicker
                startDate="2026-01-01"
                endDate="2026-01-07"
                onChange={onChange}
            />,
        );

        const input = screen.getByDisplayValue('2026-01-01 ~ 2026-01-07');
        fireEvent.click(input);
        fireEvent.change(input, {
            target: { value: '2026-02-01 ~ 2026-02-07' },
        });
        fireEvent.click(screen.getByText('Cancel'));

        expect(input).toHaveValue('2026-01-01 ~ 2026-01-07');
        expect(onChange).not.toHaveBeenCalled();
    });
});
