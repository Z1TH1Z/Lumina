import client from './client'

export const dashboardApi = {
    fetchSummary: async () => {
        const res = await client.get('/api/v1/transactions/summary')
        return res.data
    },

    fetchAnomalies: async () => {
        const res = await client.get('/api/v1/anomalies/')
        return res.data
    },

    fetchForecast: async () => {
        const res = await client.get('/api/v1/forecasting/spending?periods=6')
        return res.data
    }
}
