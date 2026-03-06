import { useVoice } from '../../hooks/useVoice';
import { Mic, Square } from 'lucide-react';

export function VoiceInput() {
    const { isRecording, startRecording, stopRecording } = useVoice();

    return (
        <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            className={`h-[72px] w-[72px] rounded-[20px] transition-all shrink-0 shadow-lg flex items-center justify-center border-2 ${isRecording
                ? 'bg-red-500/20 text-red-600 hover:bg-red-500/30 border-red-500/40 animate-pulse scale-105'
                : 'bg-rose-500 text-white hover:bg-rose-600 border-rose-500'
                }`}
            title={isRecording ? "Stop Recording" : "Start Voice Input"}
        >
            {isRecording ? <Square className="w-6 h-6 fill-current" /> : <Mic className="w-6 h-6" />}
        </button>
    );
}
