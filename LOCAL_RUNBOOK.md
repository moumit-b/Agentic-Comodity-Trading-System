# Local Development Commands

## Start Backend API

```bash
cd C:\Users\moumi\Agentic-Comodotity-Trading-System
uv run python -m uvicorn src.api.main:app --reload --port 8000
```

**Access:** http://localhost:8000/docs

## Start Frontend Dashboard

```bash
cd C:\Users\moumi\Agentic-Comodotity-Trading-System\frontend
npm run dev
```

**Access:** http://localhost:3000

## Verify System

1. **Backend:** Check http://localhost:8000/docs shows API documentation
2. **Frontend:** Check http://localhost:3000 shows dashboard
3. **WebSocket:** Dashboard should show "CONNECTED" status indicator

## Troubleshooting

### Backend won't start
```bash
# Install dependencies
uv pip install fastapi uvicorn[standard] websockets
```

### Frontend won't start
```bash
cd frontend
npm install
npm run dev
```

### Dashboard shows errors
- Clear cache: Delete `frontend/.next` folder
- Restart: `npm run dev`
