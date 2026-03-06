import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../lib/constants';
import { Meteors } from '../components/shared/Meteors';

export function LoginPage() {
    const navigate = useNavigate();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        try {
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);

            const response = await fetch(`${API_BASE_URL}/api/auth/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData,
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Login failed');
            }

            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            navigate('/');
        } catch (err: any) {
            setError(err.message);
        }
    };

    return (
        <div className="flex h-screen items-center justify-center bg-zinc-950 relative overflow-hidden">
            {/* Background Animation */}
            <div className="absolute inset-0 pointer-events-none z-0">
                <Meteors number={60} />
            </div>

            <div className="w-full max-w-sm p-12 bg-zinc-900/50 backdrop-blur-xl border border-zinc-800 rounded-[32px] shadow-2xl relative z-10">
                <div className="mb-10 text-center">
                    <h2 className="text-4xl font-black tracking-tight text-white mb-2">Warm Regards</h2>
                    <p className="text-zinc-500 font-bold uppercase tracking-widest text-[10px]">Access Gepetto Core</p>
                </div>

                <form onSubmit={handleLogin} className="space-y-6">
                    {error && (
                        <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-2xl text-red-500 text-[14px] font-bold">
                            {error}
                        </div>
                    )}
                    <div className="space-y-2">
                        <label className="block text-[10px] font-black uppercase tracking-widest text-zinc-500 ml-1">Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full bg-zinc-950/50 border border-zinc-800 rounded-2xl p-4 text-zinc-100 focus:ring-2 focus:ring-accent focus:border-accent transition-all outline-none"
                            required
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="block text-[10px] font-black uppercase tracking-widest text-zinc-500 ml-1">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-zinc-950/50 border border-zinc-800 rounded-2xl p-4 text-zinc-100 focus:ring-2 focus:ring-accent focus:border-accent transition-all outline-none"
                            required
                        />
                    </div>
                    <button type="submit" className="w-full py-5 mt-4 bg-accent hover:bg-accent-hover text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all shadow-lg shadow-accent/20 active:scale-[0.98]">
                        Initialize Session
                    </button>
                </form>
            </div>
        </div>
    );
}

