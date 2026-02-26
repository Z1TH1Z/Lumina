import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import CommandPalette from './CommandPalette'

export default function Layout() {
    return (
        <div className="flex min-h-screen bg-surface-900">
            <Sidebar />
            <main className="flex-1 overflow-hidden">
                <CommandPalette />
                <Outlet />
            </main>
        </div>
    )
}
