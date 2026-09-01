import Image from 'next/image';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { buttonVariants } from '@/components/ui/button';

interface DemoAccessProps {
    message: string;
}

export default function DemoAccess({ message }: DemoAccessProps) {
    return (
        <main className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
            <section className="w-full max-w-lg rounded-xl bg-card p-8 text-center ring-1 ring-border">
                <Link href="/" className="mx-auto block w-fit" aria-label="B.ai home">
                    <Image src="/logo_B_ai_bg_removed.png" alt="" width={51} height={48} priority />
                </Link>
                <Badge variant="outline" className="mt-6 border-primary/30 bg-primary/10 text-primary">Demo mode</Badge>
                <h1 className="mt-4 text-3xl font-semibold tracking-tight">Read-only demo</h1>
                <p className="mx-auto mt-3 max-w-[46ch] text-muted-foreground">{message}</p>
                <Link href="/dashboard" className={buttonVariants({ className: 'mt-8 min-h-11 px-5' })}>
                    Open market dashboard
                </Link>
            </section>
        </main>
    );
}
