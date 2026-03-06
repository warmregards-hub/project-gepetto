import { create } from 'zustand';

interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: string;
}

interface AgentState {
    messages: Message[];
    isProcessing: boolean;
    addMessage: (message: Message) => void;
    setMessages: (messages: Message[]) => void;
    setProcessing: (status: boolean) => void;
    clearMessages: () => void;
}

export const useAgentStore = create<AgentState>((set) => ({
    messages: [],
    isProcessing: false,
    addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
    setMessages: (messages) => set({ messages }),
    setProcessing: (status) => set({ isProcessing: status }),
    clearMessages: () => set({ messages: [] }),
}));
