import fs from 'node:fs';
import path from 'node:path';

describe('global UI hygiene', () => {
    const css = fs.readFileSync(path.join(process.cwd(), 'src/app/globals.css'), 'utf8');
    const layout = fs.readFileSync(path.join(process.cwd(), 'src/app/layout.tsx'), 'utf8');
    const dashboardPage = fs.readFileSync(path.join(process.cwd(), 'src/app/dashboard/page.tsx'), 'utf8');
    const gitignore = fs.readFileSync(path.join(process.cwd(), '..', '.gitignore'), 'utf8');

    it('uses the design-system colors and excludes retired visual utilities', () => {
        expect(css).toContain('--primary: #f7931a');
        expect(css).toContain('--background: #07090a');
        expect(css).toContain('--card: #0b0d0f');
        expect(css).not.toMatch(/\.gradient-text|\.glass-card|\.energy-glow|\.gradient-border/);
        expect(css).not.toContain('transition: all');
    });

    it('does not mount the decorative Unicorn scene across every route', () => {
        expect(layout).not.toContain('@/components/EnergyBeam');
        expect(layout).not.toContain('<EnergyBeam />');
    });

    it('keeps local dashboard prototypes out of the nominal route', () => {
        expect(dashboardPage).not.toMatch(/PrototypeD|prototypeVariant|variant\?:/);
        expect(gitignore).toContain('app/src/components/dashboard/prototype/');
    });
});
