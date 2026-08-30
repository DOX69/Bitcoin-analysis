import { StrictMode } from 'react';
import { render } from '@testing-library/react';
import EnergyBeam from '../EnergyBeam';

const UNICORN_STUDIO_SCRIPT =
    'https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v1.5.2/dist/unicornStudio.umd.js';

const getUnicornStudioScripts = () =>
    Array.from(document.querySelectorAll<HTMLScriptElement>('script')).filter(
        (script) => script.src === UNICORN_STUDIO_SCRIPT,
    );

describe('EnergyBeam UnicornStudio script lifecycle', () => {
    afterEach(() => {
        getUnicornStudioScripts().forEach((script) => script.remove());
    });

    it('keeps one script through StrictMode, project changes, and remounts', () => {
        const firstRender = render(
            <StrictMode>
                <EnergyBeam />
            </StrictMode>,
        );

        expect(getUnicornStudioScripts()).toHaveLength(1);

        getUnicornStudioScripts()[0].dispatchEvent(new Event('load'));
        firstRender.rerender(
            <StrictMode>
                <EnergyBeam projectId="different-project" />
            </StrictMode>,
        );

        expect(getUnicornStudioScripts()).toHaveLength(1);

        firstRender.unmount();
        expect(getUnicornStudioScripts()).toHaveLength(0);

        const secondRender = render(
            <StrictMode>
                <EnergyBeam />
            </StrictMode>,
        );

        expect(getUnicornStudioScripts()).toHaveLength(1);
        secondRender.unmount();
    });
});
