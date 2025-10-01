'use client'

import { useState, useEffect } from 'react'
import { Calendar, Clock, Trophy, TrendingUp } from 'lucide-react'
import { leagues } from '@/lib/mockData'

interface Countdown {
  days: number
  hours: number
  minutes: number
  seconds: number
}

export default function ComingSoonPage() {
  const [countdowns, setCountdowns] = useState<{ [key: string]: Countdown }>({})

  // Mock season start dates (in real app, these would come from API)
  const seasonStarts = {
    'Premier League': new Date('2024-08-17T15:00:00'),
    'La Liga': new Date('2024-08-18T21:00:00'),
    'Serie A': new Date('2024-08-19T20:45:00'),
    'Bundesliga': new Date('2024-08-20T20:30:00'),
    'Ligue 1': new Date('2024-08-21T21:00:00')
  }

  useEffect(() => {
    const calculateCountdown = () => {
      const now = new Date()
      const newCountdowns: { [key: string]: Countdown } = {}

      Object.entries(seasonStarts).forEach(([league, startDate]) => {
        const diff = startDate.getTime() - now.getTime()
        
        if (diff > 0) {
          const days = Math.floor(diff / (1000 * 60 * 60 * 24))
          const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
          const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
          const seconds = Math.floor((diff % (1000 * 60)) / 1000)

          newCountdowns[league] = { days, hours, minutes, seconds }
        } else {
          newCountdowns[league] = { days: 0, hours: 0, minutes: 0, seconds: 0 }
        }
      })

      setCountdowns(newCountdowns)
    }

    calculateCountdown()
    const interval = setInterval(calculateCountdown, 1000)

    return () => clearInterval(interval)
  }, [])

  const getLeagueFlag = (league: string) => {
    const flags: { [key: string]: string } = {
      'Premier League': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
      'La Liga': '🇪🇸',
      'Serie A': '🇮🇹',
      'Bundesliga': '🇩🇪',
      'Ligue 1': '🇫🇷'
    }
    return flags[league] || '⚽'
  }

  const formatCountdown = (countdown: Countdown) => {
    if (countdown.days === 0 && countdown.hours === 0 && countdown.minutes === 0 && countdown.seconds === 0) {
      return 'Season Started!'
    }
    return `${countdown.days}d ${countdown.hours}h ${countdown.minutes}m ${countdown.seconds}s`
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <div className="flex justify-center mb-6">
          <Calendar className="h-16 w-16 text-primary-600" />
        </div>
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
          Coming Soon
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          Real matches will appear once the season resumes. 
          Our AI models are ready to provide predictions for live matches across all major European leagues.
        </p>
      </div>

      {/* Current Status */}
      <div className="card mb-8">
        <div className="text-center">
          <TrendingUp className="h-12 w-12 text-primary-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Offseason Status
          </h2>
          <p className="text-gray-600 mb-6">
            All major European leagues are currently in their offseason break. 
            Our prediction models are being updated with the latest data and will be ready 
            for the new season with improved accuracy.
          </p>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary-600">5</div>
              <div className="text-gray-600">Leagues Ready</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-success-600">24/7</div>
              <div className="text-gray-600">Model Training</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-warning-600">100%</div>
              <div className="text-gray-600">Uptime</div>
            </div>
          </div>
        </div>
      </div>

      {/* Season Countdowns */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
          Season Start Countdowns
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {leagues.map((league) => (
            <div key={league.id} className="border border-gray-200 rounded-lg p-6 text-center">
              <div className="text-3xl mb-3">{getLeagueFlag(league.name)}</div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {league.name}
              </h3>
              <div className="text-sm text-gray-600 mb-4">
                {league.country}
              </div>
              
              <div className="mb-4">
                <div className="text-2xl font-bold text-primary-600 mb-1">
                  {formatCountdown(countdowns[league.name] || { days: 0, hours: 0, minutes: 0, seconds: 0 })}
                </div>
                <div className="text-xs text-gray-500">
                  until season start
                </div>
              </div>

              <div className="flex items-center justify-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${
                  league.status === 'PRODUCTION' ? 'bg-success-500' : 'bg-warning-500'
                }`}></div>
                <span className="text-xs text-gray-600">
                  {league.status} Model
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* What to Expect */}
      <div className="grid md:grid-cols-2 gap-6 mt-8">
        <div className="card">
          <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
            <Trophy className="h-5 w-5 mr-2" />
            Live Predictions
          </h3>
          <ul className="space-y-2 text-gray-600">
            <li>• Real-time match predictions</li>
            <li>• Live confidence scores</li>
            <li>• Expected value calculations</li>
            <li>• SHAP feature explanations</li>
            <li>• Betting recommendations</li>
          </ul>
        </div>

        <div className="card">
          <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
            <Clock className="h-5 w-5 mr-2" />
            Model Updates
          </h3>
          <ul className="space-y-2 text-gray-600">
            <li>• Continuous model training</li>
            <li>• Performance optimization</li>
            <li>• New feature integration</li>
            <li>• Market efficiency analysis</li>
            <li>• Risk assessment improvements</li>
          </ul>
        </div>
      </div>

      {/* CTA */}
      <div className="text-center mt-8">
        <div className="card">
          <h3 className="text-xl font-bold text-gray-900 mb-4">
            Ready to Get Started?
          </h3>
          <p className="text-gray-600 mb-6">
            Explore our sandbox to test predictions with mock data, 
            or check out our current model performance across all leagues.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="/sandbox"
              className="btn-primary"
            >
              Try Sandbox
            </a>
            <a
              href="/predictions"
              className="btn-secondary"
            >
              View Mock Predictions
            </a>
          </div>
        </div>
      </div>
    </div>
  )
} 