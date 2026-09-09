'use client';

import { useEffect, useState } from 'react';
import type { PrototypeLayoutProps } from './types';

export default function VariantA({
    chart, controls, periodControls, scenarioControls, details, status,
    enabled, emissionCount, onEnable,
}: PrototypeLayoutProps) {
    const [settingsOpen, setSettingsOpen] = useState(true);

    useEffect(() => {
        const query = window.matchMedia('(max-width: 850px)');
        const update = () => setSettingsOpen(!query.matches);
        update();
        query.addEventListener('change', update);
        return () => query.removeEventListener('change', update);
    }, []);

    return <section className="fpa" aria-label="Atelier graphique">
        <header className="fpa-heading">
            <div><h2>Atelier graphique</h2><p>Lire le prix et les prévisions sur une même courbe.</p></div>
            <span className="fpa-layer-count">{enabled ? `${emissionCount} émissions affichées` : 'Prix observé seul'}</span>
        </header>
        <div className="fpa-workspace">
            <div className="fpa-canvas">
                {enabled && <div className="fpa-status">{status}</div>}
                <div className="fpa-plot">{chart}</div>
                <div className="fpa-period"><h3>Période historique</h3>{periodControls}</div>
                {enabled ? <div className="fpa-inspector">{details}</div> : <div className="fpa-off">
                    <div><h3>Ajouter les prévisions</h3><p>Superposer les émissions et leur bande Q25–Q75 au prix observé.</p></div>
                    <button type="button" onClick={onEnable}>Activer Forecast</button>
                </div>}
            </div>
            <aside className="fpa-rail" aria-label="Réglages de l’atelier">
                <details open={settingsOpen} onToggle={(event) => setSettingsOpen(event.currentTarget.open)}>
                    <summary>Réglages du graphique <span>{settingsOpen ? '−' : '+'}</span></summary>
                    <div className="fpa-settings">
                        <h3>Affichage</h3>
                        {controls}
                        <div className="fpa-scenario"><h3>État des prévisions</h3>{scenarioControls}</div>
                        <p className="fpa-note">Le prix suit la fréquence choisie. Les prévisions gardent leurs échéances hebdomadaires.</p>
                    </div>
                </details>
            </aside>
        </div>
        <style jsx global>{`
            .fpa {border:1px solid var(--border);border-radius:10px;overflow:clip;background:var(--card)}
            .fpa .fpa-heading {display:flex;align-items:center;justify-content:space-between;gap:18px;padding:20px 24px;border-bottom:1px solid var(--border)}
            .fpa .fpa-heading h2 {font-size:20px;font-weight:600;letter-spacing:-.02em;margin:0}
            .fpa .fpa-heading p {margin:4px 0 0;font-size:13px}
            .fpa .fpa-layer-count {font-size:12px;white-space:nowrap;color:#c4c4c4;font-variant-numeric:tabular-nums}
            .fpa .fpa-workspace {display:grid;grid-template-columns:minmax(0,1fr) 250px;align-items:stretch}
            .fpa .fpa-canvas {min-width:0;padding:24px}
            .fpa .fpa-plot .fp-chart {border:0;padding:0;border-radius:0;background:transparent}
            .fpa .fpa-plot svg {min-height:320px}
            .fpa .fpa-status .fp-status {margin:0 0 20px}
            .fpa .fpa-period {border-top:1px solid var(--border);margin-top:22px;padding-top:16px}
            .fpa h3 {font-size:13px;font-weight:600;color:var(--foreground);margin:0 0 10px}
            .fpa .fpa-period .fp-controls {gap:8px;margin:0}
            .fpa .fpa-period button {font-size:12px}
            .fpa .fpa-period label {font-size:12px}
            .fpa .fpa-rail {min-width:0;background:var(--secondary);border-left:1px solid var(--border)}
            .fpa .fpa-rail summary {display:none;cursor:pointer;min-height:48px;font-weight:500;list-style:none}
            .fpa .fpa-rail summary::-webkit-details-marker {display:none}
            .fpa .fpa-rail summary:focus-visible {outline:2px solid #f7931a;outline-offset:-4px}
            .fpa .fpa-settings {padding:24px 18px}
            .fpa .fpa-settings .fp-controls {display:flex;flex-direction:column;align-items:stretch;gap:18px;margin:0}
            .fpa .fpa-settings .fp-controls label {width:100%;min-width:0;margin:0;font-size:12px}
            .fpa .fpa-settings .fp-controls label:first-child:has([type=checkbox]) {padding-bottom:16px;border-bottom:1px solid var(--border);font-size:14px}
            .fpa .fpa-settings :is(select,input:not([type=checkbox])) {width:100%;min-width:0;background:var(--background)}
            .fpa .fpa-scenario {margin-top:28px;padding-top:20px;border-top:1px solid var(--border)}
            .fpa .fpa-scenario .fp-scenario {border:0;padding:0;margin:0}
            .fpa .fpa-scenario label {font-size:12px}
            .fpa .fpa-note {font-size:12px;line-height:1.6;margin-top:20px;color:#b8b8b8}
            .fpa .fpa-inspector .fp-details {margin-top:24px}
            .fpa .fpa-inspector dl {grid-template-columns:repeat(2,minmax(0,1fr))}
            .fpa .fpa-off {display:flex;align-items:center;justify-content:space-between;gap:20px;border-top:1px solid var(--border);padding-top:22px;margin-top:24px}
            .fpa .fpa-off h3 {margin:0 0 4px;font-size:14px}
            .fpa .fpa-off p {font-size:12px;max-width:52ch;margin:0}
            .fpa .fpa-off button {flex-shrink:0;background:#f7931a;color:#17100a;border-color:#f7931a;font-weight:600}
            .fpa .fpa-off button:hover {background:#ffab42}
            @media(max-width:1100px) and (min-width:851px) {
                .fpa .fpa-workspace {grid-template-columns:minmax(0,1fr) 220px}
                .fpa .fpa-canvas {padding:18px}
                .fpa .fpa-period .fp-controls label {flex:1;min-width:120px}
                .fpa .fpa-off {align-items:flex-start;flex-direction:column;gap:12px}
            }
            @media(max-width:850px) {
                .fpa .fpa-heading {padding:16px;align-items:flex-start;flex-direction:column;gap:8px}
                .fpa .fpa-heading h2 {font-size:18px}
                .fpa .fpa-workspace {display:flex;flex-direction:column}
                .fpa .fpa-rail {order:-1;border-left:0;border-bottom:1px solid var(--border)}
                .fpa .fpa-rail summary {display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;font-size:13px}
                .fpa .fpa-settings {padding:6px 16px 18px}
                .fpa .fpa-settings .fp-controls {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
                .fpa .fpa-settings .fp-controls label:first-child:has([type=checkbox]) {grid-column:1/-1;padding-bottom:10px}
                .fpa .fpa-scenario {margin-top:18px;padding-top:14px}
                .fpa .fpa-note {margin-top:12px}
                .fpa .fpa-canvas {padding:16px 12px}
                .fpa .fpa-plot svg {min-height:220px}
                .fpa .fpa-period {margin-top:16px}
                .fpa .fpa-period .fp-controls label {flex:0 0 calc(50% - 4px);min-width:0}
                .fpa .fpa-period .fp-controls button {flex:1 1 calc(50% - 4px);white-space:normal}
                .fpa .fpa-off {align-items:flex-start;flex-direction:column;gap:12px;margin-top:18px;padding-top:18px}
                .fpa .fpa-inspector dl {gap:14px}
                .fpa .fpa-inspector dd {overflow-wrap:anywhere}
            }
        `}</style>
    </section>;
}
