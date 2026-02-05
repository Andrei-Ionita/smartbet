import NextAuth, { NextAuthOptions } from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'
import GoogleProvider from 'next-auth/providers/google'

// User type with subscription tier
interface User {
    id: string
    email: string
    name: string
    tier: 'free' | 'pro'
    createdAt: Date
}

// In production, this would be your database
// For now, we'll use a simple in-memory store + localStorage sync
const users: Map<string, User & { password: string }> = new Map()

export const authOptions: NextAuthOptions = {
    providers: [
        // Email/Password login
        CredentialsProvider({
            name: 'credentials',
            credentials: {
                email: { label: 'Email', type: 'email' },
                password: { label: 'Password', type: 'password' },
                action: { label: 'Action', type: 'text' } // 'login' or 'register'
            },
            async authorize(credentials) {
                if (!credentials?.email || !credentials?.password) {
                    throw new Error('Email and password are required')
                }

                const email = credentials.email.toLowerCase()
                const action = credentials.action || 'login'

                if (action === 'register') {
                    // Check if user already exists
                    if (users.has(email)) {
                        throw new Error('User already exists')
                    }

                    // Create new user
                    const newUser: User & { password: string } = {
                        id: crypto.randomUUID(),
                        email,
                        name: email.split('@')[0],
                        password: credentials.password, // In production, hash this!
                        tier: 'free', // All new users start on free tier
                        createdAt: new Date()
                    }
                    users.set(email, newUser)

                    return {
                        id: newUser.id,
                        email: newUser.email,
                        name: newUser.name,
                        tier: newUser.tier
                    }
                } else {
                    // Login
                    const user = users.get(email)
                    if (!user) {
                        throw new Error('No user found with this email')
                    }

                    if (user.password !== credentials.password) {
                        throw new Error('Invalid password')
                    }

                    return {
                        id: user.id,
                        email: user.email,
                        name: user.name,
                        tier: user.tier
                    }
                }
            }
        }),
        // Google OAuth (optional - add credentials later)
        ...(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET
            ? [
                GoogleProvider({
                    clientId: process.env.GOOGLE_CLIENT_ID,
                    clientSecret: process.env.GOOGLE_CLIENT_SECRET
                })
            ]
            : [])
    ],
    callbacks: {
        async jwt({ token, user }) {
            // Add tier to JWT token
            if (user) {
                token.id = user.id
                token.tier = (user as any).tier || 'free'
            }
            return token
        },
        async session({ session, token }) {
            // Add tier to session
            if (session.user) {
                (session.user as any).id = token.id
                    (session.user as any).tier = token.tier || 'free'
            }
            return session
        }
    },
    pages: {
        signIn: '/login',
        signOut: '/',
        error: '/login'
    },
    session: {
        strategy: 'jwt',
        maxAge: 30 * 24 * 60 * 60 // 30 days
    },
    secret: process.env.NEXTAUTH_SECRET || 'development-secret-change-in-production'
}

const handler = NextAuth(authOptions)
export { handler as GET, handler as POST }
