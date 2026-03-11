import { useState } from 'react';
import { useConversation } from '@elevenlabs/react';

import { fetchClient } from '../lib/api';

export function useVoice() {
    const [isRecording, setIsRecording] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const rawAgentId = (import.meta.env.VITE_ELEVENLABS_AGENT_ID as string | undefined) || '';
    const normalizedAgentId = rawAgentId.trim();
    const agentId = normalizedAgentId && normalizedAgentId !== 'undefined' && normalizedAgentId !== 'null'
        ? normalizedAgentId
        : undefined;
    const isAvailable = Boolean(agentId);

    const isDebug = import.meta.env.VITE_DEBUG_VOICE === '1';

    const conversation = useConversation({
        onConnect: () => setIsRecording(true),
        onDisconnect: () => {
            setIsRecording(false);
        },
        onError: (err: Error | string) => {
            if (isDebug) {
                console.log('[Voice] error', err);
            }
            if (typeof err === 'string') setError(err);
            else if (err instanceof Error) setError(err.message);
            setIsRecording(false);
        },
        clientTools: {
            finalize_and_submit_brief: async (parameters: { brief: string }) => {
                if (isDebug) {
                    console.log('[Voice] client tool fired: finalize_and_submit_brief', parameters);
                }
                if (parameters.brief) {
                    window.dispatchEvent(new CustomEvent('gepetto-voice-brief', { detail: parameters.brief }));
                    await stopRecording();
                }
                return "Successfully submitted brief to UI.";
            }
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
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Microphone not supported on this browser');
            }
            await navigator.mediaDevices.getUserMedia({ audio: true });

            const signed = await fetchClient(`/api/voice/signed-url?agent_id=${encodeURIComponent(agentId)}`);
            if (isDebug) {
                console.log('[Voice] signed url', signed?.signed_url ? signed.signed_url : signed);
            }
            if (typeof conversation.startSession === 'function') {
                await conversation.startSession({ signedUrl: signed.signed_url });
                if (typeof conversation.setVolume === 'function') {
                    conversation.setVolume({ volume: 1 });
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
    };

    return {
        isRecording,
        transcript: '', // Maintained for interface compatibility, but empty
        isAvailable,
        status: conversation.status,
        isSpeaking: conversation.isSpeaking,
        error,
        startRecording,
        stopRecording
    };
}
