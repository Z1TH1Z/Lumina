import { useState, useEffect } from 'react'
import { Plus, Target, TrendingUp, AlertCircle, Trash2, Pencil } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'

export default function BudgetProgressCard({ categories }) {
    const { user } = useAuth()
    const [budgets, setBudgets] = useState([])
    const [loading, setLoading] = useState(true)
    const [showForm, setShowForm] = useState(false)
    const [formData, setFormData] = useState({ category: '', amount: '' })

    const fetchBudgets = async () => {
        try {
            const res = await client.get('/api/v1/budgets/progress')
            setBudgets(res.data)
        } catch (error) {
            console.error('Failed to fetch budgets:', error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchBudgets()
    }, [])

    const formatCurrency = (amount, maxDecimals = 2) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: user?.base_currency || 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: maxDecimals
        }).format(amount)
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        try {
            // Get first day of current month in YYYY-MM-DD
            const d = new Date()
            const monthStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`

            await client.post('/api/v1/budgets/', {
                category: formData.category,
                amount: parseFloat(formData.amount),
                month: monthStr
            })
            setFormData({ category: '', amount: '' })
            setShowForm(false)
            fetchBudgets()
        } catch (error) {
            console.error('Failed to create budget', error)
            alert(error.response?.data?.detail || 'Failed to create budget. You may already have a budget for this category.')
        }
    }

    // Use default categories if none provided
    const availableCategories = categories || [
        "Housing", "Food", "Transport", "Utilities", "Entertainment",
        "Healthcare", "Shopping", "Personal", "Education"
    ]

    if (loading) {
        return (
            <div className="glass-card p-6 min-h-[300px] flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin"></div>
            </div>
        )
    }

    return (
        <div className="glass-card p-6 flex flex-col h-full">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <Target className="w-5 h-5 text-emerald-400" />
                    <h3 className="text-lg font-semibold text-white">Monthly Budgets</h3>
                </div>
                <button
                    onClick={() => setShowForm(!showForm)}
                    className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-surface-200 transition-colors"
                >
                    <Plus className="w-4 h-4" />
                </button>
            </div>

            {showForm && (
                <form onSubmit={handleSubmit} className="mb-6 p-4 rounded-xl bg-surface-900/50 border border-white/5 animate-slide-up">
                    <div className="flex gap-3">
                        <select
                            value={formData.category}
                            onChange={e => setFormData({ ...formData, category: e.target.value })}
                            className="input-field flex-1"
                            required
                        >
                            <option value="">Select Category</option>
                            {availableCategories.map(c => (
                                <option key={c} value={c}>{c}</option>
                            ))}
                        </select>
                        <input
                            type="number"
                            placeholder="Amount"
                            value={formData.amount}
                            onChange={e => setFormData({ ...formData, amount: e.target.value })}
                            className="input-field w-32"
                            required
                            min="1"
                            step="0.01"
                        />
                        <button type="submit" className="btn-primary">Save</button>
                    </div>
                </form>
            )}

            <div className="flex-1 overflow-y-auto space-y-5 pr-2 custom-scrollbar">
                {budgets.length === 0 ? (
                    <div className="text-center py-8">
                        <Target className="w-12 h-12 text-surface-200/20 mx-auto mb-3" />
                        <p className="text-surface-200/60 text-sm">No budgets set for this month.</p>
                        <button
                            onClick={() => setShowForm(true)}
                            className="mt-4 text-primary-400 text-sm hover:text-primary-300 font-medium"
                        >
                            Create your first budget
                        </button>
                    </div>
                ) : (
                    budgets.map(b => (
                        <div key={b.category} className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="font-medium text-surface-50 flex items-center gap-2">
                                    {b.category}
                                    {b.is_exceeded && <AlertCircle className="w-3.5 h-3.5 text-rose-400" />}
                                </span>
                                <span className="text-surface-200">
                                    <span className={b.is_exceeded ? 'text-rose-400 font-medium' : 'text-white'}>
                                        {formatCurrency(b.spent_amount)}
                                    </span>
                                    <span className="text-surface-200/40 mx-1">/</span>
                                    {formatCurrency(b.budget_amount, 0)}
                                </span>
                            </div>

                            {/* Progress bar background */}
                            <div className="h-2 w-full bg-surface-900 rounded-full overflow-hidden">
                                {/* Progress bar fill */}
                                <div
                                    className={`h-full rounded-full transition-all duration-1000 ${b.percentage_used > 100
                                        ? 'bg-rose-500'
                                        : b.percentage_used > 85
                                            ? 'bg-amber-500'
                                            : 'bg-emerald-500'
                                        }`}
                                    style={{ width: `${Math.min(b.percentage_used, 100)}%` }}
                                />
                            </div>

                            <div className="flex justify-between text-xs text-surface-200/50">
                                <span>{b.percentage_used.toFixed(0)}% used</span>
                                {b.budget_amount - b.spent_amount > 0 ? (
                                    <span>{formatCurrency(b.budget_amount - b.spent_amount, 0)} left</span>
                                ) : (
                                    <span className="text-rose-400/80">{formatCurrency(Math.abs(b.budget_amount - b.spent_amount), 0)} over</span>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}
