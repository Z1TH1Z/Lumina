import { Bot, User, BookOpen, AlertCircle } from 'lucide-react'

export default function ChatMessage({ message }) {
    const isUser = message.role === 'user'

    return (
        <div className={`flex gap-3 animate-slide-up ${isUser ? 'justify-end' : 'justify-start'}`}>
            {!isUser && (
                <div className="w-8 h-8 rounded-xl bg-primary-500/20 flex items-center justify-center shrink-0 mt-1">
                    <Bot className="w-4 h-4 text-primary-400" />
                </div>
            )}

            <div
                className={`max-w-[75%] lg:max-w-[85%] ${isUser
                    ? 'bg-primary-500/20 border border-primary-500/20 rounded-2xl rounded-tr-md'
                    : 'glass-card'
                    } p-4`}
            >
                <p className="text-sm shadow-sm whitespace-pre-wrap leading-relaxed">
                    {message.content}
                </p>

                {/* Warning */}
                {message.warning && (
                    <div className="mt-3 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                        <p className="text-xs text-amber-400">{message.warning}</p>
                    </div>
                )}

                {/* Citations */}
                {message.citations?.length > 0 && (
                    <div className="mt-3 space-y-1">
                        <p className="text-xs font-medium text-surface-200/40 flex items-center gap-1">
                            <BookOpen className="w-3 h-3" /> Sources
                        </p>
                        {message.citations.map((c, j) => (
                            <div key={j} className="text-xs text-surface-200/30 p-2 rounded-lg bg-white/5">
                                [Source {c.source_id}] Similarity: {(c.similarity * 100).toFixed(0)}%
                                {c.excerpt && <span className="block mt-1 text-surface-200/20">{c.excerpt.slice(0, 100)}...</span>}
                            </div>
                        ))}
                    </div>
                )}

                {/* Confidence Bar */}
                {message.confidence !== undefined && message.confidence > 0 && (
                    <div className="mt-2 flex items-center gap-2">
                        <div className="w-16 h-1 rounded-full bg-white/10 overflow-hidden">
                            <div
                                className={`h-full rounded-full ${message.confidence > 0.7 ? 'bg-emerald-500' : message.confidence > 0.4 ? 'bg-amber-500' : 'bg-rose-500'
                                    }`}
                                style={{ width: `${message.confidence * 100}%` }}
                            />
                        </div>
                        <span className="text-xs text-surface-200/30">
                            {(message.confidence * 100).toFixed(0)}% confidence
                        </span>
                    </div>
                )}
            </div>

            {isUser && (
                <div className="w-8 h-8 rounded-xl bg-white/10 flex items-center justify-center shrink-0 mt-1">
                    <User className="w-4 h-4 text-surface-200/60" />
                </div>
            )}
        </div>
    )
}
