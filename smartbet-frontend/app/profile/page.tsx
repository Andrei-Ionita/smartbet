'use client'

import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { User, Shield, Key, LogOut, Trash2, AlertTriangle, Save } from 'lucide-react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function ProfilePage() {
    const { user, logout, deleteAccount } = useAuth()
    const router = useRouter()
    const [riskProfile, setRiskProfile] = useState('balanced')
    const [isSaving, setIsSaving] = useState(false)
    const [deleteOpen, setDeleteOpen] = useState(false)
    const [deletePassword, setDeletePassword] = useState('')
    const [deleteError, setDeleteError] = useState('')
    const [isDeleting, setIsDeleting] = useState(false)

    if (!user) {
        if (typeof window !== 'undefined') {
            router.push('/login')
        }
        return null
    }

    const handleSave = async () => {
        setIsSaving(true)
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000))
        setIsSaving(false)
    }

    const handleLogout = () => {
        logout()
        router.push('/')
    }

    const handleDelete = async (event: React.FormEvent) => {
        event.preventDefault()
        setDeleteError('')
        setIsDeleting(true)
        try {
            await deleteAccount(deletePassword)
        } catch (error) {
            setDeleteError(error instanceof Error ? error.message : 'Account deletion failed.')
            setIsDeleting(false)
        }
    }

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Account Settings</h1>
                <p className="text-gray-600">Manage your profile and preferences</p>
            </div>

            <div className="grid gap-8">
                {/* Profile Summary */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="p-6 border-b border-gray-200 bg-gray-50">
                        <div className="flex items-center gap-4">
                            <div className="h-16 w-16 bg-primary-100 rounded-full flex items-center justify-center text-primary-600">
                                <User className="h-8 w-8" />
                            </div>
                            <div>
                                <h2 className="text-xl font-bold text-gray-900">{user.username}</h2>
                                <p className="text-gray-600">{user.email || 'No email linked'}</p>
                            </div>
                        </div>
                    </div>

                    <div className="p-6 grid gap-6 md:grid-cols-2">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                            <input
                                type="text"
                                value={user.username}
                                disabled
                                className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-500 cursor-not-allowed"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                            <input
                                type="email"
                                value={user.email || ''}
                                disabled
                                className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-500 cursor-not-allowed"
                            />
                        </div>
                    </div>
                </div>

                {/* Risk Profile Settings */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                    <div className="p-6 border-b border-gray-200">
                        <div className="flex items-center gap-2 mb-1">
                            <Shield className="h-5 w-5 text-primary-600" />
                            <h2 className="text-lg font-bold text-gray-900">Betting Preferences</h2>
                        </div>
                        <p className="text-sm text-gray-600">Customize how we calculate your recommended stakes</p>
                    </div>

                    <div className="p-6">
                        <div className="mb-6">
                            <label className="block text-sm font-medium text-gray-700 mb-2">Risk Profile</label>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {['conservative', 'balanced', 'aggressive'].map((profile) => (
                                    <button
                                        key={profile}
                                        onClick={() => setRiskProfile(profile)}
                                        className={`p-4 rounded-xl border-2 text-left transition-all ${riskProfile === profile
                                                ? 'border-primary-500 bg-primary-50 ring-1 ring-primary-500'
                                                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                            }`}
                                    >
                                        <div className="font-semibold text-gray-900 capitalize mb-1">{profile}</div>
                                        <div className="text-xs text-gray-500">
                                            {/* No growth promises and no Kelly endorsement here —
                                                these are stake CAPS the user chooses, nothing more. */}
                                            {profile === 'conservative' ? 'Lower stake caps (1-2% of bankroll)' :
                                                profile === 'balanced' ? 'Moderate stake caps (2-4% of bankroll)' :
                                                    'Higher stake caps (4-6% of bankroll) — higher variance'}
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="flex justify-end">
                            <button
                                onClick={handleSave}
                                disabled={isSaving}
                                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
                            >
                                {isSaving ? (
                                    <>Saving...</>
                                ) : (
                                    <>
                                        <Save className="h-4 w-4" />
                                        Save Preferences
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Security */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                    <div className="p-6 border-b border-gray-200">
                        <div className="flex items-center gap-2 mb-1">
                            <Key className="h-5 w-5 text-gray-600" />
                            <h2 className="text-lg font-bold text-gray-900">Security</h2>
                        </div>
                        <p className="text-sm text-gray-600">Manage your password and account access</p>
                    </div>

                    <div className="p-6">
                        <Link
                            href="/forgot-password"
                            className="inline-flex min-h-[44px] items-center text-primary-600 font-medium hover:text-primary-700 hover:underline"
                        >
                            Change Password
                        </Link>
                    </div>
                </div>

                {/* Danger Zone */}
                <div className="bg-red-50 rounded-xl border border-red-200 p-6">
                    <h2 className="text-lg font-bold text-red-900 mb-2 flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5" />
                        Danger Zone
                    </h2>
                    <p className="text-sm text-red-700 mb-4">
                        Once you delete your account, there is no going back. Please be certain.
                    </p>
                    <div className="flex gap-4">
                        <button
                            onClick={handleLogout}
                            className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium flex items-center gap-2"
                        >
                            <LogOut className="h-4 w-4" />
                            Log Out
                        </button>
                        <button
                            type="button"
                            onClick={() => setDeleteOpen((open) => !open)}
                            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium flex items-center gap-2"
                        >
                            <Trash2 className="h-4 w-4" />
                            Delete Account
                        </button>
                    </div>
                    {deleteOpen && (
                        <form onSubmit={handleDelete} className="mt-5 max-w-lg rounded-xl border border-red-300 bg-white p-4">
                            <label htmlFor="delete-password" className="block text-sm font-semibold text-red-900">
                                Confirm your password
                            </label>
                            <p className="mt-1 text-xs leading-relaxed text-red-700">
                                This permanently deletes your account and associated bankroll data. It cannot be undone.
                            </p>
                            <input
                                id="delete-password"
                                type="password"
                                autoComplete="current-password"
                                required
                                value={deletePassword}
                                onChange={(event) => setDeletePassword(event.target.value)}
                                className="mt-3 min-h-[44px] w-full rounded-lg border border-red-300 px-3 text-gray-900 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-200"
                            />
                            {deleteError && <p role="alert" className="mt-2 text-sm text-red-700">{deleteError}</p>}
                            <div className="mt-4 flex flex-wrap gap-3">
                                <button
                                    type="submit"
                                    disabled={isDeleting}
                                    className="min-h-[44px] rounded-lg bg-red-700 px-4 font-semibold text-white hover:bg-red-800 disabled:opacity-50"
                                >
                                    {isDeleting ? 'Deleting…' : 'Permanently delete my account'}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => { setDeleteOpen(false); setDeletePassword(''); setDeleteError('') }}
                                    className="min-h-[44px] rounded-lg border border-gray-300 px-4 font-semibold text-gray-700 hover:bg-gray-50"
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    )}
                </div>
            </div>
        </div>
    )
}
