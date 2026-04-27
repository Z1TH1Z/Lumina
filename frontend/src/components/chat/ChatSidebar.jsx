import { Plus, Loader2, MessageSquare, Clock, Trash2 } from 'lucide-react'

export default function ChatSidebar({
    sessions,
    currentSessionId,
    fetchingSessions,
    startNewSession,
    loadSession,
    archiveSession
}) {
    return (
        <div className="w-64 border-r border-white/5 bg-surface-900 flex flex-col shrink-0">
            <div className="p-4 border-b border-white/5 shrink-0">
                <button
                    onClick={startNewSession}
                    className="w-full btn-primary flex items-center justify-center gap-2"
                >
                    <Plus className="w-4 h-4" />
                    New Chat
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1 scrollbar-hide">
                {fetchingSessions ? (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="w-5 h-5 text-surface-200/30 animate-spin" />
                    </div>
                ) : sessions.length === 0 ? (
                    <div className="text-center py-8">
                        <MessageSquare className="w-8 h-8 text-surface-200/20 mx-auto mb-2" />
                        <p className="text-sm text-surface-200/40">No previous chats</p>
                    </div>
                ) : (
                    sessions.map(session => (
                        <div
                            key={session.id}
                            onClick={() => loadSession(session.id)}
                            className={`w-full text-left p-3 rounded-xl transition-all flex items-center gap-3 group cursor-pointer ${currentSessionId === session.id
                                ? 'bg-primary-500/10 border border-primary-500/20'
                                : 'hover:bg-white/5 border border-transparent'
                                }`}
                        >
                            <MessageSquare className={`w-4 h-4 shrink-0 ${currentSessionId === session.id ? 'text-primary-400' : 'text-surface-200/40'}`} />
                            <div className="truncate text-sm flex-1">
                                <span className={currentSessionId === session.id ? 'text-primary-50' : 'text-surface-200'}>
                                    {session.title}
                                </span>
                                <div className="text-xs text-surface-200/40 flex items-center gap-1 mt-1">
                                    <Clock className="w-3 h-3" />
                                    {new Date(session.updated_at).toLocaleDateString()}
                                </div>
                            </div>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    archiveSession(e, session.id);
                                }}
                                className="p-1 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-rose-500/20 text-surface-200/30 hover:text-rose-400 transition-all shrink-0"
                                title="Archive chat"
                            >
                                <Trash2 className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}
