import React, { useState, useEffect } from 'react';
import { Activity, Database, Brain, Terminal, Send, ShieldCheck, AlertCircle } from 'lucide-react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:50001'; // Use Vercel Env Var or fallback to local
const API_KEY = 'swarm-secret-key'; // Should be moved to .env in production

const App = () => {
    const [logs, setLogs] = useState([]);
    const [health, setHealth] = useState({ agents: [], status: 'unknown' });
    const [task, setTask] = useState('');
    const [isExecuting, setIsExecuting] = useState(false);

    const fetchLogs = async () => {
        try {
            const res = await axios.get(`${API_BASE}/logs`, { headers: { 'X-API-Key': API_KEY } });
            setLogs(res.data.logs.slice(-50).reverse());
        } catch (e) { console.error('Log fetch failed', e); }
    };

    const fetchHealth = async () => {
        try {
            const res = await axios.get(`${API_BASE}/health`, { headers: { 'X-API-Key': API_KEY } });
            setHealth(res.data);
        } catch (e) { console.error('Health fetch failed', e); }
    };

    const triggerTask = async () => {
        if (!task) return;
        setIsExecuting(true);
        try {
            await axios.post(`${API_BASE}/execute`, { task }, { headers: { 'X-API-Key': API_KEY } });
            setTask('');
        } catch (e) { alert('Execution failed to start'); }
        finally { setIsExecuting(false); }
    };

    useEffect(() => {
        fetchHealth();
        const interval = setInterval(() => {
            fetchLogs();
            fetchHealth();
        }, 3000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="min-h-screen p-6 flex flex-col gap-6">
            {/* Header */}
            <header className="flex justify-between items-center border-b border-slate-800 pb-4">
                <div className="flex items-center gap-3">
                    <Activity className="text-blue-500 w-8 h-8" />
                    <h1 className="text-2xl font-bold tracking-tight">SWARM <span className="text-blue-500">COMMAND CENTER</span></h1>
                </div>
                <div className="flex items-center gap-4">
                    <div className={`px-3 py-1 rounded-full text-xs font-medium ${health.status === 'healthy' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                        ● {health.status?.toUpperCase() || 'OFFLINE'}
                    </div>
                </div>
            </header>

            <div className="grid grid-cols-12 gap-6">
                {/* Left Panel: Health & Stats */}
                <div className="col-span-4 flex flex-col gap-6">
                    <section className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-xl">
                        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">
                            <ShieldCheck className="w-4 h-4" /> Agent Matrix
                        </h2>
                        <div className="grid grid-cols-1 gap-3">
                            {health.agents?.map((agent, i) => (
                                <div key={i} className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                                    <span className="text-sm font-medium">{agent.name}</span>
                                    <span className={`text-[10px] px-2 py-0.5 rounded ${agent.status === 'online' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                        {agent.status}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-xl">
                        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">
                            <Database className="w-4 h-4" /> Storage Sync
                        </h2>
                        <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                            <span className="text-sm">Supabase</span>
                            <span className="text-green-500 text-xs font-bold">ACTIVE</span>
                        </div>
                        <div className="flex justify-between items-center p-3 mt-2 bg-slate-800/50 rounded-lg border border-slate-700/50">
                            <span className="text-sm">Firebase Backup</span>
                            <span className="text-blue-500 text-xs font-bold">SYNCED</span>
                        </div>
                    </section>

                    <section className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-xl">
                        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">
                            <Brain className="w-4 h-4" /> Knowledge Hub
                        </h2>
                        <div className="text-xs text-slate-500 italic">
                            Dify Brain connected. Indexing active.
                        </div>
                    </section>
                </div>

                {/* Right Panel: Terminal & Control */}
                <div className="col-span-8 flex flex-col gap-6">
                    <section className="bg-black border border-slate-800 rounded-xl overflow-hidden shadow-2xl flex flex-col h-[600px]">
                        <div className="bg-slate-900 px-4 py-2 border-b border-slate-800 flex justify-between items-center">
                            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                                <Terminal className="w-3 h-3" /> MasterLog Stream
                            </div>
                            <div className="flex gap-1.5">
                                <div className="w-2.5 h-2.5 rounded-full bg-red-500/50"></div>
                                <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50"></div>
                                <div className="w-2.5 h-2.5 rounded-full bg-green-500/50"></div>
                            </div>
                        </div>
                        <div className="flex-1 p-4 font-mono text-xs overflow-y-auto space-y-2 scrollbar-hide">
                            {logs.map((log, i) => (
                                <div key={i} className="flex gap-3 animate-in fade-in slide-in-from-left-2 duration-300">
                                    <span className="text-slate-600">[{log.timestamp}]</span>
                                    <span className={`font-bold ${log.level === 'error' ? 'text-red-500' : 'text-blue-400'}`}>
                                        {log.agent || 'SYSTEM'}:
                                    </span>
                                    <span className="text-slate-300">{log.message}</span>
                                </div>
                            ))}
                            {logs.length === 0 && <div className="text-slate-700 italic text-center mt-20">Awaiting system events...</div>}
                        </div>
                    </section>

                    <section className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-xl">
                        <div className="flex gap-3">
                            <input 
                                type="text" 
                                value={task}
                                onChange={(e) => setTask(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && triggerTask()}
                                placeholder="Enter research goal or task for the swarm..."
                                className="flex-1 bg-black border border-slate-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                            />
                            <button 
                                onClick={triggerTask}
                                disabled={isExecuting}
                                className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium transition-all active:scale-95"
                            >
                                <Send className="w-4 h-4" /> {isExecuting ? 'Executing...' : 'Launch'}
                            </button>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
};

export default App;
