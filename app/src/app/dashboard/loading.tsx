
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';

export default function Loading() {
    return (
        <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
            <div className="flex flex-col items-center gap-4">
                <div className="relative size-12">
                    <Skeleton className="absolute inset-0 size-12 rounded-full" />
                    <Spinner className="relative m-2 size-8 text-primary" />
                </div>
                <p className="text-muted-foreground">Loading Bitcoin Dashboard...</p>
            </div>
        </div>
    );
}
