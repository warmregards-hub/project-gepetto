import { create } from 'zustand';
import { fetchClient } from '../lib/api';

interface CostState {
    sessionTotal: number;
    dailyTotal: number;
    monthlyTotal: number;
    projectTotal: number;
    incrementSession: (amount: number) => void;
    setTotals: (session: number, daily: number, monthly: number, project: number) => void;
    fetchTotals: (projectId?: string | null, sessionId?: string | null) => Promise<void>;
}

export const useCostStore = create<CostState>((set) => ({
    sessionTotal: 0,
    dailyTotal: 0,
    monthlyTotal: 0,
    projectTotal: 0,
    incrementSession: (amount) => set((state) => ({ sessionTotal: state.sessionTotal + amount })),
    setTotals: (session, daily, monthly, project) => set({ sessionTotal: session, dailyTotal: daily, monthlyTotal: monthly, projectTotal: project }),
    fetchTotals: async (projectId, sessionId) => {
        const params = new URLSearchParams();
        if (projectId) params.set('project_id', projectId);
        if (sessionId) params.set('session_id', sessionId);
        const query = params.toString() ? `?${params.toString()}` : '';
        const data = await fetchClient(`/api/learning/costs/totals${query}`);
        set({
            sessionTotal: data.session_total ?? 0,
            dailyTotal: data.daily_total ?? 0,
            monthlyTotal: data.monthly_total ?? 0,
            projectTotal: data.project_total ?? 0,
        });
    },
}));
