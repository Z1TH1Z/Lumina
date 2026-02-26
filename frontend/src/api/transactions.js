import client from './client'

export const transactionsApi = {
    fetchTransactions: async (filter) => {
        const params = filter !== 'all' ? `?category=${filter}` : ''
        const res = await client.get(`/api/v1/transactions/${params}`)
        return res.data
    },

    updateCategory: async (id, correctCategory) => {
        const res = await client.post('/api/v1/transactions/feedback', {
            transaction_id: id,
            correct_category: correctCategory,
        })
        return res.data
    }
}
