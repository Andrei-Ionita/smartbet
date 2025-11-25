'use client'

import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { User, Shield, Key, LogOut, Trash2, AlertTriangle, Save } from 'lucide-react'
import { useRouter } from 'next/navigation'

export default function ProfilePage() {
    const { user, logout } = useAuth()
    const router = useRouter()
    const [riskProfile, setRiskProfile] = useState('balanced')
    const [isSaving, setIsSaving] = useState(false)

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
                                            {profile === 'conservative' ? 'Lower stakes, safer growth (1-2%)' :
                                                profile === 'balanced' ? 'Standard Kelly sizing (2-4%)' :
                                                    'Higher variance, max growth (4-6%)'}
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
                        <button className="text-primary-600 font-medium hover:text-primary-700 hover:underline">
                            Change Password
                        </button>
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
                        <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium flex items-center gap-2">
                            <Trash2 className="h-4 w-4" />
                            Delete Account
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
