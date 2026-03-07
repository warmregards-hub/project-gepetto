import { useCallback, useRef, useState } from 'react';
import { useConversation } from '@11labs/react';

import { useProjectStore } from '../stores/projectStore';
import { useSessionStore } from '../stores/sessionStore';
import { fetchClient } from '../lib/api';

export function useVoice() {
    const [isRecording, setIsRecording] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [error, setError] = useState<string | null>(null);
    const lastTranscriptRef = useRef('');
    const { activeProject } = useProjectStore();
    const { activeSessionId } = useSessionStore();
    const formattingRef = useRef(false);

    const rawAgentId = (import.meta.env.VITE_ELEVENLABS_AGENT_ID as string | undefined) || '';
    const normalizedAgentId = rawAgentId.trim();
    const agentId = normalizedAgentId && normalizedAgentId !== 'undefined' && normalizedAgentId !== 'null'
        ? normalizedAgentId
        : undefined;
    const isAvailable = Boolean(agentId);

    const isDebug = import.meta.env.VITE_DEBUG_VOICE === '1';

    const shouldTriggerBrief = (text: string) => {
        return /\b(generate|start generating|render|make|create)\b/i.test(text);
    };

    const normalizeTranscript = (text: string) => {
        return text
            .replace(/\bz\s*image\b/gi, 'z-image')
            .replace(/\bgpt\s*image\s*1\b/gi, 'gpt-image-1')
            .replace(/\bveo\s*3\.1\s*fast\b/gi, 'veo-3.1-fast')
            .replace(/\bveo\s*3\.1\b/gi, 'veo-3.1')
            .replace(/\brunway\s*aleph\b/gi, 'runway-aleph')
            .replace(/\bnano\s*banana\s*pro\b/gi, 'nano-banana-pro');
    };

    const formatBrief = useCallback(async (text: string) => {
        if (!text.trim() || !activeProject) return null;
        if (formattingRef.current) return null;
        const normalized = normalizeTranscript(text);
        formattingRef.current = true;
        try {
            const response = await fetchClient('/api/voice/format-brief', {
                method: 'POST',
                body: JSON.stringify({
                    transcript: normalized,
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
        try {
            setError(null);
            setIsRecording(true);
            setTranscript('');
            lastTranscriptRef.current = '';
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Microphone not supported on this browser');
            }
            await navigator.mediaDevices.getUserMedia({ audio: true });
            const signed = await fetchClient(`/api/voice/signed-url?agent_id=${encodeURIComponent(agentId)}`);
            if (isDebug) {
                console.log('[Voice] signed url', signed?.signed_url ? signed.signed_url : signed);
            }
            if (typeof conversation.startSession === 'function') {
                await conversation.startSession({ signedUrl: signed.signed_url, agentId });
                if (typeof conversation.setVolume === 'function') {
                    await conversation.setVolume({ volume: 1 });
                }
            }
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Voice connection failed';
            setError(message);
            setIsRecording(false);
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
        status: conversation.status,
        isSpeaking: conversation.isSpeaking,
        error,
        startRecording,
        stopRecording
    };
}
