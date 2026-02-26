import { NavLink, useLocation } from 'react-router-dom'
import {
    LayoutDashboard,
    FileText,
    CreditCard,
    AlertTriangle,
    TrendingUp,
    MessageSquare,
    Wrench,
    Settings,
    LogOut,
    Brain,
    ChevronLeft,
    ChevronRight,
} from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/documents', icon: FileText, label: 'Documents' },
    { path: '/transactions', icon: CreditCard, label: 'Transactions' },
    { path: '/anomalies', icon: AlertTriangle, label: 'Anomalies' },
    { path: '/forecasting', icon: TrendingUp, label: 'Forecasting' },
    { path: '/chat', icon: MessageSquare, label: 'AI Chat' },
    { path: '/tools', icon: Wrench, label: 'Tools' },
]

export default function Sidebar() {
    const [collapsed, setCollapsed] = useState(false)
    const { user, logout } = useAuth()
    const location = useLocation()

    return (
        <aside
            className={`${collapsed ? 'w-20' : 'w-72'
                } h-screen sticky top-0 flex flex-col border-r border-white/5 bg-surface-900/80 backdrop-blur-xl transition-all duration-300`}
        >
            {/* Logo */}
            <div className="flex items-center gap-3 p-6 border-b border-white/5">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shrink-0">
                    <Brain className="w-5 h-5 text-white" />
                </div>
                {!collapsed && (
                    <div className="animate-fade-in">
                        <h1 className="text-sm font-bold gradient-text">AI Financial</h1>
                        <p className="text-[10px] text-surface-200/40 font-medium tracking-wider uppercase">Copilot</p>
                    </div>
                )}
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                {navItems.map(({ path, icon: Icon, label }) => (
                    <NavLink
                        key={path}
                        to={path}
                        className={({ isActive }) =>
                            `nav-link ${isActive ? 'nav-link-active' : ''}`
                        }
                        title={collapsed ? label : undefined}
                    >
                        <Icon className="w-5 h-5 shrink-0" />
                        {!collapsed && <span>{label}</span>}
                    </NavLink>
                ))}
            </nav>

            {/* Footer */}
            <div className="p-4 border-t border-white/5 space-y-2">
                <NavLink
                    to="/settings"
                    className={({ isActive }) =>
                        `nav-link ${isActive ? 'nav-link-active' : ''}`
                    }
                    title={collapsed ? 'Settings' : undefined}
                >
                    <Settings className="w-5 h-5 shrink-0" />
                    {!collapsed && <span>Settings</span>}
                </NavLink>

                {user && (
                    <button onClick={logout} className="nav-link w-full text-rose-400/70 hover:text-rose-400">
                        <LogOut className="w-5 h-5 shrink-0" />
                        {!collapsed && <span>Log Out</span>}
                    </button>
                )}

                {/* Collapse toggle */}
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="nav-link w-full justify-center mt-2"
                >
                    {collapsed ? (
                        <ChevronRight className="w-4 h-4" />
                    ) : (
                        <>
                            <ChevronLeft className="w-4 h-4" />
                            <span className="text-xs">Collapse</span>
                        </>
                    )}
                </button>
            </div>
        </aside>
    )
}
