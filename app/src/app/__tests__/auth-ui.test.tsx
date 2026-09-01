import React from 'react';
import { render, screen } from '@testing-library/react';
import LoginPage from '../login/page';
import SignupPage from '../signup/page';

jest.mock('@/components/landing/EnergyGraph', () => {
    function MockEnergyGraph() {
        return React.createElement('div');
    }

    return MockEnergyGraph;
});

describe('authentication UI', () => {
    it('states that sign-in is unavailable and offers read-only access', () => {
        render(<LoginPage />);

        expect(screen.getByRole('heading', { name: 'Read-only demo' })).toBeInTheDocument();
        expect(screen.getByText(/accounts and sign-in are not available/i)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Open market dashboard' })).toHaveAttribute('href', '/dashboard');
        expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    });

    it('does not pretend to create an account', () => {
        render(<SignupPage />);

        expect(screen.getByRole('heading', { name: 'Read-only demo' })).toBeInTheDocument();
        expect(screen.getByText(/account creation is not available/i)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Open market dashboard' })).toHaveAttribute('href', '/dashboard');
        expect(screen.queryByLabelText(/Password|Confirm Password/i)).not.toBeInTheDocument();
    });
});
