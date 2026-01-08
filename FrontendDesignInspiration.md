# Professional Agentic Trading Dashboard UI — Design Reference (Dribbble inspo)

This doc is meant to be AN INSPIRATION GUIDE into Claude Code (frontend skill) so it can generate a UI that feels like a **professional trading tool** (clean, dense, elegant, institutional).

**Primary references (screenshots you attached):**
- Ref A (EchoFi-style): dark “glass” dashboard + pastel brand accents; font: **Banana Grotesk**; palette shown: `#000000`, `#c2f4ff`, `#c6c0ff`, `#b1ffc2`, `#ffffff`.
- Ref B (Numora-style): darker, more “terminal/quant” vibe; font: **IBM Plex Mono**; palette shown: `#225AEB`, `#565B66`, `#B62472`.

---

## 1) What makes these feel “pro-grade”

### Visual language
- **Dark, desaturated base** with *very subtle* gradients (charcoal → near-black), sometimes a soft vignette.
- **Two-layer depth model**:
  1) App “shell” (background)
  2) Floating dashboard surface (rounded, bordered, slightly blurred or softly lit)
- **Hairline borders** everywhere (1px, low opacity), not heavy shadows.
- **High information density** without chaos: strong alignment, consistent spacing, restrained accent use.
- **Numbers and tickers feel “precise”**: monospaced or tabular numerals; consistent decimals; aligned columns.
- **Elegant controls**: segmented tabs, pill chips, toggles, icon buttons—minimal text, no noisy outlines.

### Component geometry
- Dashboard containers and cards use **large radii** (≈ 16–24px).
- Internal elements use **smaller radii** (≈ 10–14px), and chips use **full pill**.
- Lots of **soft padding** and **consistent gutters** (8px grid).

### Color usage (important)
- The UI is mostly grayscale. **Accent colors are sparse**:
  - Ref A uses pastel accents (cyan/lavender/mint) for **selected states**, not for everything.
  - Ref B uses a stronger blue/magenta accent but still sparingly.
- Performance semantics:
  - **Green** for positive / buy / up
  - **Red** for negative / sell / down
  - Keep them muted; avoid neon unless for tiny highlights.

---

## 2) Design anatomy of the references

### Ref A: EchoFi-style (glass + pastel)
**Overall structure**
- A single large rounded dashboard surface.
- **Top app bar** inside the surface:
  - Left: logo + product name
  - Center-left: **search** pill (icon + placeholder)
  - Center: primary nav links (EchoFi / Exchange / Portfolio / NFTs / AI Signals)
  - Right: “Connect wallet” primary button + icon buttons + avatar
- **Asset header row** (below nav):
  - Left: asset selector (icon + ticker + name + dropdown)
  - Right: a horizontal row of **KPI stats** (Price, Market cap, 24H change, Volume(24h), FDV, Buy/Sell volume, Total locked, DEXs volume)

**Main work area**
- Left ~70%: **chart card**
  - Top-left: chart mode segmented control (e.g., *Price* / *Market cap*) + small icon buttons
  - Top-center: feature toggles (Volume / TVL / Transaction)
  - Top-right: time range chips (1D/7D/1M/1Y/All) with one selected (filled pill)
  - Chart style: soft line, subtle grid, tooltip card with date + price + volume; volume bars along bottom
- Right ~30%: **trade ticket**
  - “Buy / Sell” header with Buy highlighted (green)
  - Tab row: Market / Limit / Conditional
  - Balance row + large amount input + USD conversion
  - Slider for size (0–100%)
  - Small rows for Max slippage / Gas fee / Minimum received
  - Bottom: large primary CTA (connect wallet / place order)

**Key feel**
- Calm, premium: glass overlay, slightly blurred backgrounds, pastel selection states.

---

### Ref B: Numora-style (terminal/quant + analytics grid)
**Overall structure**
- Top app bar:
  - Left: logo + product name
  - Search input (“Search any token”)
  - Nav links (AI Signals / Stake / Portfolio / Smart Alerts)
  - Right: bell icon + user profile chip (name + wallet address)
- Second row: asset header and chart tooling
  - Asset chip with icon + ticker
  - “Indicators” dropdown
  - Mode toggle (Price / Market cap)
  - Icon actions (undo/redo etc.)
  - Time range chips (1D/7D/1M/1Y/All)

**Main work area**
- Left: **candlestick chart** with fine grid; minimalist axis labels; controls are tight and utilitarian.
- Right: **portfolio insight panel**
  - “Portfolio” header + “Buy {asset}” chip button
  - Today / Month / Year P&L blocks with percent change colored
  - Allocation/flow visualization using a compact square matrix + legend

**Lower analytics row**
- “Transactions Heatmap” card (grid of squares with intensity)
- “Holders” card (segmented distribution: Cruisers/Holders/Traders)
- “Unlocks” card (donut progress with category breakdown)

**Key feel**
- Serious, “desk tool” vibe: tighter spacing, more mono typography, analytic widgets.

---

## 3) Recommended design system (tokens)

> Use CSS variables so Claude (and you) can keep everything consistent across pages.

### Core grayscale (suggested)
- `--bg`: near-black background
- `--surface-1`: main dashboard surface
- `--surface-2`: card surface
- `--border`: hairline strokes (low opacity)
- `--text`: primary text
- `--muted`: secondary labels
- `--faint`: tertiary (axis ticks, placeholders)

### Accents (choose one “brand set”)
**Brand set A (pastel like Ref A)**
- `--accent-cyan: #c2f4ff`
- `--accent-lavender: #c6c0ff`
- `--accent-mint: #b1ffc2`

**Brand set B (bold like Ref B)**
- `--accent-blue: #225AEB`
- `--accent-gray: #565B66`
- `--accent-magenta: #B62472`

### Semantics (trading)
- `--pos`: muted green (for gains/buy)
- `--neg`: muted red (for losses/sell)
- `--warn`: muted amber (risk/warnings)

### Elevation model
- Avoid heavy drop shadows. Prefer:
  - 1px border with low opacity
  - subtle inner highlight
  - optional soft outer shadow only on top-level surface

---

## 4) Typography rules (institutional feel)

### Font strategy
- **Headings/UI**: Banana Grotesk / Inter / SF Pro (clean grotesk)
- **Numbers/tickers**: IBM Plex Mono (or enable `font-variant-numeric: tabular-nums`)

### Scale (example)
- Page title: 20–24px, 600–700
- Card title: 14–16px, 600
- Body: 13–14px, 400–500
- Labels: 11–12px, 500, uppercase optional with tracking
- KPI numbers: 14–18px, tabular numerals

### Formatting conventions (critical for pro dashboards)
- Always show currency with consistent decimals (e.g., 2 for USD, 6–8 for crypto qty).
- Right-align numeric columns in tables; align decimals if possible.
- Use compact separators (thin spaces) and consistent abbreviations (K/M/B).

---

## 5) Layout + spacing (how to get the density right)

### Grid
- Use an **8px spacing system** (4/8/12/16/24/32).
- Dashboard surface padding: **24–32px**
- Card padding: **16–20px**
- Control row gaps: **8–12px**
- KPI row uses **equal-width columns** with consistent label/value alignment.

### App shell layout (recommended)
- **Top bar**: fixed height ~56–64px
- **Main**: 12-column grid
  - Left: 8–9 columns (chart + analytics)
  - Right: 3–4 columns (trade ticket / portfolio insights)
- For large screens, keep a **max width** so content doesn’t stretch too wide.

### Visual hierarchy
- Highest emphasis: chart + order ticket (Ref A), chart + portfolio (Ref B)
- Next: KPI row
- Then: secondary analytics cards

---

## 6) Component patterns to replicate

### Top navigation
- Left brand, middle nav, right utilities.
- Search is a **pill input** with icon and subtle placeholder.
- Primary action button is **high-contrast** (often white filled), not neon.

### Segmented controls + chips
- Use pill segmented controls for:
  - Price vs Market cap
  - Market vs Limit vs Conditional
  - 1D/7D/1M/1Y/All
- Selected: filled background + slightly brighter text.
- Unselected: transparent + muted text.

### KPI stat blocks
Each KPI block:
- Label (muted) on top
- Value (primary) below
- Optional delta (% change) with semantic color

### Chart container (must-have details)
- Subtle grid lines
- Crosshair + tooltip card
- Time range chips on top-right
- Overlay toggles: Volume / TVL / Transactions
- Volume histogram inside chart area (bottom)
- Minimal axis labels (muted, small)

### Trade ticket / execution panel
- Header with Buy/Sell tabs (semantic colors)
- Order type tabs (Market/Limit/Conditional)
- Amount input + unit selector + USD equivalent
- Slider for size (%)
- Advanced rows (slippage, fees, min received)
- Primary CTA at bottom (place order / connect)

### Analytics cards (Ref B style)
- Heatmap grid (transactions / liquidity)
- Distribution bars (holders segments)
- Donut progress (unlocks / risk budgets)
- Compact legends

---

## 7) Micro-interactions (what makes it feel expensive)
- Hover: slight background lift + border brightening (not a big glow).
- Pressed: tiny translateY(1px) or darker fill.
- Focus: accessible focus ring (subtle but clear).
- Loading: skeletons for KPIs and charts; shimmer is optional but should be subtle.
- Real-time updates: **avoid layout shift**; animate numbers with gentle transitions.

**Motion timings**
- Fast UI transitions: 120–180ms
- Panel expansions: 200–260ms
- Use easing like `cubic-bezier(0.2, 0.8, 0.2, 1)`.

---

## 8) Practical implementation notes (React/Next/Tailwind friendly)

### Use tokens + variants
- Build components with:
  - `variant`: default / ghost / subtle / danger / success
  - `size`: sm / md / lg
  - `state`: default / hover / active / disabled / loading

### CSS tips
- Keep borders at 1px with ~6–10% opacity (white on dark).
- Add a **very subtle noise** overlay or gradient to avoid flatness.
- Use `backdrop-filter: blur(...)` only on top-level surfaces (glass); don’t overuse.

### Charting
- For “pro” feel: TradingView Lightweight Charts, ECharts, or custom D3.
- Ensure:
  - crosshair
  - tooltip
  - performant updates (requestAnimationFrame / throttling)

---


### Notes
If you want, you can keep Ref A’s **pastel accents** for selections and Ref B’s **mono numerics + analytics widgets** for seriousness. That combo reads “modern institutional” rather than “consumer crypto app”.
