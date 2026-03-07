import { useState } from 'react';
import { useAgentStore } from '../stores/agentStore';
import { useProjectStore } from '../stores/projectStore';
import { useSessionStore } from '../stores/sessionStore';
import { fetchClient } from '../lib/api';

export function useAgent() {
    const { messages, addMessage, setProcessing } = useAgentStore();
    const { activeProject } = useProjectStore();
    const { activeSessionId, setActiveSessionId, setPendingSession, loadSessions } = useSessionStore();
    const [error, setError] = useState<string | null>(null);

    const makeId = () => {
        if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
            return crypto.randomUUID();
        }
        if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
            const bytes = new Uint8Array(16);
            crypto.getRandomValues(bytes);
            return Array.from(bytes).map((b) => b.toString(16).padStart(2, '0')).join('');
        }
        return `msg_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    };

    const sendMessage = async (content: string) => {
        if (!activeProject) {
            setError('No active project selected.');
            return;
        }

        try {
            setProcessing(true);
            setError(null);

            const userMsg = {
                id: makeId(),
                role: 'user' as const,
                content,
                timestamp: new Date().toISOString()
            };
            addMessage(userMsg);

            // Build history: all messages so far, excluding the one we just added
            // (the backend will append it as the new user turn)
            const history = messages.map(m => ({ role: m.role, content: m.content }));

            const response = await fetchClient('/api/agent/chat', {
                method: 'POST',
                body: JSON.stringify({
                    message: content,
                    project_id: activeProject.id,
                    conversation_history: history,
                    session_id: activeSessionId || undefined
                })
            });

            if (response.session_id && response.session_id !== activeSessionId) {
                setActiveSessionId(response.session_id);
                setPendingSession(false);
                loadSessions(activeProject.id);
            }

            addMessage({
                id: makeId(),
                role: 'assistant',
                content: response.content,
                timestamp: new Date().toISOString()
            });

        } catch (err: any) {
            setError(err.message || 'Failed to send message');
        } finally {
            setProcessing(false);
        }
    };

    return { sendMessage, error };
}
