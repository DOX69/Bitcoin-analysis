'use client';

import Link from 'next/link';

export default function Footer() {
    const currentYear = new Date().getFullYear();

    return (
        <footer className="relative py-12 px-4 border-t border-white/5">
            <div className="max-w-6xl mx-auto">
                <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="text-sm text-gray-500">
                        © {currentYear} B.ai. Bitcoin market analysis.
                    </div>

                    <nav className="flex items-center gap-6" aria-label="Footer navigation">
                        <Link
                            href="https://github.com/DOX69/Bitcoin-analysis"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
                        >
                            Source code
                        </Link>
                    </nav>

                    <div className="flex items-center gap-2 text-sm text-gray-500">
                        <span className="font-medium text-primary">PostgreSQL, updated daily</span>
                    </div>
                </div>
            </div>
        </footer>
    );
}
