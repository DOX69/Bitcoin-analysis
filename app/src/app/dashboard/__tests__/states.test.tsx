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

    it('uses a shadcn Alert without exposing internal error details', () => {
        const { container } = render(
            <ErrorState error={Object.assign(new Error('Database password leaked'), { digest: 'secret-digest' })} reset={jest.fn()} />,
        );

        expect(container.querySelector('[data-slot="alert"]')).toBeInTheDocument();
        expect(screen.getByText('Dashboard unavailable')).toBeInTheDocument();
        expect(screen.queryByText(/password leaked|secret-digest/i)).not.toBeInTheDocument();
    });
});
