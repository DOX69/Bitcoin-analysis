import React from 'react';
import { render } from '@testing-library/react';
import Features from '../Features';

describe('Features', () => {
    it('uses a shadcn Card for each feature', () => {
        const { container } = render(<Features />);

        expect(container.querySelectorAll('[data-slot="card"]')).toHaveLength(3);
    });
});
