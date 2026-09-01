import React from 'react';
import { render, screen } from '@testing-library/react';
import Features from '../Features';

describe('Features', () => {
    it('uses a structured capability list instead of interchangeable cards', () => {
        const { container } = render(<Features />);

        expect(container.querySelector('section')).toHaveAttribute('id', 'capabilities');
        expect(container.querySelectorAll('[data-slot="card"]')).toHaveLength(0);
        expect(screen.getByRole('heading', { name: 'What the dashboard shows' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Daily market snapshots' })).toBeInTheDocument();
    });

    it('centers every capability icon', () => {
        const { container } = render(<Features />);
        const icons = container.querySelectorAll('article > svg');

        expect(icons).toHaveLength(3);
        icons.forEach((icon) => expect(icon).toHaveClass('mx-auto'));
    });
});
