import { useState, useEffect } from 'react'
import client from '../api/client'
import { AlertTriangle, Shield, ShieldAlert, Sparkles, Loader2, CheckCircle, XCircle } from 'lucide-react'

export default function Anomalies() {
    const [anomalies, setAnomalies] = useState([])
    const [loading, setLoading] = useState(true)
    const [detecting, setDetecting] = useState(false)
    const [explaining, setExplaining] = useState(null)
    const [detectResult, setDetectResult] = useState(null)

    useEffect(() => {
        fetchAnomalies()
    }, [])

    const fetchAnomalies = async () => {
        try {
            const res = await client.get('/api/v1/anomalies/')
            setAnomalies(res.data.anomalies || [])
        } catch (err) {
            console.error('Failed to fetch anomalies:', err)
        } finally {
            setLoading(false)
        }
    }

    const runDetection = async () => {
        setDetecting(true)
        try {
            const res = await client.post('/api/v1/anomalies/detect?z_threshold=2.5')
            setDetectResult(res.data)
            fetchAnomalies()
        } catch (err) {
            console.error('Detection failed:', err)
        } finally {
            setDetecting(false)
        }
    }

    const explainAnomaly = async (id) => {
        setExplaining(id)
        try {
            const res = await client.post(`/api/v1/anomalies/${id}/explain`)
            setAnomalies((prev) =>
                prev.map((a) => (a.id === id ? { ...a, anomaly_explanation: res.data.explanation } : a))
            )
        } catch (err) {
            console.error('Explain failed:', err)
        } finally {
            setExplaining(null)
        }
    }

    const confirmAnomaly = async (id, isLegitimate) => {
        try {
            await client.put(`/api/v1/anomalies/${id}/confirm?is_legitimate=${isLegitimate}`)
            fetchAnomalies()
        } catch (err) {
            console.error('Confirm failed:', err)
        }
    }

    return (
        <div className="page-container">
            <div className="page-header flex items-center justify-between">
                <div>
                    <h1 className="page-title">Anomaly Detection</h1>
                    <p className="page-subtitle">AI-powered transaction anomaly detection</p>
                </div>
                <button onClick={runDetection} disabled={detecting} className="btn-primary flex items-center gap-2">
                    {detecting ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                        <ShieldAlert className="w-4 h-4" />
                    )}
                    {detecting ? 'Scanning...' : 'Run Detection'}
                </button>
            </div>

            {/* Detection Result */}
            {detectResult && (
                <div className="glass-card p-6 mb-6 animate-slide-up">
                    <div className="flex items-center gap-4">
                        <Shield className="w-8 h-8 text-primary-400" />
                        <div>
                            <p className="font-semibold">Detection Complete</p>
                            <p className="text-sm text-surface-200/50">
                                Scanned {detectResult.total_checked} transactions · Found {detectResult.anomaly_count} anomalies
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Anomaly List */}
            <div className="space-y-4">
                {anomalies.length === 0 && !loading ? (
                    <div className="glass-card p-12 text-center">
                        <Shield className="w-12 h-12 text-emerald-400/20 mx-auto mb-3" />
                        <p className="text-surface-200/40">No anomalies detected</p>
                        <p className="text-sm text-surface-200/25 mt-1">Run detection to scan your transactions</p>
                    </div>
                ) : (
                    anomalies.map((anomaly) => (
                        <div key={anomaly.id} className="glass-card p-6 border-l-4 border-amber-500/60 animate-fade-in">
                            <div className="flex items-start justify-between mb-4">
                                <div className="flex items-start gap-4">
                                    <div className="p-3 rounded-xl bg-amber-500/10">
                                        <AlertTriangle className="w-5 h-5 text-amber-400" />
                                    </div>
                                    <div>
                                        <p className="font-semibold">{anomaly.description}</p>
                                        <div className="flex items-center gap-3 mt-1 text-sm text-surface-200/40">
                                            <span>{anomaly.merchant}</span>
                                            <span>·</span>
                                            <span className="capitalize">{anomaly.category}</span>
                                            <span>·</span>
                                            <span>{anomaly.date?.split('T')[0]}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="text-xl font-bold text-amber-400">${Math.abs(anomaly.amount).toFixed(2)}</p>
                                    <div className="mt-1 flex items-center gap-2">
                                        <div className="w-20 h-1.5 rounded-full bg-white/10 overflow-hidden">
                                            <div
                                                className="h-full rounded-full bg-gradient-to-r from-amber-500 to-rose-500"
                                                style={{ width: `${Math.min((anomaly.anomaly_score || 0) * 100, 100)}%` }}
                                            />
                                        </div>
                                        <span className="text-xs text-surface-200/40">
                                            {((anomaly.anomaly_score || 0) * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Explanation */}
                            {anomaly.anomaly_explanation && (
                                <div className="mt-4 p-4 rounded-xl bg-white/5 border border-white/5">
                                    <div className="flex items-center gap-2 mb-2 text-xs font-medium text-primary-400">
                                        <Sparkles className="w-3.5 h-3.5" />
                                        AI Analysis
                                    </div>
                                    <p className="text-sm text-surface-200/70">{anomaly.anomaly_explanation}</p>
                                </div>
                            )}

                            {/* Actions */}
                            <div className="mt-4 flex items-center gap-3">
                                {!anomaly.anomaly_explanation && (
                                    <button
                                        onClick={() => explainAnomaly(anomaly.id)}
                                        disabled={explaining === anomaly.id}
                                        className="btn-secondary text-xs flex items-center gap-1.5"
                                    >
                                        {explaining === anomaly.id ? (
                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                        ) : (
                                            <Sparkles className="w-3.5 h-3.5" />
                                        )}
                                        Explain
                                    </button>
                                )}
                                <button
                                    onClick={() => confirmAnomaly(anomaly.id, false)}
                                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 transition-colors"
                                >
                                    <XCircle className="w-3.5 h-3.5" />
                                    Confirm Anomaly
                                </button>
                                <button
                                    onClick={() => confirmAnomaly(anomaly.id, true)}
                                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                                >
                                    <CheckCircle className="w-3.5 h-3.5" />
                                    Mark Legitimate
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}
