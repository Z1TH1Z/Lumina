import {
    DollarSign, TrendingUp, AlertTriangle,
    FileText, CreditCard, PieChart, Activity,
} from 'lucide-react'
import {
    AreaChart, Area, BarChart, Bar, PieChart as RechartsPie, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import BudgetProgressCard from '../components/BudgetProgressCard'
import StatCard from '../components/dashboard/StatCard'
import EmptyState from '../components/dashboard/EmptyState'
import { useDashboard } from '../hooks/useDashboard'

const COLORS = ['#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6', '#ec4899', '#14b8a6']

export default function Dashboard() {
    const {
        user,
        loading,
        summary,
        anomalies,
        totalSpending,
        totalTransactions,
        anomalyCount,
        categories,
        categoryChartData,
        forecastData,
        formatCurrency,
    } = useDashboard()

    if (loading) return null // Could return a spinner here instead

    return (
        <div className="page-container">
            {/* Header */}
            <div className="page-header flex items-center justify-between">
                <div>
                    <h1 className="page-title">
                        Welcome back, <span className="gradient-text">{user?.full_name || user?.username || 'User'}</span>
                    </h1>
                    <p className="page-subtitle">Here's your financial overview</p>
                </div>
                <div className="badge-sky flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5" />
                    Live
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <StatCard
                    icon={DollarSign}
                    label="Total Spending"
                    value={formatCurrency(totalSpending)}
                    trend={-2.4}
                    color="primary"
                />
                <StatCard
                    icon={CreditCard}
                    label="Transactions"
                    value={totalTransactions.toString()}
                    trend={5.1}
                    color="sky"
                />
                <StatCard
                    icon={AlertTriangle}
                    label="Anomalies"
                    value={anomalyCount.toString()}
                    trend={anomalyCount > 0 ? anomalyCount : 0}
                    color="amber"
                    trendLabel={anomalyCount > 0 ? 'needs review' : 'all clear'}
                />
                <StatCard
                    icon={FileText}
                    label="Documents"
                    value={summary ? categories.length.toString() : '0'}
                    trend={0}
                    color="emerald"
                    trendLabel="categories"
                />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* Spending by Category */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <PieChart className="w-5 h-5 text-primary-400" />
                        Spending by Category
                    </h3>
                    {categoryChartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={300}>
                            <RechartsPie>
                                <Pie
                                    data={categoryChartData}
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={100}
                                    innerRadius={60}
                                    dataKey="value"
                                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                    labelLine={false}
                                >
                                    {categoryChartData.map((_, i) => (
                                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                                    labelStyle={{ color: '#f8fafc' }}
                                    itemStyle={{ color: '#94a3b8' }}
                                    formatter={(val) => formatCurrency(val, 0)}
                                />
                            </RechartsPie>
                        </ResponsiveContainer>
                    ) : (
                        <EmptyState message="Upload documents to see spending breakdown" />
                    )}
                </div>

                {/* Category Breakdown Bar Chart */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Activity className="w-5 h-5 text-accent-sky" />
                        Category Breakdown
                    </h3>
                    {categoryChartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={categoryChartData} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                <XAxis type="number" tick={{ fill: '#64748b', fontSize: 12 }} tickFormatter={(v) => formatCurrency(v, 0)} />
                                <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} width={100} />
                                <Tooltip
                                    contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                                    formatter={(val) => formatCurrency(val, 0)}
                                />
                                <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                                    {categoryChartData.map((_, i) => (
                                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    ) : (
                        <EmptyState message="No data to display yet" />
                    )}
                </div>
            </div>

            {/* Forecast & Budgets Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* Forecast Chart */}
                <div className="glass-card p-6 flex flex-col h-full">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-accent-emerald" />
                        Spending Forecast
                    </h3>

                    {forecastData.length > 0 ? (
                        <div className="flex-1 min-h-[300px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={forecastData}>
                                    <defs>
                                        <linearGradient id="forecastGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                    <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 12 }} />
                                    <YAxis tick={{ fill: '#64748b', fontSize: 12 }} tickFormatter={(v) => formatCurrency(v, 0)} />
                                    <Tooltip
                                        contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                                        formatter={(val) => formatCurrency(val, 0)}
                                    />
                                    <Area type="monotone" dataKey="upper" stroke="transparent" fill="rgba(99,102,241,0.1)" />
                                    <Area type="monotone" dataKey="forecast" stroke="#6366f1" fill="url(#forecastGradient)" strokeWidth={2} />
                                    <Area type="monotone" dataKey="lower" stroke="transparent" fill="rgba(99,102,241,0.1)" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <EmptyState message="Upload more documents to generate forecasts" />
                    )}
                </div>

                {/* Monthly Budgets */}
                <BudgetProgressCard categories={categories.map(c => c.category)} />
            </div>

            {/* Recent Anomalies */}
            {anomalies.length > 0 && (
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-amber-400" />
                        Recent Anomalies
                    </h3>
                    <div className="space-y-3">
                        {anomalies.slice(0, 5).map((a, i) => (
                            <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-amber-500/10">
                                <div>
                                    <p className="font-medium">{a.description}</p>
                                    <p className="text-sm text-surface-200/50">{a.merchant} · {a.category}</p>
                                </div>
                                <div className="text-right">
                                    <p className="font-semibold text-amber-400">{formatCurrency(Math.abs(a.amount))}</p>
                                    <p className="text-xs text-surface-200/40">Score: {(a.anomaly_score * 100).toFixed(0)}%</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
