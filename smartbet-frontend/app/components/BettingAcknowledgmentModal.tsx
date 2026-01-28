'use client'

import { useState } from 'react'
import { AlertTriangle, CheckCircle, X } from 'lucide-react'

interface BettingAcknowledgmentModalProps {
    isOpen: boolean
    onConfirm: () => void
    onClose: () => void
    language?: 'en' | 'ro'
}

export default function BettingAcknowledgmentModal({
    isOpen,
    onConfirm,
    onClose,
    language = 'en'
}: BettingAcknowledgmentModalProps) {
    const [acknowledged, setAcknowledged] = useState({
        entertainment: false,
        mayBeWrong: false,
        affordToLose: false
    })

    const allChecked = acknowledged.entertainment && acknowledged.mayBeWrong && acknowledged.affordToLose

    const handleConfirm = () => {
        if (allChecked) {
            // Store acknowledgment in session so we don't show it again in this session
            sessionStorage.setItem('betting_acknowledged', 'true')
            onConfirm()
        }
    }

    if (!isOpen) return null

    const text = {
        en: {
            title: 'Before You Continue',
            subtitle: 'Please acknowledge the following to use the betting calculator:',
            entertainment: 'I understand this is for entertainment and informational purposes only',
            mayBeWrong: 'I accept that predictions may be wrong and past performance doesn\'t guarantee future results',
            affordToLose: 'I will only bet money I can afford to lose',
            continue: 'Continue to Calculator',
            cancel: 'Cancel',
            helpLink: 'If you need help with gambling, visit our Responsible Gambling page'
        },
        ro: {
            title: 'Înainte să continuați',
            subtitle: 'Vă rugăm să confirmați următoarele pentru a utiliza calculatorul de pariuri:',
            entertainment: 'Înțeleg că este doar pentru divertisment și informare',
            mayBeWrong: 'Accept că predicțiile pot fi greșite și performanța trecută nu garantează rezultatele viitoare',
            affordToLose: 'Voi paria doar bani pe care îmi permit să îi pierd',
            continue: 'Continuă la Calculator',
            cancel: 'Anulează',
            helpLink: 'Dacă aveți nevoie de ajutor cu jocurile de noroc, vizitați pagina noastră de Joc Responsabil'
        }
    }

    const t = text[language]

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
                {/* Header */}
                <div className="bg-gradient-to-r from-amber-500 to-orange-500 p-6 text-white">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <AlertTriangle className="h-6 w-6" />
                            <h2 className="text-xl font-bold">{t.title}</h2>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1 hover:bg-white/20 rounded-lg transition-colors"
                        >
                            <X className="h-5 w-5" />
                        </button>
                    </div>
                    <p className="mt-2 text-sm opacity-90">{t.subtitle}</p>
                </div>

                {/* Checkboxes */}
                <div className="p-6 space-y-4">
                    <label className="flex items-start gap-3 cursor-pointer group">
                        <div className="relative mt-0.5">
                            <input
                                type="checkbox"
                                checked={acknowledged.entertainment}
                                onChange={(e) => setAcknowledged(prev => ({ ...prev, entertainment: e.target.checked }))}
                                className="sr-only peer"
                            />
                            <div className="w-5 h-5 border-2 border-gray-300 rounded peer-checked:border-green-500 peer-checked:bg-green-500 transition-colors flex items-center justify-center">
                                {acknowledged.entertainment && <CheckCircle className="h-4 w-4 text-white" />}
                            </div>
                        </div>
                        <span className="text-sm text-gray-700 group-hover:text-gray-900">{t.entertainment}</span>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer group">
                        <div className="relative mt-0.5">
                            <input
                                type="checkbox"
                                checked={acknowledged.mayBeWrong}
                                onChange={(e) => setAcknowledged(prev => ({ ...prev, mayBeWrong: e.target.checked }))}
                                className="sr-only peer"
                            />
                            <div className="w-5 h-5 border-2 border-gray-300 rounded peer-checked:border-green-500 peer-checked:bg-green-500 transition-colors flex items-center justify-center">
                                {acknowledged.mayBeWrong && <CheckCircle className="h-4 w-4 text-white" />}
                            </div>
                        </div>
                        <span className="text-sm text-gray-700 group-hover:text-gray-900">{t.mayBeWrong}</span>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer group">
                        <div className="relative mt-0.5">
                            <input
                                type="checkbox"
                                checked={acknowledged.affordToLose}
                                onChange={(e) => setAcknowledged(prev => ({ ...prev, affordToLose: e.target.checked }))}
                                className="sr-only peer"
                            />
                            <div className="w-5 h-5 border-2 border-gray-300 rounded peer-checked:border-green-500 peer-checked:bg-green-500 transition-colors flex items-center justify-center">
                                {acknowledged.affordToLose && <CheckCircle className="h-4 w-4 text-white" />}
                            </div>
                        </div>
                        <span className="text-sm text-gray-700 group-hover:text-gray-900">{t.affordToLose}</span>
                    </label>
                </div>

                {/* Actions */}
                <div className="p-6 pt-0 space-y-3">
                    <button
                        onClick={handleConfirm}
                        disabled={!allChecked}
                        className={`w-full py-3 px-4 rounded-xl font-semibold transition-all ${allChecked
                                ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600 shadow-lg'
                                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                            }`}
                    >
                        {t.continue}
                    </button>
                    <button
                        onClick={onClose}
                        className="w-full py-2 px-4 text-gray-600 hover:text-gray-800 text-sm font-medium transition-colors"
                    >
                        {t.cancel}
                    </button>
                </div>

                {/* Help Link */}
                <div className="px-6 pb-6">
                    <a
                        href="/responsible-gambling"
                        className="text-xs text-amber-600 hover:text-amber-800 hover:underline flex items-center justify-center gap-1"
                    >
                        {t.helpLink}
                    </a>
                </div>
            </div>
        </div>
    )
}
