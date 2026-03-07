import { create } from 'zustand';
import { fetchClient } from '../lib/api';
import { SessionDetail, SessionSummary } from '../types';
import { useAgentStore } from './agentStore';

interface SessionState {
    sessions: SessionSummary[];
    activeSessionId: string | null;
    pendingSession: boolean;
    isLoading: boolean;
    loadSessions: (projectId: string) => Promise<void>;
    startNewSession: () => void;
    selectSession: (sessionId: string) => Promise<void>;
    setActiveSessionId: (sessionId: string | null) => void;
    setPendingSession: (pending: boolean) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
    sessions: [],
    activeSessionId: null,
    pendingSession: true,
    isLoading: false,
    loadSessions: async (projectId: string) => {
        set({ isLoading: true });
        try {
            const data = await fetchClient(`/api/sessions?project_id=${encodeURIComponent(projectId)}`);
            set({ sessions: data || [] });
        } catch {
            set({ sessions: [] });
        } finally {
            set({ isLoading: false });
        }
    },
    startNewSession: () => {
        useAgentStore.getState().clearMessages();
        set({ activeSessionId: null, pendingSession: true });
    },
    selectSession: async (sessionId: string) => {
        set({ isLoading: true });
        try {
            const data = await fetchClient(`/api/sessions/${sessionId}`) as SessionDetail;
            const messages = data.messages.map((msg) => ({
                id: msg.id,
                role: msg.role,
                content: msg.content,
                timestamp: msg.created_at,
            }));

            const assetLinks = data.assets
                .map((asset) => asset.drive_direct_url || asset.drive_url)
                .filter((link): link is string => Boolean(link));

            const hasAssetLinks = assetLinks.some((link) =>
                messages.some((message) => message.content.includes(link))
            );

            if (assetLinks.length > 0 && !hasAssetLinks) {
                const assetBody = assetLinks.map((link, idx) => `![asset_${idx}](${link})`).join('\n');
                messages.push({
                    id: `assets_${data.id}`,
                    role: 'assistant',
                    content: `Assets\n\n${assetBody}`,
                    timestamp: data.assets[data.assets.length - 1].created_at,
                });
            }

            useAgentStore.getState().setMessages(messages);
            set({ activeSessionId: data.id, pendingSession: false });
        } finally {
            set({ isLoading: false });
        }
    },
    setActiveSessionId: (sessionId) => set({ activeSessionId: sessionId }),
    setPendingSession: (pending) => set({ pendingSession: pending }),
}));
