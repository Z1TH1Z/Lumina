import { Edit3, Check, X, CreditCard } from 'lucide-react'
import { CATEGORIES } from '../../hooks/useTransactions'

const categoryColors = {
    housing: 'bg-violet-500/10 text-violet-400',
    food: 'bg-orange-500/10 text-orange-400',
    transport: 'bg-sky-500/10 text-sky-400',
    utilities: 'bg-cyan-500/10 text-cyan-400',
    entertainment: 'bg-pink-500/10 text-pink-400',
    healthcare: 'bg-rose-500/10 text-rose-400',
    shopping: 'bg-fuchsia-500/10 text-fuchsia-400',
    income: 'bg-emerald-500/10 text-emerald-400',
    transfer: 'bg-blue-500/10 text-blue-400',
    investment: 'bg-indigo-500/10 text-indigo-400',
    insurance: 'bg-teal-500/10 text-teal-400',
    education: 'bg-amber-500/10 text-amber-400',
    other: 'bg-gray-500/10 text-gray-400',
}

export default function TransactionTable({
    transactions,
    loading,
    editingId,
    editCategory,
    setEditCategory,
    updateCategory,
    startEditing,
    cancelEditing,
    formatCurrency
}) {
    return (
        <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-white/5">
                            <th className="text-left px-6 py-4 text-xs font-semibold text-surface-200/50 uppercase tracking-wider">Date</th>
                            <th className="text-left px-6 py-4 text-xs font-semibold text-surface-200/50 uppercase tracking-wider">Description</th>
                            <th className="text-left px-6 py-4 text-xs font-semibold text-surface-200/50 uppercase tracking-wider">Category</th>
                            <th className="text-right px-6 py-4 text-xs font-semibold text-surface-200/50 uppercase tracking-wider">Amount</th>
                            <th className="text-center px-6 py-4 text-xs font-semibold text-surface-200/50 uppercase tracking-wider">Status</th>
                            <th className="text-center px-6 py-4 text-xs font-semibold text-surface-200/50 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {transactions.map((txn) => (
                            <tr
                                key={txn.id}
                                className="border-b border-white/5 hover:bg-white/5 transition-colors"
                            >
                                <td className="px-6 py-4 text-sm text-surface-200/70">
                                    {new Date(txn.date).toLocaleDateString()}
                                </td>
                                <td className="px-6 py-4">
                                    <p className="text-sm font-medium">{txn.description}</p>
                                    {txn.merchant && (
                                        <p className="text-xs text-surface-200/40 mt-0.5">{txn.merchant}</p>
                                    )}
                                </td>
                                <td className="px-6 py-4">
                                    {editingId === txn.id ? (
                                        <div className="flex items-center gap-2">
                                            <select
                                                value={editCategory}
                                                onChange={(e) => setEditCategory(e.target.value)}
                                                className="input-field py-1 text-xs w-32"
                                            >
                                                {CATEGORIES.filter((c) => c !== 'all').map((c) => (
                                                    <option key={c} value={c}>{c}</option>
                                                ))}
                                            </select>
                                            <button
                                                onClick={() => updateCategory(txn.id, editCategory)}
                                                className="p-1 text-emerald-400 hover:bg-emerald-500/10 rounded"
                                            >
                                                <Check className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={cancelEditing}
                                                className="p-1 text-rose-400 hover:bg-rose-500/10 rounded"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ) : (
                                        <span className={`badge ${categoryColors[txn.category] || categoryColors.other}`}>
                                            {txn.category}
                                        </span>
                                    )}
                                </td>
                                <td className={`px-6 py-4 text-right text-sm font-semibold ${txn.amount >= 0 ? 'text-emerald-400' : 'text-rose-400'
                                    }`}>
                                    {txn.amount >= 0 ? '+' : ''}{formatCurrency(Math.abs(txn.amount))}
                                </td>
                                <td className="px-6 py-4 text-center">
                                    {txn.is_anomaly ? (
                                        <span className="badge-amber">Anomaly</span>
                                    ) : (
                                        <span className="text-xs text-surface-200/30">Normal</span>
                                    )}
                                </td>
                                <td className="px-6 py-4 text-center">
                                    <button
                                        onClick={() => startEditing(txn.id, txn.category)}
                                        className="p-1.5 rounded-lg hover:bg-white/10 text-surface-200/40 hover:text-white transition-colors"
                                    >
                                        <Edit3 className="w-4 h-4" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {transactions.length === 0 && !loading && (
                <div className="p-12 text-center">
                    <CreditCard className="w-12 h-12 text-surface-200/20 mx-auto mb-3" />
                    <p className="text-surface-200/40">No transactions found</p>
                </div>
            )}
        </div>
    )
}
