import { useState, useEffect } from 'react'
import { dashboardApi } from '../api/dashboard'
import { useAuth } from '../context/AuthContext'

export function useDashboard() {
    const { user } = useAuth()
    const [summary, setSummary] = useState(null)
    const [forecast, setForecast] = useState(null)
    const [anomalies, setAnomalies] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        let isMounted = true

        const loadData = async () => {
            try {
                const [summaryRes, anomalyRes] = await Promise.allSettled([
                    dashboardApi.fetchSummary(),
                    dashboardApi.fetchAnomalies(),
                ])

                if (!isMounted) return

                if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value)
                if (anomalyRes.status === 'fulfilled') setAnomalies(anomalyRes.value.anomalies || [])

                try {
                    const forecastData = await dashboardApi.fetchForecast()
                    if (isMounted) setForecast(forecastData)
                } catch { }
            } catch (err) {
                console.error('Dashboard fetch error:', err)
            } finally {
                if (isMounted) setLoading(false)
            }
        }

        loadData()

        return () => {
            isMounted = false
        }
    }, [])

    const formatCurrency = (amount, maxDecimals = 2) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: user?.base_currency || 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: maxDecimals
        }).format(amount)
    }

    // Derived State
    const totalSpending = summary?.total_spending || 0
    const totalTransactions = summary?.total_transactions || 0
    const anomalyCount = anomalies.length
    const categories = summary?.categories || []

    const categoryChartData = categories
        .filter((c) => c.total !== 0)
        .map((c) => ({
            name: c.category.charAt(0).toUpperCase() + c.category.slice(1),
            value: Math.abs(c.total),
            count: c.count,
        }))
        .sort((a, b) => b.value - a.value)

    const forecastData = forecast?.forecast?.map((val, i) => ({
        period: `Month ${i + 1}`,
        forecast: val,
        lower: forecast.confidence_lower?.[i] || val * 0.8,
        upper: forecast.confidence_upper?.[i] || val * 1.2,
    })) || []

    return {
        user,
        loading,
        summary,
        forecast,
        anomalies,
        totalSpending,
        totalTransactions,
        anomalyCount,
        categories,
        categoryChartData,
        forecastData,
        formatCurrency,
    }
}
