import React from 'react';

interface FiltersProps {
  confidenceLevel: string;
  league: string;
  onConfidenceChange: (value: string) => void;
  onLeagueChange: (value: string) => void;
  availableLeagues: string[];
}

export default function Filters({
  confidenceLevel,
  league,
  onConfidenceChange,
  onLeagueChange,
  availableLeagues,
}: FiltersProps) {
  return (
    <div className="bg-white rounded-lg shadow mb-6 p-4">
      <h2 className="text-lg font-semibold mb-4">Filters</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Confidence Level Filter */}
        <div>
          <label htmlFor="confidenceLevel" className="block text-sm font-medium text-gray-700 mb-1">
            Confidence Level
          </label>
          <select
            id="confidenceLevel"
            value={confidenceLevel}
            onChange={(e) => onConfidenceChange(e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
          >
            <option value="All">All Levels</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        {/* League Filter */}
        <div>
          <label htmlFor="league" className="block text-sm font-medium text-gray-700 mb-1">
            League
          </label>
          <select
            id="league"
            value={league}
            onChange={(e) => onLeagueChange(e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
          >
            <option value="All">All Leagues</option>
            {availableLeagues.map((leagueName) => (
              <option key={leagueName} value={leagueName}>
                {leagueName}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
} 