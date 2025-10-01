"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { 
  Home, 
  BarChart3, 
  Zap, 
  Activity,
  Star
} from 'lucide-react';

const Navigation: React.FC = () => {
  const pathname = usePathname();
  
  const navItems = [
    {
      href: '/',
      label: 'Home',
      icon: Home
    },
    {
      href: '/dashboard',
      label: 'Dashboard',
      icon: BarChart3
    },
    {
      href: '/predictions',
      label: 'Predictions',
      icon: Zap
    },
    {
      href: '/live-predictions',
      label: 'Live Predictions',
      icon: Activity
    }
  ];

  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-2 rounded-lg">
              <Star className="h-5 w-5" />
            </div>
            <span className="text-xl font-bold text-gray-900">SmartBet</span>
          </Link>

          {/* Navigation Items */}
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                    isActive
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation; 