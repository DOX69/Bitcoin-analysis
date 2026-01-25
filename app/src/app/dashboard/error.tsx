
'use client';

import { useEffect } from 'react';

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error(error);
    }, [error]);

    return (
        <div className="min-h-screen bg-[#141414] text-white flex items-center justify-center p-6">
            <div className="max-w-md w-full bg-[#1c1c1c] border border-red-500/20 rounded-2xl p-8 text-center shadow-2xl">
                <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                    <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                </div>
                <h2 className="text-2xl font-bold mb-2">Something went wrong!</h2>
                <p className="text-gray-400 mb-8">
                    We encountered an error while loading the dashboard data. Please try again or contact support if the problem persists.
                </p>
                <div className="flex gap-4 justify-center">
                    <button
                        onClick={() => reset()}
                        className="px-6 py-2 bg-[#F7931A] text-black font-semibold rounded-lg hover:bg-[#e08215] transition-colors"
                    >
                        Try again
                    </button>
                    <a
                        href="/"
                        className="px-6 py-2 bg-gray-800 text-white font-semibold rounded-lg hover:bg-gray-700 transition-colors"
                    >
                        Go Home
                    </a>
                </div>
            </div>
        </div>
    );
}
