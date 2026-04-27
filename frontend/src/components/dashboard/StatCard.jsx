import { ArrowUpRight, ArrowDownRight } from 'lucide-react'

export default function StatCard({ icon: Icon, label, value, trend, color, trendLabel }) {
    const colorClasses = {
        primary: 'from-primary-500/20 to-primary-500/5 text-primary-400',
        sky: 'from-sky-500/20 to-sky-500/5 text-sky-400',
        amber: 'from-amber-500/20 to-amber-500/5 text-amber-400',
        emerald: 'from-emerald-500/20 to-emerald-500/5 text-emerald-400',
    }

    const iconBg = {
        primary: 'bg-primary-500/10',
        sky: 'bg-sky-500/10',
        amber: 'bg-amber-500/10',
        emerald: 'bg-emerald-500/10',
    }

    return (
        <div className="stat-card animate-fade-in">
            <div className="flex items-start justify-between mb-4">
                <div className={`p-3 rounded-xl ${iconBg[color]}`}>
                    <Icon className={`w-5 h-5 ${colorClasses[color]?.split(' ').pop()}`} />
                </div>
                {trend !== 0 && (
                    <span className={`flex items-center gap-1 text-xs font-medium ${trend > 0 ? 'text-emerald-400' : 'text-rose-400'
                        }`}>
                        {trend > 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        {trendLabel || `${Math.abs(trend)}%`}
                    </span>
                )}
            </div>
            <p className="text-2xl font-bold mb-1">{value}</p>
            <p className="text-sm text-surface-200/50">{label}</p>
        </div>
    )
}
