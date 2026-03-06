import { create } from 'zustand';

interface LayoutState {
    isSidebarOpen: boolean;
    setSidebarOpen: (open: boolean) => void;
}

export const useLayoutStore = create<LayoutState>((set) => ({
    isSidebarOpen: false,
    setSidebarOpen: (open) => set({ isSidebarOpen: open })
}));
