import colors from './colors.json';
import typography from './typography.json';
import spacing from './spacing.json';

export const theme = {
    colors,
    typography,
    spacing,
    // Computed values for CSS
    cssVariables: {
        '--color-primary-orange': colors.primary.orange,
        '--color-primary-black': colors.primary.dark,
        '--color-text-primary': colors.text.primary,
        '--color-bg-landing-gradient': colors.backgrounds.gradient_landing,
    }
};

export default theme;
