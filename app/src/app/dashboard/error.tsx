
'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { TriangleAlert } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button, buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';

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
        <div className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
            <Alert variant="destructive" className="max-w-md gap-4 p-8 shadow-2xl">
                <TriangleAlert />
                <AlertTitle className="text-xl">Error: {error.name}</AlertTitle>
                <AlertDescription className="flex flex-col gap-4">
                    <p className="max-h-60 overflow-auto font-mono">{error.message}</p>
                    {error.digest && <p className="font-mono text-xs">Digest: {error.digest}</p>}
                    <p className="text-xs">Check Railway logs for the full stack trace.</p>
                    <div className="flex justify-center gap-4 pt-2">
                        <Button onClick={() => reset()}>Try again</Button>
                        <Link href="/" className={cn(buttonVariants({ variant: 'secondary' }))}>Go Home</Link>
                    </div>
                </AlertDescription>
            </Alert>
        </div>
    );
}
