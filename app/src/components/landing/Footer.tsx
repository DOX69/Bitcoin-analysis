'use client';

import Link from 'next/link';
import { theme } from '@/theme';

export default function Footer() {
    const currentYear = new Date().getFullYear();

    return (
        <footer className="relative py-12 px-4 border-t border-white/5">
            <div className="max-w-6xl mx-auto">
                <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                    {/* Copyright */}
                    <div className="text-sm text-gray-500">
                        © {currentYear} B.ai - Bitcoin Intelligence. All rights reserved.
                    </div>

                    {/* Links */}
                    <nav className="flex items-center gap-6">
                        <Link
                            href="/privacy"
                            className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
                        >
                            Privacy
                        </Link>
                        <Link
                            href="/terms"
                            className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
                        >
                            Terms
                        </Link>
                        <Link
                            href="https://github.com"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
                        >
                            GitHub
                        </Link>
                    </nav>

                    {/* Powered By */}
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                        <span>Powered by</span>
                        <span
                            className="font-medium"
                            style={{ color: theme.colors.primary.orange }}
                        >
                            Databricks
                        </span>
                    </div>
                </div>
            </div>
        </footer>
    );
}
