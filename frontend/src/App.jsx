import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Documents from './pages/Documents'
import Transactions from './pages/Transactions'
import Anomalies from './pages/Anomalies'
import Forecasting from './pages/Forecasting'
import Chat from './pages/Chat'
import Tools from './pages/Tools'
import Settings from './pages/Settings'

function ProtectedRoute({ children }) {
    const { isAuthenticated, loading } = useAuth()

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-surface-900">
                <div className="w-10 h-10 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
            </div>
        )
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />
    }

    return children
}

export default function App() {
    return (
        <Routes>
            <Route path="/login" element={<Login />} />
            <Route
                path="/"
                element={
                    <ProtectedRoute>
                        <Layout />
                    </ProtectedRoute>
                }
            >
                <Route index element={<Dashboard />} />
                <Route path="documents" element={<Documents />} />
                <Route path="transactions" element={<Transactions />} />
                <Route path="anomalies" element={<Anomalies />} />
                <Route path="forecasting" element={<Forecasting />} />
                <Route path="chat" element={<Chat />} />
                <Route path="tools" element={<Tools />} />
                <Route path="settings" element={<Settings />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    )
}
