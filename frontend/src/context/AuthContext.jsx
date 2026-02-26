import { createContext, useContext, useState, useEffect } from 'react'
import client from '../api/client'

import { authApi } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)
    const [isAuthenticated, setIsAuthenticated] = useState(false)

    useEffect(() => {
        const token = localStorage.getItem('access_token')
        if (token) {
            fetchUser()
        } else {
            setLoading(false)
        }
    }, [])

    const fetchUser = async () => {
        try {
            const data = await authApi.fetchMe()
            setUser(data)
            setIsAuthenticated(true)
        } catch {
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            setIsAuthenticated(false)
        } finally {
            setLoading(false)
        }
    }

    const login = async (email, password) => {
        const data = await authApi.login(email, password)
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        setIsAuthenticated(true)
        await fetchUser()
        return data
    }

    const register = async (email, username, password, fullName) => {
        const data = await authApi.register(email, username, password, fullName)
        return data
    }

    const logout = () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setUser(null)
        setIsAuthenticated(false)
    }

    const updateProfile = async (updates) => {
        const data = await authApi.updateProfile(updates)
        setUser(data)
        return data
    }

    return (
        <AuthContext.Provider
            value={{ user, loading, isAuthenticated, login, register, logout, updateProfile }}
        >
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) throw new Error('useAuth must be used within AuthProvider')
    return context
}
