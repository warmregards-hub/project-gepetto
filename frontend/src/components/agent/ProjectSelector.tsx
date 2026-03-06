import { useProjectStore } from '../../stores/projectStore';
import { ChevronDown } from 'lucide-react';

export function ProjectSelector() {
    const { activeProject, projects, setActiveProject } = useProjectStore();

    return (
        <div className="relative inline-block w-full max-w-full md:max-w-xs xl:max-w-md">
            <select
                className="w-full appearance-none bg-white border border-zinc-200 text-zinc-950 py-4 pl-6 pr-12 rounded-2xl focus:outline-none focus:ring-4 focus:ring-accent/10 focus:border-accent shadow-sm font-bold text-xl cursor-not-allowed md:cursor-pointer transition-all hover:bg-zinc-50/50"
                value={activeProject?.id || ''}
                onChange={(e) => {
                    const selected = projects.find(p => p.id === e.target.value);
                    if (selected) setActiveProject(selected);
                }}
            >
                <option value="" disabled>Select Project...</option>
                {projects.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-zinc-400">
                <ChevronDown className="h-6 w-6" />
            </div>
        </div>
    );
}
