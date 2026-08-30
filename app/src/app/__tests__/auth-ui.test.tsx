import React from 'react';
import { render, screen } from '@testing-library/react';
import LoginPage from '../login/page';
import SignupPage from '../signup/page';

jest.mock('@/components/dashboard', () => ({
    AuthKPIs: () => React.createElement('div', null, 'KPIs'),
}));

jest.mock('@/components/landing/EnergyGraph', () => {
    function MockEnergyGraph() {
        return React.createElement('div');
    }

    return MockEnergyGraph;
});

jest.mock('next/navigation', () => ({
    useRouter: () => ({ push: jest.fn() }),
}));

describe('authentication UI', () => {
    it('uses shadcn controls on the login form', () => {
        render(<LoginPage />);

        expect(screen.getByLabelText('Email')).toHaveAttribute('data-slot', 'input');
        expect(screen.getByLabelText('Password')).toHaveAttribute('data-slot', 'input');
        expect(screen.getByRole('checkbox', { name: 'Remember me' })).toHaveAttribute('data-slot', 'checkbox');
        expect(screen.getByRole('button', { name: 'Sign in' })).toHaveAttribute('data-slot', 'button');
    });

    it('uses shadcn controls on the signup form', () => {
        render(<SignupPage />);

        expect(screen.getByLabelText('Email')).toHaveAttribute('data-slot', 'input');
        expect(screen.getByLabelText('Password')).toHaveAttribute('data-slot', 'input');
        expect(screen.getByLabelText('Confirm Password')).toHaveAttribute('data-slot', 'input');
        expect(screen.getByRole('button', { name: 'Sign up' })).toHaveAttribute('data-slot', 'button');
    });
});
