import { Brain } from 'lucide-react'

export default function EmptyState({ message }) {
    return (
        <div className="flex flex-col items-center justify-center h-64 text-surface-200/30">
            <Brain className="w-12 h-12 mb-3" />
            <p className="text-sm">{message}</p>
        </div>
    )
}
