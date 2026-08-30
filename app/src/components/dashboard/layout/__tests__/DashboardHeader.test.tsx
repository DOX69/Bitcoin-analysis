import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import DashboardHeader from '../DashboardHeader';

describe('DashboardHeader', () => {
    it('opens an accessible shadcn profile menu', () => {
        render(<DashboardHeader />);

        fireEvent.click(screen.getByRole('button', { name: /user/i }));

        expect(screen.getByRole('menu')).toBeInTheDocument();
        expect(screen.getByRole('menuitem', { name: 'Profile' })).toBeInTheDocument();
        expect(screen.getByRole('menuitem', { name: 'Settings' })).toBeInTheDocument();
    });
});
