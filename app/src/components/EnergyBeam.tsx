'use client';

import React, { useEffect, useRef } from 'react';

interface EnergyBeamProps {
    projectId?: string;
    className?: string;
}

declare global {
    interface UnicornStudioApi {
        init: () => void;
    }

    interface Window {
        UnicornStudio?: UnicornStudioApi;
    }
}

const EnergyBeam: React.FC<EnergyBeamProps> = ({
    projectId = "hRFfUymDGOHwtFe7evR2",
    className = ""
}) => {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v1.5.2/dist/unicornStudio.umd.js';
        script.async = true;

        script.onload = () => {
            if (window.UnicornStudio && containerRef.current) {
                window.UnicornStudio.init();
            }
        };

        document.head.appendChild(script);

        return () => {
            script.onload = null;
            script.remove();
        };
    }, [projectId]);

    return (
        <div className={`fixed inset-0 w-full h-screen bg-black overflow-hidden -z-10 ${className}`}>
            <div
                ref={containerRef}
                data-us-project={projectId}
                className="w-full h-full"
            />
        </div>
    );
};

export default EnergyBeam;
