'use client';

import type { PrototypeLayoutProps } from './types';

export default function VariantB({
    chart, controls, periodControls, scenarioControls, details, status,
    enabled, emissionCount, emissionPanels, onEnable,
}: PrototypeLayoutProps) {
    return <section className="fpb" aria-label="Journal des émissions">
        <header className="fpb-heading">
            <div>
                <h2>Journal des émissions</h2>
                <p>Une ligne par émission. Comparez les prévisions à leur date de publication.</p>
            </div>
            <span className="fpb-count">{enabled ? `${emissionCount} émissions dans la période` : 'Prévisions désactivées'}</span>
        </header>

        <div className="fpb-toolbar">{controls}{periodControls}</div>
        <div className="fpb-scenarios">{scenarioControls}</div>
        {enabled && <div className="fpb-status">{status}</div>}

        <div className="fpb-journal">
            <section className="fpb-row fpb-observed" aria-label="Vue d’ensemble du journal">
                <div className="fpb-margin">
                    <span className="fpb-dot" aria-hidden="true" />
                    <h3>{enabled ? 'Vue d’ensemble' : 'Prix observé'}</h3>
                    <p>{enabled ? 'Le prix et les émissions sur une même période.' : 'L’historique reste visible. Activez Forecast pour ouvrir le journal des prévisions.'}</p>
                    <span className="fpb-line-key"><span aria-hidden="true" /> Prix observé</span>
                </div>
                <div className="fpb-plot fpb-overview">{chart}</div>
            </section>

            {enabled ? <>
                <div className="fpb-journal-label"><span>Publication et provenance</span><span>Mêmes dates et même échelle sur chaque ligne</span></div>
                {emissionPanels.map((emission) => <article className="fpb-row fpb-emission" key={emission.id} aria-label={`Émission ${emission.title}`}>
                    <div className="fpb-margin">
                        <span className="fpb-dot" aria-hidden="true" />
                        <h3>{emission.title}</h3>
                        <div className="fpb-meta">{emission.meta}</div>
                    </div>
                    <div className="fpb-plot">{emission.chart}</div>
                </article>)}
                {emissionPanels.length === 0 && <div className="fpb-empty"><h3>Aucune émission dans cette période</h3><p>Modifiez les dates ou le scénario pour consulter une émission conservée.</p></div>}
            </> : <div className="fpb-row fpb-activation">
                <div className="fpb-margin"><span className="fpb-dot fpb-dot-muted" aria-hidden="true" /><h3>Prévisions</h3><p>Journal fermé</p></div>
                <div className="fpb-enable-content"><h3>Retrouver chaque publication</h3><p>Les émissions s’affichent les unes sous les autres, avec leur bande Q25–Q75, leur médiane et leur provenance.</p><button type="button" onClick={onEnable}>Activer Forecast</button></div>
            </div>}
        </div>

        {enabled && emissionPanels.length > 0 && <details className="fpb-inspector">
            <summary>Inspecter une échéance précise</summary>
            {details}
        </details>}

        <style jsx global>{`
            .fpb { min-width: 0; }
            .fpb .fpb-heading { display: flex; align-items: start; justify-content: space-between; gap: 20px; padding: 22px 0 18px; }
            .fpb .fpb-heading h2 { font-size: 22px; line-height: 1.3; font-weight: 650; margin: 0; }
            .fpb .fpb-heading p { margin: 8px 0 0; max-width: 65ch; }
            .fpb .fpb-count { flex-shrink: 0; color: #c6c6c6; font-size: 12px; padding-top: 7px; }
            .fpb .fpb-toolbar { padding: 4px 0 14px; border-top: 1px solid var(--border); }
            .fpb .fpb-journal { border-top: 1px solid var(--border); }
            .fpb .fpb-row { display: grid; grid-template-columns: 236px minmax(0, 1fr); gap: 24px; padding: 24px 0; border-bottom: 1px solid var(--border); }
            .fpb .fpb-margin { position: relative; min-width: 0; padding: 6px 0 0 22px; }
            .fpb .fpb-margin:before { content: ''; position: absolute; top: 22px; bottom: -25px; left: 4px; width: 1px; background: var(--border); }
            .fpb .fpb-row:last-child .fpb-margin:before { bottom: 0; }
            .fpb .fpb-dot { position: absolute; top: 12px; left: 0; width: 9px; height: 9px; border: 2px solid #c6c6c6; border-radius: 50%; background: var(--background); }
            .fpb .fpb-observed .fpb-dot { border-color: #f7931a; background: #f7931a; }
            .fpb .fpb-dot-muted { border-color: #8b8b8b; }
            .fpb h3 { font-size: 15px; line-height: 1.4; font-weight: 600; margin: 0; }
            .fpb .fpb-margin p { font-size: 13px; line-height: 1.6; margin: 10px 0; }
            .fpb .fpb-line-key { display: inline-flex; align-items: center; gap: 8px; margin-top: 12px; font-size: 12px; color: #fbb665; }
            .fpb .fpb-line-key > span { display: inline-block; width: 20px; height: 2px; background: #f7931a; }
            .fpb .fpb-plot { min-width: 0; }
            .fpb .fpb-plot .fp-chart { border: 0; border-radius: 0; background: transparent; padding: 0; }
            .fpb .fpb-plot svg { display: block; width: 100%; height: auto; min-height: 170px; max-height: 280px; }
            .fpb .fpb-journal-label { display: grid; grid-template-columns: 236px minmax(0, 1fr); gap: 24px; padding: 13px 0; color: #b8b8b8; font-size: 12px; border-bottom: 1px solid var(--border); }
            .fpb .fpb-journal-label > span:first-child { padding-left: 22px; }
            .fpb .fpb-meta { font-size: 12px; line-height: 1.7; overflow-wrap: anywhere; }
            .fpb .fpb-meta dl { display: block; margin: 12px 0 0; }
            .fpb .fpb-meta dl > div { margin: 10px 0; }
            .fpb .fpb-meta dd { margin-top: 2px; font-size: 13px; }
            .fpb .fpb-activation { padding-bottom: 32px; }
            .fpb .fpb-enable-content { padding: 20px 0; max-width: 65ch; }
            .fpb .fpb-enable-content p { margin: 10px 0 20px; }
            .fpb .fpb-enable-content button { background: #f7931a; color: #17110a; border-color: #f7931a; font-weight: 600; }
            .fpb .fpb-enable-content button:hover { background: #ffb152; }
            .fpb .fpb-enable-content button:focus-visible { outline: 2px solid #f7931a; outline-offset: 4px; }
            .fpb .fpb-empty { padding: 28px 0 28px 22px; }
            .fpb .fpb-empty p { margin-top: 8px; }
            .fpb .fpb-status { margin-top: 20px; }
            .fpb .fpb-inspector { border-bottom: 1px solid var(--border); padding: 8px 0 16px; }
            .fpb .fpb-inspector summary { padding: 14px 0; cursor: pointer; font-weight: 500; }
            .fpb .fpb-inspector summary:focus-visible { outline: 2px solid #f7931a; outline-offset: 3px; }
            .fpb .fpb-inspector .fp-details { margin-top: 0; }
            .fpb .fpb-scenarios { margin-top: 20px; }
            @media (max-width: 800px) {
                .fpb .fpb-heading { flex-direction: column; gap: 8px; }
                .fpb .fpb-count { padding-top: 0; }
                .fpb .fpb-row { grid-template-columns: minmax(0, 1fr); gap: 16px; padding: 20px 0; }
                .fpb .fpb-margin:before { display: none; }
                .fpb .fpb-margin p { margin: 6px 0; }
                .fpb .fpb-line-key { margin-top: 4px; }
                .fpb .fpb-meta dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 16px; }
                .fpb .fpb-meta dl > div { margin: 0; }
                .fpb .fpb-journal-label { display: block; padding: 12px 0; }
                .fpb .fpb-journal-label > span:first-child { display: none; }
                .fpb .fpb-plot svg { max-height: none; min-height: 180px; }
                .fpb .fpb-enable-content { padding: 0 0 4px 22px; }
            }
            @media (max-width: 380px) {
                .fpb .fpb-heading h2 { font-size: 20px; }
                .fpb .fpb-meta dl { grid-template-columns: minmax(0, 1fr); }
            }
        `}</style>
    </section>;
}
