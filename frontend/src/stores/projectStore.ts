import { create } from 'zustand';
import { Project } from '../types';
import { fetchClient } from '../lib/api';

interface ProjectState {
    activeProject: Project | null;
    projects: Project[];
    savedAssets: string[];
    rejectedAssets: string[];
    setActiveProject: (project: Project) => void;
    setProjects: (projects: Project[]) => void;
    saveAsset: (url: string, projectId: string) => Promise<void>;
    rejectAsset: (url: string, projectId: string) => Promise<void>;
}

export const useProjectStore = create<ProjectState>((set) => ({
    activeProject: null,
    projects: [],
    savedAssets: [],
    rejectedAssets: [],
    setActiveProject: (project) => set({ activeProject: project }),
    setProjects: (projects) => set({ projects }),
    saveAsset: async (url, projectId) => {
        try {
            await fetchClient('/api/learning/log-qc', {
                method: 'POST',
                body: JSON.stringify({ project_id: projectId, asset_url: url, decision: 'keep' })
            });
            set((state) => ({
                savedAssets: state.savedAssets.includes(url) ? state.savedAssets : [...state.savedAssets, url],
                rejectedAssets: state.rejectedAssets.filter(a => a !== url)
            }));
        } catch (err) {
            console.error('Failed to log keep decision:', err);
        }
    },
    rejectAsset: async (url, projectId) => {
        try {
            await fetchClient('/api/learning/log-qc', {
                method: 'POST',
                body: JSON.stringify({ project_id: projectId, asset_url: url, decision: 'reject' })
            });
            set((state) => ({
                rejectedAssets: state.rejectedAssets.includes(url) ? state.rejectedAssets : [...state.rejectedAssets, url],
                savedAssets: state.savedAssets.filter(a => a !== url)
            }));
        } catch (err) {
            console.error('Failed to log reject decision:', err);
        }
    },
}));
