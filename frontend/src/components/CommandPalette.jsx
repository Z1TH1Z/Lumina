import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Command } from 'cmdk';
import { DialogTitle, DialogDescription } from '@radix-ui/react-dialog';
import {
    Calculator,
    LayoutDashboard,
    FileText,
    CreditCard,
    AlertTriangle,
    TrendingUp,
    MessageSquare,
    Settings,
    Wrench,
    Search,
    Sparkles
} from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';
import api from '../api/client';

export default function CommandPalette() {
    const [open, setOpen] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const [forecastResult, setForecastResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    // Toggle the menu when ⌘K is pressed
    useEffect(() => {
        const down = (e) => {
            if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                setOpen((open) => !open);
            }
        };
        document.addEventListener('keydown', down);
        return () => document.removeEventListener('keydown', down);
    }, []);

    const runCommand = (command) => {
        setOpen(false);
        command();
    };

    const handleForecastSubmit = async () => {
        if (!inputValue.startsWith('/forecast')) return;

        setLoading(true);
        try {
            // For demonstration, we simply hit the exponential spending forecast 
            // and adjust it based on the text if it contains keywords like "increase"
            const res = await api.get('/forecasting/spending?periods=6&method=exponential');
            const data = res.data;

            let modifier = 1.0;
            if (inputValue.toLowerCase().includes('10%') && inputValue.toLowerCase().includes('increase')) {
                modifier = 1.1;
            }

            const chartData = data.forecast.map((val, i) => ({
                month: data.months ? data.months[i] : `Month ${i + 1}`,
                value: val * modifier
            }));

            setForecastResult({
                title: "Adjusted Burn Rate Projection",
                data: chartData,
                base_currency: data.base_currency || 'USD'
            });
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const pages = [
        { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
        { name: 'Documents', icon: FileText, path: '/documents' },
        { name: 'Transactions', icon: CreditCard, path: '/transactions' },
        { name: 'Anomalies', icon: AlertTriangle, path: '/anomalies' },
        { name: 'Forecasting', icon: TrendingUp, path: '/forecasting' },
        { name: 'AI Chat', icon: MessageSquare, path: '/chat' },
        { name: 'Financial Tools', icon: Wrench, path: '/tools' },
        { name: 'Settings', icon: Settings, path: '/settings' },
    ];

    return (
        <Command.Dialog
            open={open}
            onOpenChange={setOpen}
            label="Global Command Menu"
            className="cmdk-dialog"
            aria-describedby={undefined}
        >
            <DialogTitle className="sr-only">Command Palette</DialogTitle>
            <DialogDescription className="sr-only">Search for actions, pages, and run AI forecasts.</DialogDescription>
            <div className="flex items-center px-4 border-b border-white/10">
                <Search className="w-5 h-5 text-surface-400 mr-2 shrink-0" />
                <Command.Input
                    autoFocus
                    placeholder="Type a command or /forecast Q3 burn rate..."
                    value={inputValue}
                    onValueChange={setInputValue}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && inputValue.startsWith('/forecast')) {
                            e.preventDefault();
                            handleForecastSubmit();
                        }
                    }}
                    className="w-full bg-transparent text-white border-0 py-4 focus:ring-0 outline-none placeholder:text-surface-500"
                />
            </div>

            <Command.List className="max-h-[300px] overflow-y-auto p-2 scrollbar-thin">
                <Command.Empty className="py-6 text-center text-sm text-surface-400">
                    {inputValue.startsWith('/forecast')
                        ? "Press Enter to run AI Forecast..."
                        : "No results found."}
                </Command.Empty>

                {!inputValue.startsWith('/') && (
                    <Command.Group heading="Navigation" className="text-xs font-semibold text-surface-500 px-2 py-1 mb-1">
                        {pages.map((page) => (
                            <Command.Item
                                key={page.path}
                                onSelect={() => runCommand(() => navigate(page.path))}
                                className="cmdk-item"
                            >
                                <page.icon className="w-4 h-4 mr-2 text-surface-400" />
                                {page.name}
                            </Command.Item>
                        ))}
                    </Command.Group>
                )}

                {inputValue.startsWith('/forecast') && (
                    <Command.Group heading="AI Actions" className="text-xs font-semibold text-surface-500 px-2 py-1">
                        <Command.Item
                            onSelect={() => handleForecastSubmit()}
                            className="cmdk-item flex items-center gap-2"
                        >
                            {loading ? <div className="w-4 h-4 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin shrink-0" /> : <Sparkles className="w-4 h-4 text-primary-400 shrink-0" />}
                            <span className="text-primary-300">Run custom forecast calculation</span>
                        </Command.Item>
                    </Command.Group>
                )}

                {forecastResult && inputValue.startsWith('/forecast') && !loading && (
                    <div className="p-4 mt-2 bg-surface-800/50 rounded-lg border border-white/5">
                        <h4 className="text-sm font-medium text-white mb-3">{forecastResult.title}</h4>
                        <div className="h-24 w-full mb-3">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={forecastResult.data}>
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                                        itemStyle={{ color: '#e2e8f0' }}
                                        formatter={(value) => [`$${parseFloat(value).toFixed(2)}`, 'Projected']}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="value"
                                        stroke="#8b5cf6"
                                        strokeWidth={2}
                                        dot={{ fill: '#8b5cf6', strokeWidth: 2, r: 3 }}
                                        activeDot={{ r: 5, fill: '#a78bfa' }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                            {forecastResult.data.slice(0, 3).map((d, i) => (
                                <div key={i} className="bg-surface-900 p-2 rounded border border-white/5 text-center">
                                    <div className="text-surface-400 mb-1">{d.month || `M${i + 1}`}</div>
                                    <div className="text-white font-medium">${d.value.toFixed(0)}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </Command.List>
        </Command.Dialog>
    );
}
