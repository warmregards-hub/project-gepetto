import { useEffect } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { CostTracker } from './CostTracker';
import { useCostStore } from '../../stores/costStore';
import { useProjectStore } from '../../stores/projectStore';
import { ChevronLeft } from 'lucide-react';
import { Meteors } from './Meteors';
import { SessionList } from '../agent/SessionList';
import { useSessionStore } from '../../stores/sessionStore';

export function Layout() {
    const location = useLocation();
    const { fetchTotals } = useCostStore();
    const { activeProject } = useProjectStore();
    const { activeSessionId } = useSessionStore();
    const { isSidebarOpen, setSidebarOpen } = useLayoutStore();

    useEffect(() => {
        const projectId = activeProject?.id ?? null;
        const sessionId = activeSessionId ?? null;
        fetchTotals(projectId, sessionId);
        const interval = setInterval(() => fetchTotals(projectId, sessionId), 10000);
        return () => clearInterval(interval);
    }, [activeProject, activeSessionId, fetchTotals]);

    return (
        <div className="flex h-screen w-full bg-[#FAF9F6] text-zinc-900 overflow-hidden font-serif">
            {/* Meteor Background Layer */}
            <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
                <Meteors number={40} />
            </div>

            {/* Mobile Backdrop */}
            <div
                onClick={() => setSidebarOpen(false)}
                className={`lg:hidden fixed inset-0 bg-black/5 backdrop-blur-[2px] z-50 transition-opacity duration-500 ${isSidebarOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
            />

            {/* Sidebar Navigation */}
            <aside className={`
                w-80 border-r border-zinc-100 bg-white flex flex-col 
                fixed lg:relative inset-y-0 left-0 z-[60] 
                transition-transform duration-500 ease-in-out lg:translate-x-0
                ${isSidebarOpen ? 'translate-x-0 shadow-2xl lg:shadow-none' : '-translate-x-full lg:translate-x-0'}
            `}>
                <div className="p-6 border-b border-zinc-50 flex items-center justify-between">
                    <div>
                        <h1 className="text-[2.7rem] font-bold tracking-tight text-zinc-950">Warm Regards</h1>
                        <p className="text-[1rem] text-zinc-500 -mt-1 font-mono font-bold uppercase tracking-widest ml-[0.5rem]">PROJECT GEPETTO</p>
                    </div>
                    <button
                        onClick={() => setSidebarOpen(false)}
                        className="lg:hidden p-2 text-zinc-400 hover:text-zinc-950 transition-colors"
                    >
                        <ChevronLeft size={32} strokeWidth={2} />
                    </button>
                </div>

                <div className="flex-1 overflow-hidden flex flex-col">
                    <nav className="p-6 space-y-2">
                        <Link
                            to="/"
                            onClick={() => setSidebarOpen(false)}
                            className={`block px-6 py-4 rounded-2xl transition-all font-black text-xl ${location.pathname === '/' ? 'bg-accent text-white shadow-lg shadow-accent/20 translate-x-1' : 'hover:bg-zinc-50 text-zinc-400'}`}
                        >
                            Agent Mode
                        </Link>
                        <Link
                            to="/studio"
                            onClick={() => setSidebarOpen(false)}
                            className={`block px-6 py-4 rounded-2xl transition-all font-black text-xl ${location.pathname === '/studio' ? 'bg-accent text-white shadow-lg shadow-accent/20 translate-x-1' : 'hover:bg-zinc-50 text-zinc-400'}`}
                        >
                            Studio Mode
                        </Link>
                    </nav>

                    <div className="px-6 pb-6">
                        <SessionList />
                    </div>
                </div>

                <div className="p-8 border-t border-zinc-100 bg-white">
                    <CostTracker />
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 relative flex flex-col overflow-hidden bg-transparent">
                <div className="relative z-10 flex-1 flex flex-col overflow-hidden">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}

