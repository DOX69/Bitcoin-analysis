'use client';

import type { PrototypeLayoutProps } from './types';

export default function VariantC({
    chart, controls, periodControls, scenarioControls, details, status,
    comparison, enabled, emissionCount, onEnable,
}: PrototypeLayoutProps) {
    return <div className="fpc" data-variant-layout="C">
        <header className="fpc-heading">
            <div>
                <h2>Table de comparaison</h2>
                <p>Comparer les médianes et les bandes de chaque émission au même horizon.</p>
            </div>
            <span className="fpc-count">{enabled ? `${emissionCount} émissions affichées` : 'Forecast désactivé'}</span>
        </header>

        <section className="fpc-commands" aria-label="Filtres de comparaison">
            <div className="fpc-display">{controls}</div>
            <div className="fpc-period">{periodControls}</div>
            <div className="fpc-scenario">{scenarioControls}</div>
        </section>

        {status}

        <section className="fpc-comparison" aria-label="Comparaison des émissions">
            {enabled ? comparison : <>
                <div className="fpc-column-preview" aria-hidden="true">
                    <span>Émission</span><span>Échéance</span><span>Médiane Q50</span><span>Bande Q25–Q75</span>
                </div>
                <div className="fpc-empty">
                    <div>
                        <h3>Une ligne par émission</h3>
                        <p>Activez Forecast pour comparer les valeurs de 1 à 52 semaines.</p>
                    </div>
                    <button type="button" onClick={onEnable}>Activer Forecast</button>
                </div>
            </>}
        </section>

        <div className="fpc-context">
            <section className="fpc-timeline" aria-label="Contexte temporel">
                <div className="fpc-section-heading"><h3>Repères dans le temps</h3><span>{enabled ? 'Toutes les émissions superposées' : 'Prix observé'}</span></div>
                {chart}
            </section>
            <aside className="fpc-audit">
                <h3>Lire la comparaison</h3>
                <p>Un même horizon correspond à des dates différentes selon l’émission.</p>
                <p>Q50 est la médiane. La bande Q25–Q75 a un niveau nominal de 50 %. Sa couverture réelle n’est pas garantie.</p>
                <details className="fpc-disclosure">
                    <summary>Dates, modèle et conversion</summary>
                    {enabled ? details : <p>Les métadonnées de chaque émission seront consultables après activation de Forecast.</p>}
                </details>
            </aside>
        </div>

        <style jsx global>{`
            .fpc {min-width:0}
            .fpc-heading {display:flex;justify-content:space-between;align-items:center;gap:20px;margin:26px 0 18px}
            .fpc .fpc-heading h2 {font-size:24px;font-weight:650;line-height:1.3}
            .fpc-heading p {margin:6px 0 0;max-width:680px}
            .fpc-count {flex-shrink:0;font-size:12px;color:#f6bb76;border:1px solid #f7931a66;padding:7px 10px;border-radius:4px}
            .fpc-commands {display:grid;grid-template-columns:minmax(0,1fr) 270px;background:var(--card);border:1px solid var(--border);border-radius:8px 8px 0 0;padding:0 18px}
            .fpc-display {grid-column:1 / -1;border-bottom:1px solid var(--border)}
            .fpc-period {min-width:0;padding-right:18px}
            .fpc-scenario {min-width:0;border-left:1px solid var(--border);padding-left:18px;display:flex;align-items:center}
            .fpc-scenario .fp-scenario {border:0;padding:10px 0;width:100%}
            .fpc-scenario select {width:100%;min-width:0}
            .fpc .fp-status {margin:12px 0}
            .fpc-comparison {min-width:0;margin-top:18px;border:1px solid var(--border);background:var(--card);border-radius:8px;overflow:hidden}
            .fpc-column-preview {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;background:var(--secondary);border-bottom:1px solid var(--border);padding:15px 20px;font-size:12px;color:#d4d4d4}
            .fpc-empty {min-height:165px;padding:28px 20px;display:flex;align-items:center;justify-content:space-between;gap:24px}
            .fpc h3 {font-size:15px;font-weight:600;line-height:1.4}
            .fpc-empty p {margin-top:8px;max-width:530px}
            .fpc-empty button {flex-shrink:0;background:#f7931a;color:#17110a;border-color:#f7931a;font-weight:600}
            .fpc-context {display:grid;grid-template-columns:minmax(0,2fr) minmax(260px,1fr);gap:24px;margin-top:26px;align-items:start}
            .fpc-timeline {min-width:0}
            .fpc-section-heading {display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:12px}
            .fpc-section-heading span {font-size:12px;color:var(--muted-foreground)}
            .fpc-timeline .fp-chart {padding:12px;border-radius:6px}
            .fpc-timeline .fp-chart svg {min-height:180px;max-height:290px}
            .fpc-timeline .fp-legend {margin-bottom:10px;font-size:12px;gap:10px}
            .fpc-audit {padding:0 0 0 24px;border-left:1px solid var(--border);min-width:0}
            .fpc-audit > p {font-size:13px;margin:10px 0 16px}
            .fpc-disclosure {border-top:1px solid var(--border);margin-top:20px}
            .fpc-disclosure summary {cursor:pointer;padding:15px 0;min-height:44px;font-weight:500;color:#f6bb76}
            .fpc-disclosure summary:focus-visible {outline:2px solid #f7931a;outline-offset:3px}
            .fpc-disclosure .fp-details {border:0;padding:0;margin:0}
            .fpc-disclosure dl {grid-template-columns:repeat(2,minmax(0,1fr))}
            .fpc-disclosure .fp-emissions {gap:6px}
            .fpc-disclosure .fp-emissions button {font-size:12px;padding:6px 8px}
            @media(max-width:1000px) {
                .fpc-commands {grid-template-columns:minmax(0,1fr)}
                .fpc-period {padding-right:0}
                .fpc-scenario {border-left:0;border-top:1px solid var(--border);padding-left:0}
                .fpc-context {grid-template-columns:minmax(0,1fr)}
                .fpc-audit {padding:18px 0 0;border-left:0;border-top:1px solid var(--border)}
            }
            @media(max-width:600px) {
                .fpc-heading {align-items:flex-start;flex-direction:column;gap:12px;margin-top:20px}
                .fpc .fpc-heading h2 {font-size:21px}
                .fpc-commands {padding:0 12px}
                .fpc .fp-controls label {min-width:0;flex-basis:calc(50% - 10px)}
                .fpc .fp-controls select,.fpc .fp-controls input[type=date] {width:100%;min-width:0}
                .fpc-column-preview {grid-template-columns:1fr 1fr;padding:12px;row-gap:8px}
                .fpc-empty {align-items:flex-start;flex-direction:column;padding:22px 14px;gap:18px}
                .fpc-section-heading {align-items:flex-start;flex-direction:column;gap:4px}
                .fpc-context {gap:18px;margin-top:22px}
                .fpc-timeline .fp-chart svg {min-height:210px;max-height:none}
            }
        `}</style>
    </div>;
}
