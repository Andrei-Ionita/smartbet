# SmartBet Frontend MVP

A modern, responsive web application for monitoring and exploring AI-powered football predictions across top European leagues.

## 🚀 Features

### 📱 Pages
- **Home Page** (`/`) - Welcome message, league selector, and value proposition
- **Predictions Dashboard** (`/predictions`) - List of upcoming matches with predictions
- **Match Detail** (`/match/[matchId]`) - Full prediction analysis with charts
- **Coming Soon** (`/coming-soon`) - Season countdowns and status updates
- **Sandbox** (`/sandbox`) - Interactive prediction testing environment

### 🎯 Core Functionality
- **League Support**: Premier League, La Liga, Serie A, Bundesliga, Ligue 1
- **Prediction Display**: Outcome, confidence, expected value, odds
- **SHAP Explanations**: Top influencing factors in plain language
- **Visual Indicators**: Recommended bets, confidence levels, risk assessment
- **Filtering**: By league, recommendation status
- **Responsive Design**: Mobile-first approach with Tailwind CSS

## 🛠 Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Icons**: Lucide React
- **Date Handling**: date-fns
- **Language**: TypeScript

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd smartbet-frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Run the development server**
   ```bash
   npm run dev
   ```

4. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## 🏗 Project Structure

```
smartbet-frontend/
├── app/                    # Next.js App Router pages
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page
│   ├── predictions/       # Predictions dashboard
│   ├── match/[matchId]/   # Match detail pages
│   ├── coming-soon/       # Coming soon page
│   └── sandbox/           # Sandbox testing page
├── components/            # Reusable components
│   ├── Navigation.tsx     # Main navigation
│   └── MatchCard.tsx      # Match prediction card
├── lib/                   # Utilities and data
│   ├── types.ts          # TypeScript type definitions
│   └── mockData.ts       # Mock data for development
└── public/               # Static assets
```

## 🎨 Design System

### Colors
- **Primary**: Blue (#3b82f6) - Main brand color
- **Success**: Green (#22c55e) - Positive outcomes
- **Warning**: Orange (#f59e0b) - Caution states
- **Danger**: Red (#ef4444) - Negative outcomes

### Components
- **Cards**: White background with subtle shadows and borders
- **Buttons**: Primary (blue) and secondary (gray) variants
- **Badges**: Status indicators with color coding
- **Charts**: Interactive pie charts for probability distribution

## 📊 Mock Data

The application uses realistic mock data for development:

### Supported Leagues
- **Premier League** (🏴󠁧󠁢󠁥󠁮󠁧󠁿) - Experimental model
- **La Liga** (🇪🇸) - Production model (74.4% hit rate)
- **Serie A** (🇮🇹) - Production model (61.5% hit rate)
- **Bundesliga** (🇩🇪) - Production model (68.7% hit rate)
- **Ligue 1** (🇫🇷) - Production model (64.3% hit rate)

### Prediction Features
- **Outcome**: Home Win, Draw, Away Win
- **Confidence**: 0-100% with color coding
- **Expected Value**: Positive/negative percentage
- **SHAP Features**: Top 4 influencing factors
- **Odds**: Market odds for all outcomes
- **Recommendations**: Based on confidence > 65% and EV > 0%

## 🔧 Configuration

### Environment Variables
Create a `.env.local` file for environment-specific settings:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=SmartBet
```

### Tailwind Configuration
Custom colors and components are defined in `tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: { /* Blue shades */ },
      success: { /* Green shades */ },
      warning: { /* Orange shades */ },
      danger: { /* Red shades */ }
    }
  }
}
```

## 🚀 Deployment

### Build for Production
```bash
npm run build
npm start
```

### Vercel Deployment
1. Connect your repository to Vercel
2. Configure environment variables
3. Deploy automatically on push to main branch

### Docker Deployment
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## 🔄 API Integration

The frontend is designed to integrate with the SmartBet backend API:

### Endpoints
- `GET /api/predictions` - List of predictions
- `GET /api/predictions/[matchId]` - Single match prediction
- `POST /api/predictions/sandbox` - Sandbox prediction generation
- `GET /api/leagues` - Supported leagues information

### Data Structure
```typescript
interface Prediction {
  outcome: 'Home' | 'Draw' | 'Away'
  confidence: number
  expectedValue: number
  odds: { home: number, draw: number, away: number }
  explanation: string
  shapFeatures: ShapFeature[]
  isRecommended: boolean
}
```

## 🧪 Testing

### Component Testing
```bash
npm run test
```

### E2E Testing
```bash
npm run test:e2e
```

## 📱 Responsive Design

The application is fully responsive with breakpoints:
- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

### Mobile-First Features
- Touch-friendly navigation
- Swipe gestures for match cards
- Optimized charts for small screens
- Collapsible sections for better UX

## 🎯 Future Enhancements

### Planned Features
- **Real-time Updates**: WebSocket integration for live predictions
- **User Authentication**: Login/signup with prediction history
- **Notifications**: Push notifications for recommended bets
- **Advanced Filters**: Date range, team-specific filtering
- **Export Features**: PDF reports, CSV data export
- **Dark Mode**: Theme switching capability

### Performance Optimizations
- **Image Optimization**: Next.js Image component
- **Code Splitting**: Dynamic imports for better loading
- **Caching**: Service worker for offline functionality
- **Bundle Analysis**: Webpack bundle analyzer

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

---

**SmartBet Frontend MVP** - AI-powered football predictions with a modern, responsive interface. 