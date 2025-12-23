'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { translations, Language, Resources } from '../locales/translations'

interface LanguageContextType {
    language: Language
    setLanguage: (lang: Language) => void
    t: (path: string) => string
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export function LanguageProvider({ children }: { children: React.ReactNode }) {
    const [language, setLanguage] = useState<Language>('en')

    useEffect(() => {
        // 1. Check local storage
        const savedLang = localStorage.getItem('smartbet-lang') as Language

        if (savedLang && (savedLang === 'en' || savedLang === 'ro')) {
            setLanguage(savedLang)
        } else {
            // 2. Check browser language
            const browserLang = navigator.language.toLowerCase()
            if (browserLang.startsWith('ro')) {
                setLanguage('ro')
            }
        }
    }, [])

    const handleSetLanguage = (lang: Language) => {
        setLanguage(lang)
        localStorage.setItem('smartbet-lang', lang)
    }

    // Helper to access nested keys like 'nav.home'
    const t = (path: string): string => {
        const keys = path.split('.')
        let current: any = translations[language]

        for (const key of keys) {
            if (current[key] === undefined) {
                console.warn(`Translation missing for key: ${path} in language: ${language}`)
                return path
            }
            current = current[key]
        }

        return current as string
    }

    return (
        <LanguageContext.Provider value={{ language, setLanguage: handleSetLanguage, t }}>
            {children}
        </LanguageContext.Provider>
    )
}

export function useLanguage() {
    const context = useContext(LanguageContext)
    if (context === undefined) {
        throw new Error('useLanguage must be used within a LanguageProvider')
    }
    return context
}
