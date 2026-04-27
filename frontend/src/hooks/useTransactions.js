import { useState, useEffect } from 'react'
import { transactionsApi } from '../api/transactions'
import { useAuth } from '../context/AuthContext'

export const CATEGORIES = [
    'all', 'housing', 'food', 'transport', 'utilities', 'entertainment',
    'healthcare', 'shopping', 'income', 'transfer', 'investment', 'insurance', 'education', 'other'
]

export function useTransactions() {
    const { user } = useAuth()
    const [transactions, setTransactions] = useState([])
    const [filter, setFilter] = useState('all')
    const [loading, setLoading] = useState(true)
    const [editingId, setEditingId] = useState(null)
    const [editCategory, setEditCategory] = useState('')

    useEffect(() => {
        let isMounted = true

        const loadTransactions = async () => {
            setLoading(true)
            try {
                const data = await transactionsApi.fetchTransactions(filter)
                if (isMounted) setTransactions(data)
            } catch (err) {
                console.error('Failed to fetch transactions:', err)
            } finally {
                if (isMounted) setLoading(false)
            }
        }

        loadTransactions()

        return () => {
            isMounted = false
        }
    }, [filter])

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: user?.base_currency || 'USD',
        }).format(amount)
    }

    const updateCategory = async (id, category) => {
        try {
            await transactionsApi.updateCategory(id, category)
            setEditingId(null)

            // Re-fetch transactions
            const data = await transactionsApi.fetchTransactions(filter)
            setTransactions(data)
        } catch (err) {
            console.error('Update failed:', err)
        }
    }

    const startEditing = (id, category) => {
        setEditingId(id)
        setEditCategory(category)
    }

    const cancelEditing = () => {
        setEditingId(null)
    }

    return {
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
    }
}
