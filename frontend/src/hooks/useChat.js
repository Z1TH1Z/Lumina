import { useState, useEffect, useRef } from 'react'
import { chatApi } from '../api/chat'

const DEFAULT_WELCOME_MESSAGE = {
    role: 'assistant',
    content: 'Hello! I\'m your AI Financial Copilot. Ask me anything about your financial documents, spending patterns, or use financial tools. I use RAG to answer questions based on your uploaded documents.',
}

export function useChat() {
    const [sessions, setSessions] = useState([])
    const [currentSessionId, setCurrentSessionId] = useState(null)
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [fetchingSessions, setFetchingSessions] = useState(true)
    const [fetchingMessages, setFetchingMessages] = useState(false)
    const messagesEndRef = useRef(null)

    useEffect(() => {
        const fetchSessions = async () => {
            try {
                const data = await chatApi.fetchSessions()
                setSessions(data)
                if (data.length > 0) {
                    loadSession(data[0].id)
                } else {
                    setMessages([DEFAULT_WELCOME_MESSAGE])
                }
            } catch (err) {
                console.error('Failed to fetch sessions:', err)
                setMessages([DEFAULT_WELCOME_MESSAGE])
            } finally {
                setFetchingSessions(false)
            }
        }
        fetchSessions()
    }, [])

    const loadSession = async (sessionId) => {
        setCurrentSessionId(sessionId)
        setFetchingMessages(true)
        try {
            const data = await chatApi.loadSessionMessages(sessionId)
            const formatted = data.map(m => ({
                role: m.role,
                content: m.content,
                citations: m.sources_json ? JSON.parse(m.sources_json) : undefined
            }))
            if (formatted.length === 0) {
                setMessages([DEFAULT_WELCOME_MESSAGE])
            } else {
                setMessages(formatted)
            }
        } catch (err) {
            console.error('Failed to fetch messages:', err)
        } finally {
            setFetchingMessages(false)
        }
    }

    const startNewSession = () => {
        setCurrentSessionId(null)
        setMessages([DEFAULT_WELCOME_MESSAGE])
        setInput('')
    }

    const archiveSession = async (e, sessionId) => {
        e.stopPropagation()
        try {
            await chatApi.archiveSession(sessionId)
            setSessions(prev => prev.filter(s => s.id !== sessionId))
            if (currentSessionId === sessionId) {
                setCurrentSessionId(null)
                setMessages([DEFAULT_WELCOME_MESSAGE])
            }
        } catch (err) {
            console.error('Failed to archive session:', err)
        }
    }

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const sendMessage = async (e) => {
        if (e) e.preventDefault()
        if (!input.trim() || loading) return

        const userMessage = input.trim()
        setInput('')
        setMessages(prev => [...prev, { role: 'user', content: userMessage }])
        setLoading(true)

        try {
            let sessionId = currentSessionId

            if (!sessionId) {
                const sessionData = await chatApi.createSession(userMessage.slice(0, 30) + "...")
                sessionId = sessionData.id
                setCurrentSessionId(sessionId)
                setSessions(prev => [sessionData, ...prev])
            }

            const data = await chatApi.queryChat(sessionId, userMessage)
            const assistantContent = data.answer
            const warning = data.hallucination_warning || null

            setMessages(prev => [
                ...prev,
                {
                    role: 'assistant',
                    content: assistantContent,
                    citations: data.citations,
                    confidence: data.confidence,
                    warning,
                },
            ])
        } catch (err) {
            let errorMsg = 'Sorry, I encountered an error processing your request. Please try again.'
            if (err.response?.data?.detail) {
                errorMsg = typeof err.response.data.detail === 'string'
                    ? err.response.data.detail
                    : JSON.stringify(err.response.data.detail)
            }
            setMessages(prev => [
                ...prev,
                { role: 'assistant', content: errorMsg, isError: true },
            ])
        } finally {
            setLoading(false)
        }
    }

    return {
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
    }
}
