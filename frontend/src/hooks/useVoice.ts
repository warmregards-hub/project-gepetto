import { useCallback, useRef, useState } from 'react';
import { useConversation } from '@11labs/react';

import { useAgentStore } from '../stores/agentStore';
import { useProjectStore } from '../stores/projectStore';
import { useSessionStore } from '../stores/sessionStore';
import { fetchClient } from '../lib/api';

export function useVoice() {
    const [isRecording, setIsRecording] = useState(false);
    const [transcript, setTranscript] = useState('');
    const lastTranscriptRef = useRef('');
    const sendingRef = useRef(false);

    const { addMessage, setProcessing } = useAgentStore();
    const { activeProject } = useProjectStore();
    const { activeSessionId, setActiveSessionId, setPendingSession, loadSessions } = useSessionStore();
    const formattingRef = useRef(false);

    const rawAgentId = (import.meta.env.VITE_ELEVENLABS_AGENT_ID as string | undefined) || '';
    const normalizedAgentId = rawAgentId.trim();
    const agentId = normalizedAgentId && normalizedAgentId !== 'undefined' && normalizedAgentId !== 'null'
        ? normalizedAgentId
        : undefined;
    const isAvailable = Boolean(agentId);

    const sendTranscript = useCallback(async (text: string) => {
        if (!text.trim() || !activeProject) return;
        if (sendingRef.current) return;
        sendingRef.current = true;
        setProcessing(true);
        const messageId = crypto.randomUUID();
        addMessage({ id: messageId, role: 'user', content: text, timestamp: new Date().toISOString() });

        try {
            const response = await fetchClient('/api/agent/chat', {
                method: 'POST',
                body: JSON.stringify({
                    message: text,
                    project_id: activeProject.id,
                    session_id: activeSessionId || undefined,
                })
            });

            addMessage({
                id: crypto.randomUUID(),
                role: 'assistant',
                content: response.content,
                timestamp: new Date().toISOString()
            });

            if (response.session_id && response.session_id !== activeSessionId) {
                setActiveSessionId(response.session_id);
                setPendingSession(false);
                loadSessions(activeProject.id);
            }
        } finally {
            sendingRef.current = false;
            setProcessing(false);
        }
    }, [activeProject, activeSessionId, addMessage, loadSessions, setActiveSessionId, setPendingSession, setProcessing]);

    const isDebug = import.meta.env.VITE_DEBUG_VOICE === '1';

    const shouldTriggerBrief = (text: string) => {
        return /\b(generate|start generating|render|make|create)\b/i.test(text);
    };

    const formatBrief = useCallback(async (text: string) => {
        if (!text.trim() || !activeProject) return null;
        if (formattingRef.current) return null;
        formattingRef.current = true;
        try {
            const response = await fetchClient('/api/voice/format-brief', {
                method: 'POST',
                body: JSON.stringify({
                    transcript: text,
                    project_id: activeProject.id,
                    session_id: activeSessionId || undefined,
                })
            });
            return response.brief as string;
        } finally {
            formattingRef.current = false;
        }
    }, [activeProject, activeSessionId]);

    const conversation = useConversation({
        onConnect: () => setIsRecording(true),
        onDisconnect: () => {
            setIsRecording(false);
        },
        onMessage: (message: unknown) => {
            if (!message) return;
            if (isDebug) {
                console.log('[Voice] message', message);
            }
            const payload = message as { source?: string; role?: string; message?: string; text?: string };
            const source = payload.source || payload.role;
            const text = payload.message || payload.text || '';
            if (!text || source !== 'user') return;
            setTranscript((prev) => (prev ? `${prev} ${text}` : text));
            lastTranscriptRef.current = lastTranscriptRef.current
                ? `${lastTranscriptRef.current} ${text}`
                : text;
            if (shouldTriggerBrief(text)) {
                const toSend = lastTranscriptRef.current;
                lastTranscriptRef.current = '';
                setTranscript('');
                void formatBrief(toSend).then((brief) => {
                    if (brief) {
                        if (isDebug) {
                            console.log('[Voice] formatted brief ready');
                        }
                        window.dispatchEvent(new CustomEvent('gepetto-voice-brief', { detail: brief }));
                    }
                });
            }
        },
        onError: () => {
            if (isDebug) {
                console.log('[Voice] error');
            }
            setIsRecording(false);
        }
    });

    const startRecording = async () => {
        if (!agentId) return;
        if (isDebug) {
            console.log('[Voice] agent id', agentId);
        }
        setIsRecording(true);
        setTranscript('');
        lastTranscriptRef.current = '';
        await navigator.mediaDevices.getUserMedia({ audio: true });
        const signed = await fetchClient(`/api/voice/signed-url?agent_id=${encodeURIComponent(agentId)}`);
        if (isDebug) {
            console.log('[Voice] signed url', signed?.signed_url ? signed.signed_url : signed);
        }
        if (typeof conversation.startSession === 'function') {
            await conversation.startSession({ signedUrl: signed.signed_url, agentId });
        }
    };

    const stopRecording = async () => {
        setIsRecording(false);
        if (typeof conversation.endSession === 'function') {
            await conversation.endSession();
        }
        lastTranscriptRef.current = '';
        setTranscript('');
    };

    return {
        isRecording,
        transcript,
        isAvailable,
        startRecording,
        stopRecording
    };
}
