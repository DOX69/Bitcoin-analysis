import React from 'react';
import { render, screen } from '@testing-library/react';
import Header from '../Header';
import Hero from '../Hero';
import Footer from '../Footer';

describe('landing navigation and copy', () => {
    it('links only to shipped sections and the market dashboard', () => {
        render(<Header />);

        expect(screen.getByRole('link', { name: 'Capabilities' })).toHaveAttribute('href', '#capabilities');
        expect(screen.getByRole('link', { name: 'Open dashboard' })).toHaveAttribute('href', '/dashboard');
        expect(screen.queryByRole('link', { name: /Sign in|Sign up|Components|Documentation/i })).not.toBeInTheDocument();
    });

    it('describes the shipped market analysis instead of account access', () => {
        render(<Hero />);

        expect(screen.getByRole('heading', { name: 'Trace Bitcoin moves through time' })).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Open market dashboard' })).toHaveAttribute('href', '/dashboard');
    });

    it('removes policy routes that do not exist', () => {
        render(<Footer />);

        expect(screen.queryByRole('link', { name: /Privacy|Terms/i })).not.toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Source code' })).toHaveAttribute(
            'href',
            'https://github.com/DOX69/Bitcoin-analysis',
        );
    });
});
