import { useVoice } from '../../hooks/useVoice';
import { Mic, Square } from 'lucide-react';

export function VoiceInput() {
    const { isRecording, startRecording, stopRecording } = useVoice();

    return (
        <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            className={`p-4 rounded-[20px] transition-all shrink-0 shadow-lg flex items-center justify-center border-2 ${isRecording
                ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20 border-red-500/30 animate-pulse scale-105'
                : 'bg-white text-zinc-500 hover:bg-zinc-50 hover:text-zinc-950 border-zinc-100 hover:border-zinc-300'
                }`}
            title={isRecording ? "Stop Recording" : "Start Voice Input"}
        >
            {isRecording ? <Square className="w-6 h-6 fill-current" /> : <Mic className="w-6 h-6" />}
        </button>
    );
}
