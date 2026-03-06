import { useCostStore } from '../../stores/costStore';

export function CostTracker() {
    const { sessionTotal, dailyTotal, monthlyTotal, projectTotal } = useCostStore();

    // Example limits from .env (hardcoded for UI display scale)
    const sessionLimit = 5.00;
    const monthlyLimit = 150.00;

    const sessionPercent = Math.min((sessionTotal / sessionLimit) * 100, 100);
    const dailyPercent = Math.min((dailyTotal / sessionLimit) * 100, 100);
    const monthPercent = Math.min((monthlyTotal / monthlyLimit) * 100, 100);

    return (
        <div className="space-y-6 font-mono">
            <div className="space-y-3">
                <div className="flex justify-between items-end text-zinc-500">
                    <span className="uppercase tracking-widest text-[14px] font-black leading-none">Session</span>
                    <span className={`text-2xl font-black leading-none ${sessionTotal > sessionLimit * 0.8 ? 'text-accent' : 'text-zinc-950'}`}>
                        ${sessionTotal.toFixed(2)}
                    </span>
                </div>
                <div className="h-2.5 bg-zinc-100 rounded-full overflow-hidden border border-zinc-200 shadow-inner">
                    <div
                        className="h-full bg-accent transition-all duration-500 shadow-[0_0_8px_rgba(232,130,90,0.4)]"
                        style={{ width: `${sessionPercent}%` }}
                    />
                </div>
            </div>

            <div className="space-y-3">
                <div className="flex justify-between items-end text-zinc-500">
                    <span className="uppercase tracking-widest text-[14px] font-black leading-none">Daily</span>
                    <span className={`text-2xl font-black leading-none ${dailyTotal > sessionLimit * 0.8 ? 'text-accent' : 'text-zinc-950'}`}>
                        ${dailyTotal.toFixed(2)}
                    </span>
                </div>
                <div className="h-2.5 bg-zinc-100 rounded-full overflow-hidden border border-zinc-200 shadow-inner">
                    <div
                        className="h-full bg-orange-400 transition-all duration-500 shadow-[0_0_8px_rgba(251,146,60,0.35)]"
                        style={{ width: `${dailyPercent}%` }}
                    />
                </div>
            </div>

            <div className="space-y-3">
                <div className="flex justify-between items-end text-zinc-500">
                    <span className="uppercase tracking-widest text-[14px] font-black leading-none">Month</span>
                    <span className={`text-2xl font-black leading-none ${monthlyTotal > monthlyLimit * 0.8 ? 'text-accent' : 'text-zinc-950'}`}>
                        ${monthlyTotal.toFixed(2)}
                    </span>
                </div>
                <div className="h-2.5 bg-zinc-100 rounded-full overflow-hidden border border-zinc-200 shadow-inner">
                    <div
                        className="h-full bg-blue-500 transition-all duration-500 shadow-[0_0_8px_rgba(59,130,246,0.4)]"
                        style={{ width: `${monthPercent}%` }}
                    />
                </div>
                <div className="flex justify-end pt-1">
                    <span className="text-[12px] font-black text-zinc-400 uppercase tracking-tighter">BUDGET ${monthlyLimit.toFixed(0)}</span>
                </div>
            </div>

            {projectTotal > 0 && (
                <div className="flex justify-between items-center mt-4 p-4 bg-zinc-50 rounded-2xl border border-zinc-100 shadow-sm">
                    <span className="uppercase tracking-widest text-[12px] font-black text-zinc-500">Project</span>
                    <span className="text-2xl font-black text-zinc-950 tracking-tighter">${projectTotal.toFixed(2)}</span>
                </div>
            )}
        </div>
    );
}
