import { useState, useEffect } from 'react'
import client from '../api/client'
import { TrendingUp, BarChart3, DollarSign, Loader2 } from 'lucide-react'
import {
    AreaChart, Area, LineChart, Line, BarChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

export default function Forecasting() {
    const [spendingForecast, setSpendingForecast] = useState(null)
    const [savingsForecast, setSavingsForecast] = useState(null)
    const [cashflow, setCashflow] = useState(null)
    const [loading, setLoading] = useState(true)
    const [periods, setPeriods] = useState(6)
    const [method, setMethod] = useState('exponential')

    useEffect(() => {
        fetchForecasts()
    }, [periods, method])

    const fetchForecasts = async () => {
        setLoading(true)
        try {
            const [spending, savings, cf] = await Promise.allSettled([
                client.get(`/api/v1/forecasting/spending?periods=${periods}&method=${method}`),
                client.get(`/api/v1/forecasting/savings?periods=${periods}`),
                client.get(`/api/v1/forecasting/cashflow?periods=${periods}`),
            ])

            if (spending.status === 'fulfilled') setSpendingForecast(spending.value.data)
            if (savings.status === 'fulfilled') setSavingsForecast(savings.value.data)
            if (cf.status === 'fulfilled') setCashflow(cf.value.data)
        } catch (err) {
            console.error('Forecast error:', err)
        } finally {
            setLoading(false)
        }
    }

    const spendingChartData = spendingForecast?.forecast?.map((val, i) => ({
        period: `M+${i + 1}`,
        forecast: val,
        lower: spendingForecast.confidence_lower?.[i],
        upper: spendingForecast.confidence_upper?.[i],
    })) || []

    const savingsChartData = savingsForecast?.savings_forecast?.map((val, i) => ({
        period: `M+${i + 1}`,
        savings: val,
        income: savingsForecast.income_forecast?.forecast?.[i] || 0,
        expenses: savingsForecast.expense_forecast?.forecast?.[i] || 0,
    })) || []

    const cashflowData = cashflow?.historical_months?.map((m, i) => ({
        month: m,
        income: cashflow.historical_income?.[i] || 0,
        expenses: cashflow.historical_expenses?.[i] || 0,
        net: (cashflow.historical_income?.[i] || 0) - (cashflow.historical_expenses?.[i] || 0),
    })) || []

    return (
        <div className="page-container">
            <div className="page-header flex items-center justify-between">
                <div>
                    <h1 className="page-title">Forecasting</h1>
                    <p className="page-subtitle">AI-powered financial projections</p>
                </div>

                <div className="flex items-center gap-3">
                    <select
                        value={method}
                        onChange={(e) => setMethod(e.target.value)}
                        className="input-field w-40 py-2 text-sm"
                    >
                        <option value="exponential">Exponential</option>
                        <option value="linear">Linear</option>
                        <option value="moving_average">Moving Avg</option>
                    </select>
                    <select
                        value={periods}
                        onChange={(e) => setPeriods(Number(e.target.value))}
                        className="input-field w-32 py-2 text-sm"
                    >
                        <option value="3">3 months</option>
                        <option value="6">6 months</option>
                        <option value="12">12 months</option>
                    </select>
                </div>
            </div>

            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Spending Forecast */}
                    <div className="glass-card p-6">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-primary-400" />
                            Spending Forecast
                            {spendingForecast?.historical_stats && (
                                <span className="text-xs text-surface-200/40 ml-auto font-normal">
                                    Based on {spendingForecast.historical_stats.data_points} data points ·
                                    Avg: ${spendingForecast.historical_stats.mean?.toLocaleString()}
                                </span>
                            )}
                        </h3>
                        {spendingChartData.length > 0 ? (
                            <ResponsiveContainer width="100%" height={300}>
                                <AreaChart data={spendingChartData}>
                                    <defs>
                                        <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                    <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 12 }} />
                                    <YAxis tick={{ fill: '#64748b', fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                                    <Tooltip
                                        contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                                        formatter={(val) => `$${val?.toLocaleString()}`}
                                    />
                                    <Area type="monotone" dataKey="upper" stroke="transparent" fill="rgba(99,102,241,0.08)" />
                                    <Area type="monotone" dataKey="forecast" stroke="#6366f1" fill="url(#spendGrad)" strokeWidth={2} dot />
                                    <Area type="monotone" dataKey="lower" stroke="transparent" fill="rgba(99,102,241,0.08)" />
                                    <Legend />
                                </AreaChart>
                            </ResponsiveContainer>
                        ) : (
                            <EmptyChart />
                        )}
                    </div>

                    {/* Savings Forecast */}
                    <div className="glass-card p-6">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <DollarSign className="w-5 h-5 text-emerald-400" />
                            Savings Projection
                        </h3>
                        {savingsChartData.length > 0 ? (
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={savingsChartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                    <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 12 }} />
                                    <YAxis tick={{ fill: '#64748b', fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                                    <Tooltip
                                        contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                                        formatter={(val) => `$${val?.toLocaleString()}`}
                                    />
                                    <Bar dataKey="income" name="Income" fill="#10b981" radius={[4, 4, 0, 0]} />
                                    <Bar dataKey="expenses" name="Expenses" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                                    <Bar dataKey="savings" name="Savings" fill="#6366f1" radius={[4, 4, 0, 0]} />
                                    <Legend />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <EmptyChart />
                        )}
                    </div>

                    {/* Historical Cash Flow */}
                    {cashflowData.length > 0 && (
                        <div className="glass-card p-6">
                            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                <BarChart3 className="w-5 h-5 text-sky-400" />
                                Historical Cash Flow
                            </h3>
                            <ResponsiveContainer width="100%" height={300}>
                                <LineChart data={cashflowData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                    <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 12 }} />
                                    <YAxis tick={{ fill: '#64748b', fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                                    <Tooltip
                                        contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                                        formatter={(val) => `$${val?.toLocaleString()}`}
                                    />
                                    <Line type="monotone" dataKey="income" stroke="#10b981" strokeWidth={2} dot />
                                    <Line type="monotone" dataKey="expenses" stroke="#f43f5e" strokeWidth={2} dot />
                                    <Line type="monotone" dataKey="net" stroke="#6366f1" strokeWidth={2} strokeDasharray="5 5" dot />
                                    <Legend />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

function EmptyChart() {
    return (
        <div className="flex flex-col items-center justify-center h-64 text-surface-200/30">
            <TrendingUp className="w-12 h-12 mb-3" />
            <p className="text-sm">Upload transactions data to see forecasts</p>
        </div>
    )
}
