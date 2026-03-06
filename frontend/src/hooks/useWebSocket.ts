import { useEffect, useState, useRef } from 'react';

type WebSocketStatus = 'connecting' | 'connected' | 'disconnected';

export function useWebSocket(url: string) {
    const [status, setStatus] = useState<WebSocketStatus>('disconnected');
    const [lastMessage, setLastMessage] = useState<any>(null);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        const connect = () => {
            setStatus('connecting');
            ws.current = new WebSocket(url);

            ws.current.onopen = () => setStatus('connected');
            ws.current.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    setLastMessage(data);
                } catch (e) {
                    console.error("Failed to parse websocket message", e);
                }
            };
            ws.current.onclose = () => {
                setStatus('disconnected');
                // Simple reconnect logic
                setTimeout(connect, 3000);
            };
        };

        connect();

        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, [url]);

    return { status, lastMessage };
}
