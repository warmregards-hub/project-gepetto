import { useEffect, useState } from 'react';
import { ConversationView } from '../components/agent/ConversationView';
import { ScriptPaste } from '../components/agent/ScriptPaste';
import { VoiceInput } from '../components/agent/VoiceInput';
import { ProjectSelector } from '../components/agent/ProjectSelector';
import { StatusMonitor } from '../components/agent/StatusMonitor';
import { useAgent } from '../hooks/useAgent';
import { useVoice } from '../hooks/useVoice';
import { useProjectStore } from '../stores/projectStore';
import { useLayoutStore } from '../stores/layoutStore';
import { useSessionStore } from '../stores/sessionStore';
import { Menu } from 'lucide-react';

export function AgentPage() {
    const { sendMessage, error } = useAgent();
    const { isRecording, isAvailable, status, isSpeaking, error: voiceError, startRecording, stopRecording } = useVoice();
    const { activeProject, setProjects, setActiveProject } = useProjectStore();
    const { startNewSession } = useSessionStore();
    const { setSidebarOpen } = useLayoutStore();
    const [draftText, setDraftText] = useState('');

    // Mock initial data load for phase 1 testing
    useEffect(() => {
        const mockProjects = [
            { id: 'drew-5trips', name: 'Drew (5TRIPS / BaySmokes)' },
            { id: 'betway-f1', name: 'Betway F1' }
        ];
        setProjects(mockProjects);
        if (!activeProject) {
            setActiveProject(mockProjects[0]);
        }
    }, [setProjects, activeProject]);

    useEffect(() => {
        if (!activeProject) return;
        startNewSession();
    }, [activeProject?.id, startNewSession]);

    useEffect(() => {
        const handler = (event: Event) => {
            const detail = (event as CustomEvent<string>).detail;
            if (detail) {
                setDraftText(detail);
            }
        };
        window.addEventListener('gepetto-voice-brief', handler as EventListener);
        return () => window.removeEventListener('gepetto-voice-brief', handler as EventListener);
    }, []);

    const handleSend = (msg: string) => {
        sendMessage(msg);
    };

    return (
        <div className="flex flex-col h-full bg-transparent">
            <header className="flex-none p-4 md:p-6 border-b border-zinc-100 flex items-center bg-white/50 backdrop-blur-md min-h-[80px] md:min-h-[96px] gap-3 md:gap-6">
                {/* Mobile Menu Toggle */}
                <button
                    onClick={() => setSidebarOpen(true)}
                    className="lg:hidden p-3 bg-zinc-50 border border-zinc-100 rounded-xl text-zinc-950 hover:bg-zinc-100 transition-all shrink-0"
                >
                    <Menu size={24} strokeWidth={2.5} />
                </button>

                {/* Project Selector - Weighted half-width on mobile */}
                <div className="flex-1 lg:flex-none">
                    <ProjectSelector />
                </div>

                {/* Status Monitor - Pushed to right */}
                <div className="shrink-0 ml-auto bg-zinc-50/50 p-2 md:p-0 rounded-xl border border-zinc-100 md:border-none">
                    <StatusMonitor />
                </div>
            </header>

            <ConversationView />

            {error && (
                <div className="mx-4 mb-4 p-4 bg-red-500/10 border border-red-500/50 rounded-xl text-red-400 text-sm">
                    {error}
                </div>
            )}

            <footer className="flex-none p-4 md:p-8 border-t border-zinc-100 bg-zinc-50/50 backdrop-blur-md min-h-[100px] md:min-h-[120px]">
                <div className="max-w-5xl mx-auto flex flex-col gap-2">
                    {(isRecording || voiceError) && (
                        <div className="text-xs font-black uppercase tracking-widest text-zinc-400">
                            Voice {status === 'connected' ? 'live' : status}
                            {isSpeaking ? ' · AI speaking' : ''}
                            {voiceError ? ` · ${voiceError}` : ''}
                        </div>
                    )}
                    <div className="flex items-end gap-3 md:gap-6">
                    <VoiceInput
                        isRecording={isRecording}
                        onStart={startRecording}
                        onStop={stopRecording}
                        disabled={!activeProject || !isAvailable}
                    />
                    <div className="flex-1">
                            <ScriptPaste
                                onSend={handleSend}
                                disabled={!activeProject}
                                value={draftText}
                                onChange={setDraftText}
                            />
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
}

