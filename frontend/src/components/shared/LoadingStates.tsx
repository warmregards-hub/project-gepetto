import { Loader2 } from 'lucide-react';

export function LoadingSpinner({ message = "Loading..." }: { message?: string }) {
    return (
        <div className="flex flex-col items-center justify-center p-12 space-y-6 text-zinc-400">
            <Loader2 className="w-12 h-12 animate-spin text-accent" />
            <p className="text-xl font-black tracking-widest uppercase">{message}</p>
        </div>
    );
}

export function SkeletonMessage() {
    return (
        <div className="relative flex animate-pulse space-x-6 p-12 mb-10 rounded-[40px] bg-white border border-zinc-100 shadow-sm max-w-5xl mx-auto">
            <img
                src="/load.gif"
                alt="Loading"
                className="absolute top-6 left-6 w-[36px] h-[36px] mix-blend-multiply"
            />
            <div className="rounded-full bg-zinc-50 h-16 w-16 border border-zinc-100"></div>
            <div className="flex-1 space-y-6 py-2">
                <div className="h-4 bg-zinc-50 rounded-full w-1/4"></div>
                <div className="h-4 bg-zinc-50 rounded-full w-3/4"></div>
                <div className="h-4 bg-zinc-50 rounded-full w-1/2"></div>
            </div>
        </div>
    );
}
