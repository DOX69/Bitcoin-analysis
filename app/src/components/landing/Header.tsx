'use client';

import Link from 'next/link';
import Image from 'next/image';
import { theme } from '@/theme';

export default function Header() {
    return (
        <header className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md bg-black/50 border-b border-white/5">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-2">
                        <Image
                            src="/logo_B_ai.jpeg"
                            alt="B.ai - Bitcoin AI Analysis"
                            width={80}
                            height={40}
                            className="h-10 w-auto object-contain"
                            priority
                        />
                    </Link>

                    {/* Navigation */}
                    <nav className="hidden md:flex items-center gap-8">
                        <Link
                            href="#features"
                            className="text-sm text-gray-400 hover:text-white transition-colors"
                        >
                            Getting started
                        </Link>
                        <Link
                            href="#components"
                            className="text-sm text-gray-400 hover:text-white transition-colors"
                        >
                            Components
                        </Link>
                        <Link
                            href="#docs"
                            className="text-sm text-gray-400 hover:text-white transition-colors"
                        >
                            Documentation
                        </Link>
                    </nav>

                    {/* Auth Buttons */}
                    <div className="flex items-center gap-3">
                        <Link
                            href="/auth/login"
                            className="text-sm font-medium text-gray-300 hover:text-white transition-colors"
                        >
                            Sign in
                        </Link>
                        <Link
                            href="/auth/register"
                            className="px-4 py-2 text-sm font-medium text-white rounded-lg transition-all hover:scale-105"
                            style={{
                                background: `linear-gradient(135deg, ${theme.colors.primary.orange} 0%, #d85a2b 100%)`,
                            }}
                        >
                            Sign up
                        </Link>
                    </div>
                </div>
            </div>
        </header>
    );
}
