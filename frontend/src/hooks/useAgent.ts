import { useState } from 'react';
import { useAgentStore } from '../stores/agentStore';
import { useProjectStore } from '../stores/projectStore';
import { fetchClient } from '../lib/api';

export function useAgent() {
    const { messages, addMessage, setProcessing } = useAgentStore();
    const { activeProject } = useProjectStore();
    const [error, setError] = useState<string | null>(null);

    const sendMessage = async (content: string) => {
        if (!activeProject) {
            setError('No active project selected.');
            return;
        }

        try {
            setProcessing(true);
            setError(null);

            const userMsg = {
                id: crypto.randomUUID(),
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
                    conversation_history: history
                })
            });

            addMessage({
                id: crypto.randomUUID(),
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
