import fs from 'node:fs';
import path from 'node:path';

describe('global UI hygiene', () => {
    const css = fs.readFileSync(path.join(process.cwd(), 'src/app/globals.css'), 'utf8');
    const button = fs.readFileSync(path.join(process.cwd(), 'src/components/ui/button.tsx'), 'utf8');
    const statCard = fs.readFileSync(path.join(process.cwd(), 'src/components/dashboard/cards/StatCard.tsx'), 'utf8');
    const layout = fs.readFileSync(path.join(process.cwd(), 'src/app/layout.tsx'), 'utf8');
    const dashboardPage = fs.readFileSync(path.join(process.cwd(), 'src/app/dashboard/page.tsx'), 'utf8');
    const gitignore = fs.readFileSync(path.join(process.cwd(), '..', '.gitignore'), 'utf8');

    it('uses the design-system colors and excludes retired visual utilities', () => {
        expect(css).toContain('--primary: #f7931a');
        expect(css).toContain('--background: #07090a');
        expect(css).toContain('--card: #0b0d0f');
        expect(css).not.toMatch(/\.gradient-text|\.glass-card|\.energy-glow|\.gradient-border/);
        expect(css).not.toContain('transition: all');
        expect(css).toContain('box-shadow:');
        expect(css).not.toContain('border: 1px solid var(--border)');
    });

    it('gives actions tactile feedback and keeps KPI numerals stable', () => {
        expect(button).toContain('active:not-disabled:scale-[0.96]');
        expect(statCard).toContain('tabular-nums');
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
