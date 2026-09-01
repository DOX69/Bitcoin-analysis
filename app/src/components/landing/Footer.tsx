'use client';

import Link from 'next/link';

export default function Footer() {
    const currentYear = new Date().getFullYear();

    return (
        <footer className="relative border-t border-white/5 px-4 py-12">
            <div className="max-w-6xl mx-auto">
                <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="text-sm text-muted-foreground">
                        © {currentYear} B.ai. Bitcoin market analysis.
                    </div>

                    <nav className="flex items-center gap-6" aria-label="Footer navigation">
                        <Link
                            href="https://github.com/DOX69/Bitcoin-analysis"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                        >
                            Source code
                        </Link>
                    </nav>

                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span className="font-medium text-primary">PostgreSQL, updated daily</span>
                    </div>
                </div>
            </div>
        </footer>
    );
}
