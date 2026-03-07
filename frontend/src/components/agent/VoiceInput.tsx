import { Mic, Square } from 'lucide-react';

interface VoiceInputProps {
    isRecording: boolean;
    onStart: () => void;
    onStop: () => void;
    disabled?: boolean;
}

export function VoiceInput({ isRecording, onStart, onStop, disabled }: VoiceInputProps) {
    const isDisabled = Boolean(disabled);

    return (
        <button
            type="button"
            onClick={isRecording ? onStop : onStart}
            disabled={isDisabled}
            className={`h-[72px] w-[72px] rounded-[20px] transition-all shrink-0 shadow-lg flex items-center justify-center border-2 ${isDisabled
                ? 'bg-zinc-200 text-zinc-400 border-zinc-200 cursor-not-allowed'
                : isRecording
                    ? 'bg-red-500/20 text-red-600 hover:bg-red-500/30 border-red-500/40 animate-pulse scale-105'
                    : 'bg-rose-500 text-white hover:bg-rose-600 border-rose-500'
                }`}
            title={isDisabled ? "Voice not configured" : (isRecording ? "Stop Recording" : "Start Voice Input")}
        >
            {isRecording ? <Square className="w-6 h-6 fill-current" /> : <Mic className="w-6 h-6" />}
        </button>
    );
}
