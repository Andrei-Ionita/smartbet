'use client'

import { AlertTriangle, Shield, Info } from 'lucide-react'

interface TrapAlertProps {
  trapLevel: 'low' | 'medium' | 'high' | 'extreme'
  trapScore: number
  alertMessage: string
  recommendation: string
  className?: string
}

export default function TrapAlert({ 
  trapLevel, 
  trapScore, 
  alertMessage, 
  recommendation, 
  className = '' 
}: TrapAlertProps) {
  
  const getAlertConfig = (level: string) => {
    switch (level) {
      case 'extreme':
        return {
          icon: '🚨',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          textColor: 'text-red-800',
          iconColor: 'text-red-600',
          title: 'EXTREME TRAP RISK'
        }
      case 'high':
        return {
          icon: '⚠️',
          bgColor: 'bg-orange-50',
          borderColor: 'border-orange-200',
          textColor: 'text-orange-800',
          iconColor: 'text-orange-600',
          title: 'HIGH TRAP RISK'
        }
      case 'medium':
        return {
          icon: '⚡',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          textColor: 'text-yellow-800',
          iconColor: 'text-yellow-600',
          title: 'MEDIUM TRAP RISK'
        }
      case 'low':
        return {
          icon: '✅',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          textColor: 'text-green-800',
          iconColor: 'text-green-600',
          title: 'LOW TRAP RISK'
        }
      default:
        return {
          icon: 'ℹ️',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          textColor: 'text-gray-800',
          iconColor: 'text-gray-600',
          title: 'SENTIMENT INFO'
        }
    }
  }

  const config = getAlertConfig(trapLevel)

  // Don't show low risk alerts to keep UI clean
  if (trapLevel === 'low') {
    return null
  }

  return (
    <div className={`rounded-lg border p-4 ${config.bgColor} ${config.borderColor} ${className}`}>
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="flex-shrink-0">
          <span className="text-2xl">{config.icon}</span>
        </div>
        
        {/* Content */}
        <div className="flex-1">
          {/* Header */}
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className={`h-4 w-4 ${config.iconColor}`} />
            <span className={`font-semibold text-sm ${config.textColor}`}>
              {config.title}
            </span>
            <div className={`ml-auto px-2 py-1 rounded-full text-xs font-bold ${config.bgColor} ${config.textColor} border ${config.borderColor}`}>
              {trapScore}/10
            </div>
          </div>
          
          {/* Alert Message */}
          <div className={`text-sm font-medium mb-2 ${config.textColor}`}>
            {alertMessage}
          </div>
          
          {/* Recommendation */}
          <div className={`text-sm ${config.textColor} opacity-90`}>
            {recommendation}
          </div>
          
          {/* Educational Note */}
          <div className="mt-3 flex items-start gap-2">
            <Info className={`h-3 w-3 mt-0.5 ${config.iconColor} flex-shrink-0`} />
            <div className={`text-xs ${config.textColor} opacity-75`}>
              <strong>What is a trap game?</strong> A match where public sentiment is heavily skewed compared to statistical predictions, potentially indicating value opportunities or dangerous betting situations.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
