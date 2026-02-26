import React, { useState } from 'react'
import { Sparkles, Bot, Loader2, Network } from 'lucide-react'
import { useChat } from '../hooks/useChat'
import ChatSidebar from '../components/chat/ChatSidebar'
import ChatMessage from '../components/chat/ChatMessage'
import ChatInput from '../components/chat/ChatInput'
import VectorGraph from '../components/VectorGraph'

export default function Chat() {
    const {
        sessions,
        currentSessionId,
        messages,
        input,
        setInput,
        loading,
        fetchingSessions,
        fetchingMessages,
        messagesEndRef,
        loadSession,
        startNewSession,
        archiveSession,
        sendMessage,
    } = useChat()

    const [showGraph, setShowGraph] = useState(false)

    // Quick action suggestions
    const suggestions = [
        'What are my top spending categories?',
        'Explain my recent anomalies',
        'Calculate compound interest for $10,000 at 7% for 5 years',
        'What does my cash flow look like?',
    ]

    return (
        <div className="flex h-screen max-h-screen bg-surface-950 overflow-hidden">
            <ChatSidebar
                sessions={sessions}
                currentSessionId={currentSessionId}
                fetchingSessions={fetchingSessions}
                startNewSession={startNewSession}
                loadSession={loadSession}
                archiveSession={archiveSession}
            />

            <div className="flex-1 flex overflow-hidden">
                {/* Main Chat Area */}
                <div className={`flex-1 flex flex-col page-container overflow-hidden ${showGraph ? 'border-r border-white/5 pr-4' : ''}`}>
                    <div className="page-header shrink-0 pb-4 border-b border-white/5 mb-4 flex justify-between items-center pr-2">
                        <div>
                            <h1 className="page-title flex items-center gap-2">
                                <Sparkles className="w-7 h-7 text-primary-400" />
                                AI Chat
                            </h1>
                            <p className="page-subtitle">Ask questions about your finances using RAG-powered AI</p>
                        </div>

                        <button
                            onClick={() => setShowGraph(!showGraph)}
                            className={`px-3 py-2 rounded-xl border flex gap-2 items-center text-sm transition-all shadow-sm shrink-0 ${showGraph
                                ? 'bg-primary-500/20 border-primary-500/50 text-primary-300 shadow-primary-500/10'
                                : 'bg-surface-800 border-white/10 text-surface-300 hover:text-white hover:bg-surface-700'
                                }`}
                        >
                            <Network className="w-4 h-4" />
                            {showGraph ? 'Close Visualizer' : 'Visualize Brain'}
                        </button>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2 scrollbar-thin">
                        {fetchingMessages ? (
                            <div className="flex items-center justify-center h-full">
                                <Loader2 className="w-8 h-8 text-primary-500/50 animate-spin" />
                            </div>
                        ) : (
                            <>
                                {messages.map((msg, i) => (
                                    <ChatMessage key={i} message={msg} />
                                ))}

                                {loading && (
                                    <div className="flex gap-3 animate-slide-up">
                                        <div className="w-8 h-8 rounded-xl bg-primary-500/20 flex items-center justify-center shrink-0">
                                            <Bot className="w-4 h-4 text-primary-400" />
                                        </div>
                                        <div className="glass-card p-4">
                                            <div className="flex items-center gap-2">
                                                <Loader2 className="w-4 h-4 text-primary-400 animate-spin" />
                                                <span className="text-sm text-surface-200/50">Thinking...</span>
                                            </div>
                                        </div>
                                    </div>
                                )}
                                <div ref={messagesEndRef} />
                            </>
                        )}
                    </div>

                    {/* Suggestions */}
                    {messages.length <= 1 && !loading && (
                        <div className="flex flex-wrap gap-2 mb-4">
                            {suggestions.map((s, i) => (
                                <button
                                    key={i}
                                    onClick={() => setInput(s)}
                                    className="px-3 py-2 rounded-xl text-xs bg-white/5 border border-white/10 text-surface-200/60 hover:bg-white/10 hover:text-white transition-all"
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                    )}

                    <ChatInput
                        input={input}
                        setInput={setInput}
                        sendMessage={sendMessage}
                        isLoading={loading || fetchingMessages}
                    />
                </div>

                {showGraph && (
                    <div className="w-[45%] h-full p-4 pl-0 bg-surface-950 flex flex-col animate-slide-left border-l border-white/5 shrink-0">
                        <VectorGraph />
                    </div>
                )}
            </div>
        </div>
    )
}

