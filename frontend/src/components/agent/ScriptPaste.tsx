import { useState } from 'react';
import { Send, Upload } from 'lucide-react';

interface Props {
    onSend: (msg: string) => void;
    disabled?: boolean;
    value?: string;
    onChange?: (value: string) => void;
}

export function ScriptPaste({ onSend, disabled, value, onChange }: Props) {
    const [internalText, setInternalText] = useState('');
    const isControlled = typeof value !== 'undefined';
    const text = isControlled ? value : internalText;
    const setText = (next: string) => {
        if (isControlled && onChange) {
            onChange(next);
            return;
        }
        setInternalText(next);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (text.trim() && !disabled) {
            onSend(text.trim());
            setText('');
        }
    };

    return (
        <form onSubmit={handleSubmit} className="relative flex items-center gap-2 bg-white border border-zinc-200 rounded-[24px] p-2 shadow-md focus-within:ring-4 focus-within:ring-accent/5 focus-within:border-accent transition-all group overflow-hidden min-h-[72px]">
            <button
                type="button"
                className="p-3 text-zinc-400 hover:text-zinc-600 transition-colors shrink-0 bg-zinc-50 rounded-xl"
                title="Upload script file"
            >
                <Upload className="w-5 h-5" />
            </button>

            <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={disabled}
                placeholder="Type a brief..."
                className="flex-1 max-h-72 min-h-[40px] bg-transparent border-none resize-none py-2 px-2 text-zinc-950 placeholder:text-zinc-400 focus:outline-none scrollbar-thin scrollbar-thumb-zinc-200 font-bold text-xl leading-snug"
                onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSubmit(e);
                    }
                }}
                rows={1}
            />

            <button
                type="submit"
                disabled={!text.trim() || disabled}
                className="p-4 bg-accent text-white rounded-xl hover:bg-accent-hover transition-all shadow-lg hover:shadow-accent/30 disabled:opacity-30 disabled:grayscale disabled:cursor-not-allowed shrink-0"
            >
                <Send className="w-5 h-5" />
            </button>
        </form>
    );
}
