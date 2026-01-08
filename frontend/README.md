# Quantum Terminal - Professional Trading Dashboard

A hyper-modern, institutional-grade algorithmic trading dashboard built with Next.js 14, featuring real-time WebSocket updates, professional dark theme design, and comprehensive trading analytics.

## 🚀 Features

### Core Dashboard Components
- **System Status** - Real-time system health, automation mode, account balance, and emergency kill switch
- **Price Chart** - Professional candlestick charts with Lightweight Charts library
- **Positions Table** - Live P&L tracking with expandable position details
- **Signal Feed** - Real-time trading signals with filtering and approval status
- **Risk Gauges** - Animated portfolio heat, RSI, and daily P&L gauges
- **Circuit Breakers** - 7-breaker safety system with live status
- **Order Confirmation** - Floating confirmation modal for LIVE_CONFIRM mode

### Real-Time Features
- **WebSocket Integration** - Live updates without page refresh
- **Auto-Reconnect** - Resilient WebSocket connection management
- **Message Handlers** - account_update, position_update, signal_new, circuit_breaker, risk_update

### Design System
- **Dark Trading Terminal Aesthetic** - Cyberpunk-inspired professional design
- **Glass Morphism Cards** - Subtle transparency with backdrop blur
- **Neon Data Glows** - Highlighted critical metrics with glow effects
- **Animated Gauges** - SVG-based gauge needles with smooth transitions
- **Scan-Line Effects** - Subtle retro-futuristic overlay
- **Noise Texture** - Adds depth to the terminal interface

## 📋 Prerequisites

- **Node.js** 18+ and npm
- **Backend API** running at `http://localhost:8000`
- **Modern Browser** with WebSocket support

## 🛠️ Installation

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/ws
```

### 3. Font Setup

Download the Azeret Mono font:
- Visit: https://fonts.google.com/specimen/Azeret+Mono
- Download variable font
- Place `AzeretMono-Variable.woff2` in `public/fonts/`

OR use the fallback monospace font (auto-configured).

### 4. Start Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📦 Build for Production

```bash
npm run build
npm start
```

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout with sidebar & theme
│   │   ├── page.tsx            # Main dashboard page
│   │   ├── performance/        # Performance analytics page
│   │   ├── signals/            # Signals history page
│   │   ├── configuration/      # Configuration page
│   │   ├── risk/               # Risk analytics page
│   │   └── audit/              # Audit log page
│   ├── components/
│   │   ├── layout/
│   │   │   └── Sidebar.tsx     # Navigation sidebar
│   │   └── dashboard/
│   │       ├── SystemStatus.tsx
│   │       ├── PriceChart.tsx
│   │       ├── PositionsTable.tsx
│   │       ├── SignalFeed.tsx
│   │       ├── RiskGauges.tsx
│   │       ├── CircuitBreakers.tsx
│   │       └── OrderConfirmation.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts     # WebSocket connection management
│   │   └── useApi.ts           # REST API data fetching
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   └── utils.ts            # Utility functions
│   └── types/
│       └── index.ts            # TypeScript type definitions
├── public/
│   └── fonts/                  # Custom fonts
├── package.json
├── next.config.js
├── tailwind.config.js
└── tsconfig.json
```

## 🎨 Design Philosophy

### Quantum Terminal Aesthetic
- **Concept**: Hyper-modern trading terminal combining cyberpunk precision with institutional-grade design
- **Inspiration**: Bloomberg Terminal meets Blade Runner
- **Typography**: Rajdhani (display), IBM Plex Sans (UI), Azeret Mono (data)
- **Color Palette**: Near-black backgrounds with neon accents

### Color System
```css
Background:     #0a0a0f  /* Near black */
Surface:        #12121a  /* Dark card background */
Border:         #1e1e2e  /* Subtle borders */
Text Primary:   #ffffff  /* White */
Text Secondary: #a0a0b0  /* Gray */
Profit Green:   #00c853  /* Success/gains */
Loss Red:       #ff1744  /* Errors/losses */
Warning Yellow: #ffc107  /* Warnings */
Accent Blue:    #2196f3  /* Primary actions */
Accent Purple:  #7c4dff  /* Secondary actions */
Accent Cyan:    #00d4ff  /* Data highlights */
```

## 🔌 API Integration

### REST Endpoints
```typescript
GET  /api/account                    // Account status
GET  /api/positions                  // Open positions
GET  /api/signals?limit=50           // Trading signals
GET  /api/executions                 // Trade executions
GET  /api/circuit-breakers           // Circuit breaker status
GET  /api/risk/metrics               // Risk metrics
GET  /api/bars/{symbol}?limit=390    // Price bars
GET  /api/indicators/{symbol}        // Technical indicators
POST /api/kill-switch                // Emergency stop
POST /api/executions/{id}/confirm    // Confirm/reject trade
```

### WebSocket Messages
```typescript
// Received message types
{
  type: 'account_update' | 'position_update' | 'signal_new' |
        'circuit_breaker' | 'risk_update' | 'market_status',
  data: { ... },
  timestamp: '2024-01-01T00:00:00Z'
}
```

## 🧪 Development Tips

### Hot Reload
Next.js automatically reloads on file changes. WebSocket reconnects automatically.

### Debug Mode
Open browser DevTools → Console to see:
- WebSocket connection status
- API requests/responses
- Component lifecycle logs

### Component Testing
```bash
# Install React DevTools extension
# Inspect component state in real-time
```

## 🚢 Deployment

### Docker (Recommended)
See `docker-compose.yml` in project root.

### Vercel
```bash
npm install -g vercel
vercel
```

### Static Export
```bash
npm run build
# Deploy `out/` directory to any static host
```

## 🔒 Security

- **API Keys**: Never commit API keys. Use environment variables.
- **CORS**: Configure backend CORS for production domains.
- **WebSocket**: Use WSS (secure WebSocket) in production.
- **Authentication**: Add authentication middleware (Phase 3).

## 📊 Performance Optimization

### Already Implemented
- **React Server Components** where possible
- **Lazy Loading** for heavy components
- **Memoization** with React hooks
- **Optimized Re-renders** with WebSocket state updates
- **SVG Gauges** instead of canvas for better performance

### Future Improvements
- Virtual scrolling for large lists
- Service Worker caching
- Image optimization
- Code splitting by route

## 🐛 Troubleshooting

### WebSocket Won't Connect
```bash
# Check backend is running
curl http://localhost:8000/health

# Check WebSocket endpoint
wscat -c ws://localhost:8000/api/ws
```

### Blank Page on Load
- Check browser console for errors
- Verify API endpoints are accessible
- Clear Next.js cache: `rm -rf .next`

### Styles Not Applying
```bash
# Rebuild Tailwind
npm run dev
# Force refresh: Ctrl+Shift+R (Chrome)
```

## 📚 Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Lightweight Charts
- **Icons**: Lucide React
- **Animation**: Framer Motion
- **WebSocket**: Native WebSocket API
- **Date**: date-fns

## 🗺️ Future Roadmap

See `FEATURES_ROADMAP.md` for comprehensive feature list including:
- Advanced analytics (Phase 2)
- Risk management suite (Phase 3)
- AI/ML features (Phase 6)
- Mobile optimization (Phase 11)
- 200+ additional features planned

## 📄 License

Proprietary - Internal Use Only

## 🤝 Contributing

Internal project. Contact project maintainer for access.

## 📞 Support

For issues or questions:
- Check `FEATURES_ROADMAP.md` for planned features
- Review API documentation at `/api/docs`
- Contact development team

---

**Built with precision. Designed for performance. Engineered for traders.**
