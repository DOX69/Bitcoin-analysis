import type { ReactNode } from 'react';

export interface PrototypeLayoutProps {
    chart: ReactNode;
    controls: ReactNode;
    periodControls: ReactNode;
    scenarioControls: ReactNode;
    details: ReactNode;
    status: ReactNode;
    comparison: ReactNode;
    enabled: boolean;
    emissionCount: number;
    emissionPanels: { id: string; title: string; chart: ReactNode; meta: ReactNode }[];
    onEnable: () => void;
}
