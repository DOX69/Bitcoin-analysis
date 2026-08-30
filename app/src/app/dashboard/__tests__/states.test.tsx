import React from 'react';
import { render, screen } from '@testing-library/react';
import Loading from '../loading';
import ErrorState from '../error';

jest.mock('next/navigation', () => ({
    useRouter: () => ({ push: jest.fn() }),
}));

describe('dashboard states', () => {
    beforeEach(() => {
        jest.spyOn(console, 'error').mockImplementation(() => undefined);
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    it('uses a shadcn Skeleton while loading', () => {
        const { container } = render(<Loading />);

        expect(container.querySelector('[data-slot="skeleton"]')).toBeInTheDocument();
    });

    it('uses a shadcn Alert for errors', () => {
        const { container } = render(
            <ErrorState error={new Error('Database unavailable')} reset={jest.fn()} />,
        );

        expect(container.querySelector('[data-slot="alert"]')).toBeInTheDocument();
        expect(screen.getByText('Database unavailable')).toBeInTheDocument();
    });
});
