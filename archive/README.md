# SmartBet - SportMonks Integration

This project includes a comprehensive SportMonks API integration for fetching football match data from Romanian leagues.

## SportMonks API Setup

1. Sign up for a SportMonks account at [https://www.sportmonks.com/](https://www.sportmonks.com/)
2. Get your API token from the dashboard
3. Create a `.env` file in the project root with the following content:
   ```
   SPORTMONKS_TOKEN=your_api_token_here
   ```

## Features

The SportMonks integration provides:

- Fetching live and upcoming fixtures from Romanian leagues
- Rich metadata extraction (lineups, injuries, statistics)
- Timezone-aware datetime handling
- Automatic creation of leagues and teams
- Comprehensive logging

## Usage

### Fetch Fixtures Command

```bash
# Fetch fixtures for the next 7 days (default)
python manage.py fetch_sportmonks_fixtures

# Fetch fixtures with verbose logging
python manage.py fetch_sportmonks_fixtures --verbose

# Fetch fixtures for a custom number of days
python manage.py fetch_sportmonks_fixtures --days 14
```

### Data Model

The integration stores data in the following models:

- `Match`: Core match data (teams, scores, status, venue)
- `MatchMetadata`: Additional JSON data (lineups, events, statistics)
- `Team`: Team information
- `League`: League information

## Rate Limiting

The integration includes built-in rate limiting to comply with SportMonks API limits.

# SmartBet Frontend

A beautiful, clean, mobile-first, and professional frontend for SmartBet using Next.js 14 with the App Router.

## 🔧 Tech Stack

- **Next.js 14** - React framework with App Router
- **Tailwind CSS + Shadcn UI** - Styling and component library
- **TypeScript** - Type safety
- **Zustand** - State management (ready for implementation)
- **TanStack React Query** - API data fetching and caching

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```

3. **Open your browser:**
   - Landing page: [http://localhost:3000](http://localhost:3000)
   - Dashboard: [http://localhost:3000/dashboard](http://localhost:3000/dashboard)

## 📁 Project Structure

```
src/
├── app/
│   ├── dashboard/
│   │   └── page.tsx          # Main dashboard with prediction cards
│   ├── api/
│   │   ├── predictions/
│   │   │   └── route.ts       # Mock predictions API
│   │   └── feedback/
│   │       └── route.ts       # Feedback submission API
│   ├── layout.tsx             # Root layout with providers
│   └── page.tsx               # Landing page
├── components/
│   ├── PredictionCard/
│   │   └── index.tsx          # Main prediction card component
│   ├── ui/                    # Shadcn UI components
│   │   ├── button.tsx
│   │   └── badge.tsx
│   └── Providers.tsx          # React Query provider
├── hooks/
│   ├── usePredictions.ts      # Fetch predictions hook
│   └── useFeedback.ts         # Submit feedback hook
├── lib/
│   ├── api.ts                 # API functions
│   └── utils.ts               # Utility functions
├── types/
│   ├── prediction.ts          # Prediction type definitions
│   └── feedback.ts            # Feedback type definitions
└── styles/
    └── globals.css            # Global styles with Shadcn variables
```

## 🖼️ Features

### Dashboard (`/dashboard`)
- **Top 3 SmartBet picks** of the day
- **PredictionCard components** showing:
  - Match details (teams, league, kickoff time)
  - Bet recommendation (e.g., "Draw", "Team A Win")
  - Odds
  - Expected Value (EV) percentage with color-coded badges
  - Confidence badges (HIGH/MEDIUM/LOW)
  - Feedback buttons: ✅ Yes / ❌ No - "Did you bet this?"

### Components

#### PredictionCard
- **Visually styled card** with clean design
- **Color-coded badges** for EV and confidence levels
- **Interactive feedback** with loading states
- **Mobile-first responsive** design
- **Dark mode support**

#### API Integration
- **Mock predictions API** (`/api/predictions`) with realistic data
- **Feedback API** (`/api/feedback`) for user interaction tracking
- **React Query** for caching and optimistic updates

## 🎨 Design Principles

- **Mobile-first** responsive design
- **Clean and minimal** following Shadcn UI principles
- **Strong visual hierarchy** for EV and confidence indicators
- **Trust-building UI** with professional appearance
- **Accessibility** considerations with proper ARIA labels

## 🔧 Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

### Adding New Components

To add new Shadcn UI components:

```bash
npx shadcn@latest add [component-name]
```

### API Integration

The frontend is designed to work with mock APIs but can easily be connected to a real backend:

1. Update `src/lib/api.ts` with your backend URLs
2. Modify the type definitions in `src/types/` as needed
3. Update the React Query hooks in `src/hooks/` for any additional data fetching needs

## 🚀 Deployment

### Build for Production

```bash
npm run build
npm run start
```

### Environment Variables

Create a `.env.local` file for environment-specific configuration:

```env
NEXT_PUBLIC_API_URL=your-backend-url
```

## 📱 Mobile Experience

The application is optimized for mobile devices with:
- Touch-friendly button sizes
- Responsive grid layouts
- Optimized typography scales
- Fast loading with React Query caching

## 🎯 Next Steps

1. **Connect to real SmartBet ML backend** API
2. **Add user authentication** and personalization
3. **Implement Zustand** for global state management
4. **Add more prediction types** and filtering
5. **Implement push notifications** for new predictions
6. **Add betting history** and performance tracking

---

Built with ❤️ using Next.js 14, Tailwind CSS, and Shadcn UI. 