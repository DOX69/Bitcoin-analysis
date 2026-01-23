import { theme } from '../index';
import colors from '../colors.json';

describe('Theme System', () => {
    it('should export colors matches json source', () => {
        expect(theme.colors).toEqual(colors);
    });

    it('should have correct primary orange color', () => {
        expect(theme.colors.primary.orange).toBe('#FF6B35');
    });

    it('should generate correct usage css variables', () => {
        expect(theme.cssVariables['--color-primary-orange']).toBe('#FF6B35');
        expect(theme.cssVariables['--color-bg-landing-gradient']).toBeDefined();
    });

    it('should export typography and spacing', () => {
        expect(theme.typography).toBeDefined();
        expect(theme.spacing).toBeDefined();
        expect(theme.typography.sizes.base).toBe('16px');
        expect((theme.spacing as any).start).toBeUndefined(); // ensure no random props
        expect(theme.spacing.md).toBe('16px');
    });
});
