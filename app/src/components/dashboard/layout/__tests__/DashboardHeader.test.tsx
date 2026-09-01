import React from 'react';
import { render, screen } from '@testing-library/react';
import DashboardHeader from '../DashboardHeader';

describe('DashboardHeader', () => {
    it('keeps navigation on shipped routes and labels the read-only state', () => {
        render(<DashboardHeader />);

        expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/');
        expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/dashboard');
        expect(screen.getByText('Read-only data')).toBeInTheDocument();
        expect(screen.queryByRole('link', { name: /Screener|Terminal|Stats|FAQ|Profile|Settings/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /Settings|Notifications|User/i })).not.toBeInTheDocument();
    });
});
