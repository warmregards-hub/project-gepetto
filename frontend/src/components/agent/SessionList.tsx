import { useEffect } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useSessionStore } from '../../stores/sessionStore';

export function SessionList() {
    const { activeProject } = useProjectStore();
    const { sessions, activeSessionId, pendingSession, isLoading, loadSessions, startNewSession, selectSession } = useSessionStore();

    useEffect(() => {
        if (!activeProject) return;
        loadSessions(activeProject.id);
    }, [activeProject?.id, loadSessions]);

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <span className="uppercase tracking-widest text-[12px] font-black text-zinc-500">Sessions</span>
                <button
                    type="button"
                    onClick={startNewSession}
                    className="px-3 py-1.5 rounded-lg border border-zinc-200 text-[11px] font-black uppercase tracking-widest text-zinc-700 hover:bg-zinc-50"
                >
                    New Session
                </button>
            </div>

            <div className="max-h-[220px] overflow-y-auto pr-2 space-y-2">
                {pendingSession && (
                    <div className="px-4 py-3 rounded-2xl border border-accent/40 bg-accent/5 text-zinc-800 text-sm font-black">
                        New Session
                    </div>
                )}

                {sessions.map((session) => (
                    <button
                        key={session.id}
                        type="button"
                        onClick={() => selectSession(session.id)}
                        className={`w-full text-left px-4 py-3 rounded-2xl border transition-all ${activeSessionId === session.id
                            ? 'border-accent bg-accent/10 text-zinc-900'
                            : 'border-zinc-100 hover:border-zinc-200 bg-white text-zinc-600'
                            }`}
                    >
                        <div className="text-sm font-black tracking-tight">{session.name}</div>
                        <div className="text-[11px] uppercase tracking-widest text-zinc-400 mt-1">
                            {new Date(session.last_activity).toLocaleDateString()}
                        </div>
                    </button>
                ))}

                {!isLoading && sessions.length === 0 && !pendingSession && (
                    <div className="px-4 py-3 rounded-2xl border border-zinc-100 text-xs text-zinc-400 font-black uppercase tracking-widest">
                        No sessions yet
                    </div>
                )}
            </div>
        </div>
    );
}
