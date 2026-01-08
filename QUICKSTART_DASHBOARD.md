# Quantum Terminal - Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Prerequisites
- Python 3.11+ with dependencies installed
- Node.js 18+
- Backend API ready (FastAPI)

---

## Step 1: Start the Backend API (Terminal 1)

```bash
# From project root
cd src/api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Verify**: Open http://localhost:8000 - should see `{"status":"ok"}`

---

## Step 2: Install Frontend Dependencies (Terminal 2)

```bash
# From project root
cd frontend
npm install
```

This installs:
- Next.js 14
- Tailwind CSS
- Lightweight Charts
- TypeScript
- All required dependencies

---

## Step 3: Configure Environment

```bash
# In frontend/ directory
cp .env.local.example .env.local
```

Verify `.env.local` contains:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/ws
```

---

## Step 4: Start Frontend (Same Terminal 2)

```bash
npm run dev
```

---

## Step 5: Open Dashboard

Navigate to: **http://localhost:3000**

You should see:
- ✅ Quantum Terminal header
- ✅ System Status (Database, WebSocket, Market, Alpaca)
- ✅ Price Chart (may be empty if no data)
- ✅ Positions Table
- ✅ Signal Feed (right column)
- ✅ Risk Gauges
- ✅ Circuit Breakers

---

## 🎨 Expected Appearance

### Theme
- **Dark Background**: Near-black (#0a0a0f)
- **Glass Cards**: Semi-transparent with blur
- **Neon Accents**: Cyan highlights on key data
- **Animated Elements**: Scan-line overlay, pulse effects

### Layout
- **Left Column (2/3)**: Price Chart + Positions Table
- **Right Column (1/3)**: Signal Feed + Risk Gauges + Circuit Breakers
- **Top Bar**: System Status with Kill Switch button

---

## 🔧 Troubleshooting

### "WebSocket disconnected"
**Fix**: Ensure backend is running on port 8000
```bash
# Check backend
curl http://localhost:8000/health
```

### "No data showing"
**Expected**: If this is a fresh installation, you need to:
1. Start the trading loop (Lambda or local)
2. Wait for market data to populate
3. Signals will appear once strategies execute

### Port 3000 already in use
```bash
# Use alternative port
npm run dev -- -p 3001
```
Then open http://localhost:3001

### Tailwind styles not loading
```bash
# Clear Next.js cache
rm -rf .next
npm run dev
```

---

## 📊 Testing WebSocket Connection

Open browser DevTools → Console

You should see:
```
WebSocket connected
```

Send a test message from backend and watch it appear in real-time.

---

## 🎯 Next Steps

### 1. Populate with Real Data
- Run the trading loop to generate signals
- Open positions to see them in Positions Table
- Activate strategies to see signals flow in

### 2. Test Kill Switch
- Click the red "KILL SWITCH" button
- Confirm in the modal
- Watch Circuit Breakers activate

### 3. Explore Pages
- **Performance** (left sidebar) - View equity curve
- **Signals** - Full signal history
- **Configuration** - System settings
- **Risk** - Advanced risk metrics
- **Audit** - System audit log

### 4. Customize
- Edit `tailwind.config.js` for color changes
- Modify components in `src/components/dashboard/`
- Add new pages in `src/app/`

---

## 📱 Mobile View

The dashboard is responsive but optimized for desktop/tablet (1024px+).

For mobile optimization, see `FEATURES_ROADMAP.md` Phase 11.

---

## 🔐 Security Notes

### Development Mode
- CORS is set to `localhost:3000`
- WebSocket is unencrypted (ws://)
- No authentication required

### Before Production
- [ ] Switch to WSS (secure WebSocket)
- [ ] Add JWT authentication
- [ ] Configure production CORS
- [ ] Enable HTTPS
- [ ] Set secure environment variables

---

## 💡 Tips for Best Experience

1. **Use Chrome/Edge** - Best WebSocket support
2. **Full Screen** - F11 for immersive terminal feel
3. **Dark Room** - Neon glows pop in low light
4. **Multiple Monitors** - Span dashboard across screens

---

## 📦 What's Included

### ✅ Phase 1 Complete (Core Dashboard)
- [x] System Status with real-time updates
- [x] Professional candlestick charts
- [x] Live position tracking
- [x] Real-time signal feed
- [x] Animated risk gauges
- [x] Circuit breaker monitoring
- [x] Order confirmation system
- [x] WebSocket integration
- [x] Dark theme design system
- [x] Responsive layout

### 🔮 Coming Soon (See FEATURES_ROADMAP.md)
- Advanced analytics (Phase 2)
- Strategy development tools (Phase 5)
- AI/ML features (Phase 6)
- Mobile optimization (Phase 11)
- 200+ additional features

---

## 🆘 Need Help?

1. **Check Logs**
   - Frontend: Browser DevTools → Console
   - Backend: Terminal running uvicorn

2. **Verify Connections**
   ```bash
   # API health
   curl http://localhost:8000/health

   # WebSocket (requires wscat)
   wscat -c ws://localhost:8000/api/ws
   ```

3. **Review Documentation**
   - `frontend/README.md` - Detailed setup
   - `FEATURES_ROADMAP.md` - Feature list
   - `infrastructure/terraform/README.md` - AWS deployment

---

**Built with precision. Designed for performance. Engineered for traders.**

*Estimated setup time: 5-10 minutes*
