import { theme } from '../index';
import colors from '../colors.json';

describe('Theme System', () => {
    it('should export colors matches json source', () => {
        expect(theme.colors).toEqual(colors);
    });

    it('should have the canonical Bitcoin signal color', () => {
        expect(theme.colors.primary.orange).toBe('#F7931A');
    });

    it('should generate correct usage css variables', () => {
        expect(theme.cssVariables['--color-primary-orange']).toBe('#F7931A');
        expect(theme.cssVariables['--color-primary-black']).toBe('#07090A');
    });

    it('should export typography and spacing', () => {
        expect(theme.typography).toBeDefined();
        expect(theme.spacing).toBeDefined();
        expect(theme.typography.sizes.base).toBe('16px');
        expect(theme.spacing).not.toHaveProperty('start');
        expect(theme.spacing.md).toBe('16px');
    });
});
