import client from './client'

export const chatApi = {
    fetchSessions: async () => {
        const res = await client.get('/api/v1/rag/sessions')
        return res.data
    },

    loadSessionMessages: async (sessionId) => {
        const res = await client.get(`/api/v1/rag/sessions/${sessionId}/messages`)
        return res.data
    },

    createSession: async (title) => {
        const res = await client.post('/api/v1/rag/sessions', { title })
        return res.data
    },

    archiveSession: async (sessionId) => {
        const res = await client.put(`/api/v1/rag/sessions/${sessionId}/archive`)
        return res.data
    },

    queryChat: async (sessionId, message) => {
        const res = await client.post('/api/v1/rag/query', { session_id: sessionId, message })
        return res.data
    }
}
