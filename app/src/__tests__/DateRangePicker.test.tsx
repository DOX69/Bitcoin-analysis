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

        // Sidebar items
        expect(screen.getByText('Today')).toBeInTheDocument();
        expect(screen.getByText('Last 5 Years')).toBeInTheDocument();

        // Check for Apply button
        expect(screen.getByText('Apply')).toBeInTheDocument();
    });
});
