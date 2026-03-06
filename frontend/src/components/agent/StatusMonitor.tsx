import { useWebSocket } from '../../hooks/useWebSocket';
import { API_BASE_URL } from '../../lib/constants';
import { useAgentStore } from '../../stores/agentStore';

// We strip http/https and replace with ws/wss
const wsUrl = `${API_BASE_URL.replace(/^http/, 'ws')}/api/agent/ws`;

export function StatusMonitor() {
    const { status, lastMessage } = useWebSocket(wsUrl);
    const { isProcessing } = useAgentStore();
    const isBusy = isProcessing || (lastMessage?.type === 'progress' && lastMessage?.data?.progress < 100);

    return (
        <div className="bg-white border border-zinc-100 rounded-xl p-4 flex items-center justify-between shadow-sm">
            <div className="flex items-center space-x-4">
                <div className={`w-3 h-3 rounded-full ${status === 'connected'
                    ? `bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]`
                    : status === 'connecting'
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    } ${isBusy ? 'animate-[pulseFull_1.2s_ease-in-out_infinite]' : ''}`} />
                <span className="text-lg font-black text-zinc-900 uppercase tracking-tight">
                    {status === 'connected' ? 'Agent Live' : status}
                </span>
            </div>

        </div>
    );
}
