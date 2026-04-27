import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

const client = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor for JWT
client.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => Promise.reject(error),
)

// Track whether a refresh is already in-flight to avoid concurrent refreshes
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
    failedQueue.forEach(({ resolve, reject }) => {
        if (error) {
            reject(error)
        } else {
            resolve(token)
        }
    })
    failedQueue = []
}

// Response interceptor: auto-refresh token on 401
client.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config

        // Only attempt refresh for 401 errors, not on the refresh endpoint itself
        if (
            error.response?.status === 401 &&
            !originalRequest._retry &&
            !originalRequest.url?.includes('/api/v1/auth/refresh') &&
            !originalRequest.url?.includes('/api/v1/auth/login')
        ) {
            if (isRefreshing) {
                // Another refresh is in-flight — queue this request
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject })
                }).then((token) => {
                    originalRequest.headers.Authorization = `Bearer ${token}`
                    return client(originalRequest)
                })
            }

            originalRequest._retry = true
            isRefreshing = true

            const refreshToken = localStorage.getItem('refresh_token')
            if (refreshToken) {
                try {
                    const res = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
                        refresh_token: refreshToken,
                    })
                    const newAccessToken = res.data.access_token
                    localStorage.setItem('access_token', newAccessToken)
                    if (res.data.refresh_token) {
                        localStorage.setItem('refresh_token', res.data.refresh_token)
                    }
                    originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
                    processQueue(null, newAccessToken)
                    return client(originalRequest)
                } catch (refreshError) {
                    processQueue(refreshError, null)
                    // Refresh failed — log out
                } finally {
                    isRefreshing = false
                }
            }

            // No refresh token or refresh failed — force logout
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            window.location.href = '/login'
        }

        return Promise.reject(error)
    },
)

export default client

