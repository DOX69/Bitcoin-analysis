'use client';

import Link from 'next/link';
import Image from 'next/image';
import { buttonVariants } from '@/components/ui/button';

export default function Header() {
    return (
        <header className="fixed inset-x-0 top-0 z-50 border-b border-white/5 bg-black/90">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    <Link
                        href="/"
                        className="flex min-h-11 items-center gap-2 rounded-lg px-1 outline-none transition-opacity duration-200 hover:opacity-90 focus-visible:ring-3 focus-visible:ring-ring/50"
                        aria-label="B.ai home"
                    >
                        <Image
                            src="/logo_B_ai_bg_removed.png"
                            alt=""
                            width={48}
                            height={45}
                            className="object-contain outline outline-1 -outline-offset-1 outline-white/10"
                            priority
                        />
                        <span className="text-base font-semibold text-white">B.ai</span>
                    </Link>

                    <nav className="hidden items-center gap-2 md:flex" aria-label="Landing navigation">
                        <Link href="#capabilities" className={buttonVariants({ variant: 'ghost', size: 'sm' })}>
                            Capabilities
                        </Link>
                        <Link
                            href="https://github.com/DOX69/Bitcoin-analysis"
                            target="_blank"
                            rel="noopener noreferrer"
                            className={buttonVariants({ variant: 'ghost', size: 'sm' })}
                        >
                            Source code
                        </Link>
                    </nav>

                    <Link href="/dashboard" className={buttonVariants({ size: 'sm', className: 'min-h-11' })}>
                        Open dashboard
                    </Link>
                </div>
            </div>
        </header>
    );
}
