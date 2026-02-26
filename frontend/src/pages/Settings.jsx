import { useState, useEffect } from 'react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Settings as SettingsIcon, Database, Brain, Shield, Server, Check } from 'lucide-react'

export default function Settings() {
    const { user, updateProfile } = useAuth()
    const [health, setHealth] = useState(null)
    const [indexStats, setIndexStats] = useState(null)
    const [saving, setSaving] = useState(false)

    const handleCurrencyChange = async (e) => {
        setSaving(true)
        try {
            await updateProfile({ base_currency: e.target.value })
            // Refresh the page to trigger all charts/dashboard fetching in the new currency
            window.location.reload()
        } catch (error) {
            console.error('Failed to update currency', error)
        } finally {
            setSaving(false)
        }
    }

    useEffect(() => {
        fetchStatus()
    }, [])

    const fetchStatus = async () => {
        try {
            const [healthRes, indexRes] = await Promise.allSettled([
                client.get('/api/v1/health'),
                client.get('/api/v1/rag/index/stats'),
            ])
            if (healthRes.status === 'fulfilled') setHealth(healthRes.value.data)
            if (indexRes.status === 'fulfilled') setIndexStats(indexRes.value.data)
        } catch { }
    }

    return (
        <div className="page-container">
            <div className="page-header">
                <h1 className="page-title">Settings</h1>
                <p className="page-subtitle">System configuration and status</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* User Profile */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Shield className="w-5 h-5 text-primary-400" />
                        User Profile
                    </h3>
                    <div className="space-y-3">
                        <InfoRow label="Username" value={user?.username} />
                        <InfoRow label="Email" value={user?.email} />
                        <InfoRow label="Full Name" value={user?.full_name || 'Not set'} />
                        <InfoRow label="Role" value={user?.role?.toUpperCase()} />
                        <InfoRow label="Status" value={user?.is_active ? 'Active' : 'Inactive'} />
                    </div>
                </div>

                {/* System Health */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Server className="w-5 h-5 text-emerald-400" />
                        System Health
                    </h3>
                    <div className="space-y-3">
                        <StatusRow label="API Server" status={health?.status === 'healthy'} />
                        <StatusRow label="Database" status={health?.database === 'connected'} />
                        <StatusRow label="LLM (Ollama)" status={health?.llm_available} />
                        <InfoRow label="Version" value={health?.version || '—'} />
                    </div>
                </div>

                {/* Preferences */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <SettingsIcon className="w-5 h-5 text-indigo-400" />
                        Preferences
                    </h3>
                    <div className="space-y-3">
                        <div className="flex items-center justify-between py-2 border-b border-white/5">
                            <div>
                                <span className="text-sm font-medium text-white block">Display Currency</span>
                                <span className="text-xs text-surface-200/50">All dashboard metrics will convert to this currency</span>
                            </div>
                            <select
                                value={user?.base_currency || 'USD'}
                                onChange={handleCurrencyChange}
                                disabled={saving}
                                className="input-field py-1 px-3 w-32"
                            >
                                <option value="USD">USD ($)</option>
                                <option value="EUR">EUR (€)</option>
                                <option value="GBP">GBP (£)</option>
                                <option value="INR">INR (₹)</option>
                                <option value="CAD">CAD ($)</option>
                                <option value="AUD">AUD ($)</option>
                                <option value="JPY">JPY (¥)</option>
                            </select>
                        </div>
                    </div>
                </div>

                {/* RAG Index */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Database className="w-5 h-5 text-sky-400" />
                        RAG Vector Index
                    </h3>
                    <div className="space-y-3">
                        <InfoRow label="Total Chunks" value={indexStats?.total_chunks || 0} />
                        <InfoRow label="Total Documents" value={indexStats?.total_documents || 0} />
                    </div>
                </div>

                {/* About */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Brain className="w-5 h-5 text-amber-400" />
                        About
                    </h3>
                    <div className="space-y-3">
                        <InfoRow label="Application" value="AI Financial Copilot" />
                        <InfoRow label="License" value="Open Source" />
                        <InfoRow label="Stack" value="React + FastAPI + PostgreSQL" />
                        <InfoRow label="LLM" value="Ollama (Llama 3 / Mistral)" />
                    </div>
                </div>
            </div>
        </div>
    )
}

function InfoRow({ label, value }) {
    return (
        <div className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
            <span className="text-sm text-surface-200/50">{label}</span>
            <span className="text-sm font-medium">{value}</span>
        </div>
    )
}

function StatusRow({ label, status }) {
    return (
        <div className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
            <span className="text-sm text-surface-200/50">{label}</span>
            <span className={`flex items-center gap-1.5 text-sm font-medium ${status ? 'text-emerald-400' : 'text-rose-400'
                }`}>
                <span className={`w-2 h-2 rounded-full ${status ? 'bg-emerald-400' : 'bg-rose-400'} animate-pulse`} />
                {status ? 'Connected' : 'Disconnected'}
            </span>
        </div>
    )
}
