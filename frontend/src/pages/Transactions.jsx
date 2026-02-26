import { CATEGORIES, useTransactions } from '../hooks/useTransactions'
import TransactionTable from '../components/transactions/TransactionTable'

export default function Transactions() {
    const {
        transactions,
        filter,
        setFilter,
        loading,
        editingId,
        editCategory,
        setEditCategory,
        formatCurrency,
        updateCategory,
        startEditing,
        cancelEditing
    } = useTransactions()

    return (
        <div className="page-container">
            <div className="page-header flex items-center justify-between">
                <div>
                    <h1 className="page-title">Transactions</h1>
                    <p className="page-subtitle">{transactions.length} transactions found</p>
                </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-2 mb-6">
                {CATEGORIES.map((cat) => (
                    <button
                        key={cat}
                        onClick={() => setFilter(cat)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${filter === cat
                            ? 'bg-primary-500 text-white'
                            : 'bg-white/5 text-surface-200/60 hover:bg-white/10 hover:text-white'
                            }`}
                    >
                        {cat.charAt(0).toUpperCase() + cat.slice(1)}
                    </button>
                ))}
            </div>

            {/* Table */}
            <TransactionTable
                transactions={transactions}
                loading={loading}
                editingId={editingId}
                editCategory={editCategory}
                setEditCategory={setEditCategory}
                updateCategory={updateCategory}
                startEditing={startEditing}
                cancelEditing={cancelEditing}
                formatCurrency={formatCurrency}
            />
        </div>
    )
}
