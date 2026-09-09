'use client';

import { useId, useState } from 'react';
import { Info, X } from 'lucide-react';

interface ForecastPrototypeProps {
    enabled: boolean;
    onEnabledChange: (value: boolean) => void;
    model: string;
    onModelChange: (value: string) => void;
    emissions: { id: string; issued: string }[];
    selectedIds: string[];
    onSelectionChange: (ids: string[]) => void;
}

// Local prototype controls. Model names refer to simulated projections only.
export default function ForecastPrototype({ enabled, onEnabledChange, model, onModelChange, emissions, selectedIds, onSelectionChange }: ForecastPrototypeProps) {
    const infoId = useId();
    const historyId = useId();
    const [historyPosition, setHistoryPosition] = useState({ top: 0, left: 0 });
    const [historyOpen, setHistoryOpen] = useState(false);

    return <div className="forecast-controls forecast-controls-A">
        <div className="forecast-controls-group">
            <label className="forecast-toggle">
                <input type="checkbox" checked={enabled} onChange={(event) => onEnabledChange(event.target.checked)} />
                <span>Forecast</span>
            </label>
            <select aria-label="Modèle de prévision" value={model} onChange={(event) => onModelChange(event.target.value)}>
                <option value="recommended">Modèle recommandé (démo)</option>
                <option value="alternative">Autre modèle (démo)</option>
            </select>
            <button className="forecast-info" type="button" popoverTarget={infoId} aria-label="À propos des prévisions"><Info size={17} aria-hidden="true" /></button>
        </div>
        <button type="button" className="forecast-history-trigger" popoverTarget={historyId} disabled={!emissions.length} aria-expanded={historyOpen} aria-controls={historyId} onClick={(event) => {
            const rect = event.currentTarget.getBoundingClientRect();
            setHistoryPosition({ top: Math.max(8, Math.min(rect.bottom + 6, window.innerHeight - 190)), left: Math.max(8, Math.min(rect.left, window.innerWidth - 288)) });
        }}>Prévisions · {selectedIds.length === 1 && selectedIds[0] === emissions[0]?.id ? 'Dernière' : `${selectedIds.length} sélectionnée${selectedIds.length > 1 ? 's' : ''}`} ▾</button>
        <div id={historyId} popover="auto" className="forecast-history" style={historyPosition} onToggle={(event) => setHistoryOpen(event.newState === 'open')}>
            <p>3 dernières prévisions</p>
            {emissions.map((emission, index) => <label key={emission.id}>
                <input type="checkbox" checked={selectedIds.includes(emission.id)} onChange={(event) => onSelectionChange(event.target.checked ? [...selectedIds, emission.id] : selectedIds.filter((id) => id !== emission.id))} />
                {new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${emission.issued}T00:00:00Z`))}{index === 0 && <small>Dernière</small>}
            </label>)}
        </div>
        <small className="forecast-demo">Projections simulées</small>
        <div id={infoId} popover="auto" className="forecast-explanation" aria-label="À propos des prévisions">
            <button className="forecast-close" type="button" popoverTarget={infoId} popoverTargetAction="hide" aria-label="Fermer les informations"><X size={18} aria-hidden="true" /></button>
            <p>À partir de l’évolution passée du Bitcoin, le modèle estime son prix semaine par semaine pour les 12 prochains mois. La médiane donne l’estimation centrale, entourée d’une estimation basse et haute. Les prévisions sont mises à jour chaque semaine, sans effacer les anciennes. Le prix réel peut sortir de cette zone : ce n’est pas une garantie.</p>
        </div>
        <style jsx global>{`
            .forecast-controls {display:flex;align-items:center;flex-wrap:wrap;gap:8px 14px;color:var(--foreground);font-size:13px}
            .forecast-controls .forecast-controls-group {display:flex;align-items:center;flex-wrap:wrap;gap:8px;min-width:0;max-width:100%}
            .forecast-controls .forecast-toggle {display:flex;align-items:center;gap:8px;min-height:40px;cursor:pointer;white-space:nowrap;font-weight:500}
            .forecast-controls .forecast-toggle input {width:16px;height:16px;accent-color:#f7931a;cursor:pointer}
            .forecast-controls select {min-height:40px;min-width:0;max-width:100%;background:var(--background);color:var(--foreground);border:1px solid var(--border);border-radius:6px;padding:6px 28px 6px 10px;font:inherit;cursor:pointer}
            .forecast-controls .forecast-info,.forecast-controls .forecast-close {display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;padding:0;flex-shrink:0;background:transparent;border:1px solid transparent;border-radius:6px;color:var(--muted-foreground);cursor:pointer}
            .forecast-controls .forecast-info:hover,.forecast-controls .forecast-close:hover {background:var(--secondary);color:var(--foreground)}
            .forecast-controls :is(input,select,button):focus-visible {outline:2px solid #f7931a;outline-offset:3px}
            .forecast-controls .forecast-demo {font-size:11px;color:var(--muted-foreground);white-space:nowrap}
            .forecast-controls .forecast-history-trigger {min-height:40px;padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--background);color:var(--foreground);font:inherit;cursor:pointer}
            .forecast-controls .forecast-history-trigger:disabled {opacity:.5;cursor:default}
            .forecast-controls .forecast-history {position:fixed;inset:auto;margin:0;width:min(280px,calc(100vw - 16px));padding:10px;background:var(--card);color:var(--foreground);border:1px solid var(--border);border-radius:8px;box-shadow:0 8px 24px #0006}
            .forecast-controls .forecast-history p {margin:0 8px 5px;color:var(--muted-foreground);font-size:12px}
            .forecast-controls .forecast-history label {display:flex;align-items:center;gap:10px;min-height:44px;padding:0 8px;cursor:pointer}
            .forecast-controls .forecast-history label:hover {background:var(--secondary)}
            .forecast-controls .forecast-history input {width:16px;height:16px;accent-color:#f7931a}
            .forecast-controls .forecast-history small {margin-left:auto;color:var(--muted-foreground)}
            .forecast-controls .forecast-explanation {position:fixed;inset:0;margin:auto;width:min(390px,calc(100vw - 32px));height:fit-content;padding:20px;background:var(--card);color:var(--foreground);border:1px solid var(--border);border-radius:10px;box-shadow:0 12px 48px #0006}
            .forecast-controls .forecast-explanation::backdrop {background:#0003}
            .forecast-controls .forecast-explanation p {margin:6px 0 0;line-height:1.65;font-size:14px;clear:both}
            .forecast-controls .forecast-close {float:right;margin:-10px -10px 0 0}
            .forecast-controls-A {padding:10px 0}
            .forecast-controls-A .forecast-toggle {margin-right:4px}
            @media(max-width:480px) {
                .forecast-controls {gap:3px 10px}
                .forecast-controls .forecast-controls-group {width:100%;gap:4px}
                .forecast-controls .forecast-toggle {min-height:44px}
                .forecast-controls select {min-height:44px;flex:1 1 180px;width:180px;font-size:12px}
                .forecast-controls .forecast-info {width:44px;height:44px}
                .forecast-controls .forecast-demo {margin-left:0}
            }
        `}</style>
    </div>;
}
