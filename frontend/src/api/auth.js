import client from './client'

export const authApi = {
    fetchMe: async () => {
        const res = await client.get('/api/v1/auth/me')
        return res.data
    },

    login: async (email, password) => {
        const res = await client.post('/api/v1/auth/login', { email, password })
        return res.data
    },

    register: async (email, username, password, fullName) => {
        const res = await client.post('/api/v1/auth/register', {
            email,
            username,
            password,
            full_name: fullName,
        })
        return res.data
    },

    updateProfile: async (updates) => {
        const res = await client.put('/api/v1/auth/me', updates)
        return res.data
    }
}
