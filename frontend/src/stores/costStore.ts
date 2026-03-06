import { create } from 'zustand';
import { fetchClient } from '../lib/api';

interface CostState {
    sessionTotal: number;
    monthlyTotal: number;
    projectTotal: number;
    incrementSession: (amount: number) => void;
    setTotals: (session: number, monthly: number, project: number) => void;
    fetchTotals: (projectId?: string | null) => Promise<void>;
}

export const useCostStore = create<CostState>((set) => ({
    sessionTotal: 0,
    monthlyTotal: 0,
    projectTotal: 0,
    incrementSession: (amount) => set((state) => ({ sessionTotal: state.sessionTotal + amount })),
    setTotals: (session, monthly, project) => set({ sessionTotal: session, monthlyTotal: monthly, projectTotal: project }),
    fetchTotals: async (projectId) => {
        const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
        const data = await fetchClient(`/api/learning/costs/totals${query}`);
        set({
            sessionTotal: data.session_total ?? 0,
            monthlyTotal: data.monthly_total ?? 0,
            projectTotal: data.project_total ?? 0,
        });
    },
}));
