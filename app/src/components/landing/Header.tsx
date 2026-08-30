'use client';

import Link from 'next/link';
import Image from 'next/image';
import { buttonVariants } from '@/components/ui/button';

export default function Header() {
    return (
        <header className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md bg-black/50 border-b border-white/5">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-2">
                        <Image
                            src="/logo_B_ai_bg_removed.png"
                            alt="B.ai - Bitcoin AI Analysis"
                            width={80}
                            height={40}
                            className="h-10 w-auto object-contain"
                            priority
                        />
                    </Link>

                    {/* Navigation */}
                    <nav className="hidden md:flex items-center gap-8">
                        <Link href="#features" className={buttonVariants({ variant: 'ghost', size: 'sm' })}>
                            Getting started
                        </Link>
                        <Link href="#components" className={buttonVariants({ variant: 'ghost', size: 'sm' })}>
                            Components
                        </Link>
                        <Link href="#docs" className={buttonVariants({ variant: 'ghost', size: 'sm' })}>
                            Documentation
                        </Link>
                    </nav>

                    {/* Auth Buttons */}
                    <div className="flex items-center gap-3">
                        <Link href="/login" className={buttonVariants({ variant: 'ghost', size: 'sm' })}>
                            Sign in
                        </Link>
                        <Link href="/signup" className={buttonVariants({ size: 'sm' })}>
                            Sign up
                        </Link>
                    </div>
                </div>
            </div>
        </header>
    );
}
