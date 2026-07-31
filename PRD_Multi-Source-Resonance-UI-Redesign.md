# Multi-Source Resonance — Web UI Redesign PRD

**Version:** 1.0 Draft
**Date:** 2026-07-31
**Author:** wed ui專員
**Status:** Pending Review

---

## 1. Overview

### 1.1 Product Context

Multi-Source Resonance (MSR) is a financial market monitoring and signal generation system. It aggregates 20+ data sources across four dimensions — Options Gamma Exposure (GEX), VIX Volatility Term Structure, Crypto Derivatives, and Dark Pool Flow — then produces a composite resonance score (0–5.0) with tiered alerts via Hawkes self-exciting process modeling and Bayesian adaptive weighting.

### 1.2 Redesign Goal

Replace the current Vue 3 + ECharts frontend with a modern React + TypeScript + Spark Design UI that:

- Provides a **command-center** experience for real-time market signal monitoring
- Surfaces the composite resonance score and per-dimension breakdowns with clarity
- Reduces cognitive load through progressive disclosure (overview → drill-down)
- Supports real-time WebSocket data streaming with graceful degradation
- Delivers responsive layouts for desktop-first, tablet-secondary usage

### 1.3 Tech Stack (Target)

| Layer | Choice |
|-------|--------|
| Framework | React 18 + TypeScript |
| UI Library | Spark Design (NPM mode: `sparkdesign`) |
| Charts | ECharts (via `echarts-for-react`) or Recharts |
| State | Zustand or TanStack Query (server state) |
| Real-time | Native WebSocket + reconnect logic |
| Build | Vite |
| Routing | React Router v6 |

### 1.4 Non-Goals

- Backend API changes (consume existing endpoints as-is)
- Mobile-native app
- Multi-language i18n (English-only for v1)
- User management / multi-tenant UI

---

## 2. Users & Personas

| Persona | Description | Primary Task |
|---------|-------------|--------------|
| **Quant Trader** | Active trader monitoring signals for entry/exit timing | Glance at resonance score → drill into triggering dimension → acknowledge alert |
| **Risk Analyst** | Reviews historical signal accuracy and dimension contributions | Browse signal history → check outcome stats → review backtest |
| **System Operator** | Monitors data pipeline health and fetcher status | Check source health → identify degraded fetchers → trigger re-collection |

---

## 3. Information Architecture

```
┌─────────────────────────────────────────────────────────┐
│  App Shell (Sidebar + TopBar + Content Area)            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  /                  → Dashboard (Resonance Overview)    │
│  /gex               → Gamma Exposure Analysis          │
│  /vix               → VIX Term Structure               │
│  /crypto            → Crypto Derivatives               │
│  /darkpool          → Dark Pool Flow                   │
│  /signals           → Signal History & Management      │
│  /analysis          → LLM-Augmented Analysis           │
│  /system            → System Health & Diagnostics      │
│  /settings          → Runtime Configuration            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Page Specifications

### 4.1 Dashboard — Resonance Command Center (`/`)

**Purpose:** Single-glance situational awareness. The composite score is the hero element.

**Layout (Desktop):**

```
┌──────────────────────────────────────────────────────────────┐
│  TopBar: System Status Badge │ Last Update │ WS Connection   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐  ┌──────────────────────────────────┐  │
│  │  RESONANCE      │  │  Dimension Score Cards (4)       │  │
│  │  GAUGE          │  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌────┐│  │
│  │  (0 - 5.0)     │  │  │ GEX │ │ VIX │ │CRYPT│ │DARK││  │
│  │  + Alert Level  │  │  │/2.5 │ │/1.5 │ │/2.0 │ │/2.0││  │
│  │  Badge          │  │  └─────┘ └─────┘ └─────┘ └────┘│  │
│  └─────────────────┘  └──────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Signal Timeline (last 24h alerts, sparkline)        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌────────────────────┐  ┌────────────────────────────┐     │
│  │  Hawkes Intensity  │  │  Source Health Grid        │     │
│  │  (branching ratio) │  │  (23 fetchers, status dot) │     │
│  └────────────────────┘  └────────────────────────────┘     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- `GET /api/dashboard` — aggregated resonance view
- `GET /api/signals/latest` — most recent alert
- `GET /api/system/health` — source status
- `WS: SIGNAL_ALERT` — real-time push

**Key States:**
- Loading: Skeleton placeholders for gauge + cards
- Empty: "No signals generated yet" with pipeline status hint
- Error: Alert banner with retry action
- Live: Pulsing dot on WS connection indicator; score animates on update

**Components (Spark Design):**
- `Card` — dimension score cards, health grid cells
- `Progress` / custom Gauge — resonance score visualization
- `Tag` / `Badge` — alert level (LEVEL_1=info, LEVEL_2=warning, LEVEL_3=critical)
- `Skeleton` — loading states
- `Alert` — error/degraded banners
- `Avatar` + status dot — source health indicators
- `Separator` — section dividers

---

### 4.2 GEX — Gamma Exposure Analysis (`/gex`)

**Purpose:** Deep-dive into options gamma exposure across 6 tracked symbols (SPX, SPY, QQQ, IWM, etc.).

**Layout:**

```
┌──────────────────────────────────────────────────────────────┐
│  Symbol Tabs: [SPX] [SPY] [QQQ] [IWM] [IWM] [AAPL]         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Key Levels Bar: Call Wall │ Zero Gamma │ Put Wall   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────┐  ┌────────────────────────┐    │
│  │  Strike Distribution    │  │  GEX History (90d)     │    │
│  │  (Bar chart: GEX/OI     │  │  (Line chart)          │    │
│  │   per strike)           │  │                        │    │
│  └─────────────────────────┘  └────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Alpha Factor History (area chart, 90d)              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- `GET /api/gex/{symbol}/dashboard-view` — BFF aggregation (single call, <10ms)
- `GET /api/gex/history?days=90` — SqueezeMetrics long history
- `GET /api/gex/alpha-history?days=90`

**Interactions:**
- Tab switch → refetch dashboard-view for selected symbol
- Hover on strike bars → tooltip with GEX value + OI count
- Brush on history chart → zoom time range

**Components:**
- `Tabs` — symbol selector
- `Card` — chart containers
- `Tag` — call wall (red), put wall (green), zero gamma (neutral)
- `Skeleton` — per-section loading

---

### 4.3 VIX — Volatility Term Structure (`/vix`)

**Purpose:** Monitor VIX spot, futures curve, and contango/backwardation state.

**Layout:**

```
┌──────────────────────────────────────────────────────────────┐
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ VIX Spot │ │ VX1      │ │ VX2      │ │ Term State   │   │
│  │  14.2    │ │ 15.1     │ │ 16.3     │ │ CONTANGO ↑   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Term Structure Curve (line: spot → VX1 → VX2 → ...)│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────┐  ┌────────────────────────┐    │
│  │  VIX History (30d)      │  │  Panic Premium Gauge   │    │
│  │  (line + volume)        │  │  (radial)              │    │
│  └─────────────────────────┘  └────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- `GET /api/vix/latest`
- `GET /api/vix/term-structure`
- `GET /api/vix/history?days=30`

**Key Logic:**
- Term structure state badge: `contango` (green), `backwardation` (red), `flat` (neutral)
- Panic premium > threshold → warning highlight

---

### 4.4 Crypto — Derivatives Monitor (`/crypto`)

**Purpose:** Track BTC funding rate, open interest, liquidation events, and leverage ratio.

**Layout:**

```
┌──────────────────────────────────────────────────────────────┐
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ Funding  │ │ OI       │ │ OI Δ1h   │ │ Leverage     │   │
│  │ Rate     │ │ (BTC)    │ │          │ │ Ratio (ELR)  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Funding Rate History (line, anomaly bands shaded)   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────┐  ┌────────────────────────┐    │
│  │  OI Change (bar chart)  │  │  Event Flags           │    │
│  │                         │  │  • Liquidation Spike   │    │
│  │                         │  │  • Funding Anomaly     │    │
│  │                         │  │  • OI Crash            │    │
│  │                         │  │  • Leverage Cleanup    │    │
│  └─────────────────────────┘  └────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- `GET /api/crypto/latest`
- `GET /api/crypto/history`

**Key States:**
- Boolean flags (liquidation_spike, funding_anomaly, oi_crash, leverage_cleanup) → `Tag` with severity color
- Funding rate anomaly → shaded region on chart

---

### 4.5 Dark Pool — Institutional Flow (`/darkpool`)

**Purpose:** Visualize dark pool activity metrics: DIX, short ratio, divergence signals, EMA crossovers.

**Layout:**

```
┌──────────────────────────────────────────────────────────────┐
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ DIX      │ │ Short    │ │ 20d Slope│ │ 60d Slope    │   │
│  │ Value    │ │ Ratio    │ │          │ │              │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  DIX + EMA(5/20) Overlay (line chart)                │   │
│  │  Zero-cross annotations                              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────┐  ┌────────────────────────┐    │
│  │  Net Volume (bar)       │  │  Signal Flags          │    │
│  │                         │  │  • Divergence          │    │
│  │                         │  │  • DBMF MA5 Recovery   │    │
│  │                         │  │  • Zero Cross          │    │
│  │                         │  │  • Momentum Reversal   │    │
│  └─────────────────────────┘  └────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- `GET /api/darkpool/latest`
- `GET /api/darkpool/history`

---

### 4.6 Signals — Alert History & Management (`/signals`)

**Purpose:** Browse, filter, acknowledge, and review outcomes of generated resonance alerts.

**Layout:**

```
┌──────────────────────────────────────────────────────────────┐
│  Filters: [Level ▼] [Outcome ▼] [Date Range] [Search]       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Signal Table                                        │   │
│  │  Time │ Score │ GEX │ VIX │ Crypto │ Dark │ Level │  │   │
│  │  ─────┼───────┼─────┼─────┼────────┼──────┼───────│  │   │
│  │  ...  │ 3.2   │ 1.8 │ 0.9 │  0.5   │  0.0 │ L2   │  │   │
│  │  ...  │ 2.1   │ 1.2 │ 0.4 │  0.5   │  0.0 │ L1   │  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Signal Detail Drawer (on row click)                 │   │
│  │  • Score breakdown radar chart                       │   │
│  │  • Hawkes branching ratio                            │   │
│  │  • Details JSON (formatted)                          │   │
│  │  • Outcome: profit/loss + forward return             │   │
│  │  • [Acknowledge] button                              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Pagination: [< 1 2 3 ... >]                                │
└──────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- `GET /api/signals/history?level=&outcome=&page=&limit=`
- `POST /api/signals/{id}/acknowledge`

**Components:**
- `DataTable` / `Table` — signal list
- `Drawer` — detail panel
- `Select` — level/outcome filters
- `Pagination` — page navigation
- `Button` — acknowledge action
- `Tag` — level badge, outcome badge
- `RadarChart` — score breakdown in drawer

---

### 4.7 Analysis — LLM-Augmented Insights (`/analysis`)

**Purpose:** Display AI-generated market analysis combining quantitative signals with LLM reasoning.

**Layout:**

```
┌──────────────────────────────────────────────────────────────┐
│  [Request Analysis] button                                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Latest Analysis Card                                │   │
│  │  • Timestamp + confidence score                      │   │
│  │  • Multi-paragraph formatted analysis text           │   │
│  │  • Source citations / dimension references           │   │
│  │  • Verification status (multi-verify)                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Analysis History (collapsible list)                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- `GET /api/analysis/latest`
- `POST /api/analysis/generate`
- `WS: ANALYSIS_COMPLETE`

**States:**
- Generating: `Spinner` + "Analyzing multi-source data..." progress text
- Cached: "Cached result" badge with age

---

### 4.8 System — Health & Diagnostics (`/system`)

**Purpose:** Monitor pipeline health, fetcher status, and system metrics.

**Layout:**

```
┌──────────────────────────────────────────────────────────────┐
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ Uptime   │ │ Version  │ │ Pipeline │ │ Last Cycle   │   │
│  │ 14d 6h   │ │ 3.1.0    │ │ RUNNING  │ │ 2m ago       │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Source Health Table                                 │   │
│  │  Name │ Status │ Mock? │ Mock Reason │ Retry Count   │   │
│  │  ─────┼────────┼───────┼─────────────┼─────────────  │   │
│  │  CBOE │ 🟢     │ No    │ —           │ 0            │   │
│  │  FINRA│ 🟡     │ Yes   │ fetch_failed│ 2            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────┐  ┌────────────────────────┐    │
│  │  Collection Report      │  │  Prometheus Metrics    │    │
│  │  (last cycle summary)   │  │  (link/embed)          │    │
│  └─────────────────────────┘  └────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- `GET /api/system/health`
- `GET /api/system/status`
- `GET /api/metrics`

**Components:**
- `Table` — source health
- `Tag` — status (online=green, degraded=yellow, offline=red)
- `Card` — stat tiles
- `Progress` — pipeline phase indicator

---

### 4.9 Settings — Runtime Configuration (`/settings`)

**Purpose:** View/edit system_config key-value pairs and pipeline parameters.

**Layout:**

```
┌──────────────────────────────────────────────────────────────┐
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Configuration Form                                  │   │
│  │  • Alert thresholds (LEVEL_1/2/3 score cutoffs)     │   │
│  │  • Pipeline interval                                 │   │
│  │  • Notification toggle                               │   │
│  │  • Data retention days                               │   │
│  │  [Save Changes]                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Raw Config Table (system_config KV store)           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- `GET /api/config`
- `PUT /api/config`

**Components:**
- `Field` + `Input` — numeric thresholds
- `Switch` — toggles
- `Button` — save
- `Table` — raw KV display
- `Toast` — save confirmation

---

## 5. App Shell & Navigation

### 5.1 Sidebar Navigation

```
┌─────────────────────┐
│  MSR Logo           │
│  ─────────────────  │
│  ◉ Dashboard        │
│  ◈ GEX              │
│  ◈ VIX              │
│  ◈ Crypto           │
│  ◈ Dark Pool        │
│  ─────────────────  │
│  ◈ Signals          │
│  ◈ Analysis         │
│  ─────────────────  │
│  ◈ System           │
│  ◈ Settings         │
│  ─────────────────  │
│  WS: ● Connected    │
│  v3.1.0             │
└─────────────────────┘
```

- Collapsible on tablet (icon-only mode)
- Active route highlighted
- WS connection status pinned to bottom

### 5.2 TopBar

- Page title (dynamic per route)
- Last data update timestamp (auto-refresh display)
- Alert level badge (shows highest unacknowledged level)
- Theme toggle (light/dark — neutral theme default)

---

## 6. Real-Time Data Strategy

| Concern | Approach |
|---------|----------|
| Connection | Single WebSocket to `/ws`, auto-reconnect with exponential backoff |
| Subscription | Subscribe to all topics; filter client-side per active view |
| Optimistic UI | Score gauge animates on `SIGNAL_ALERT`; table prepends on new signal |
| Staleness | "Last updated" timestamp per card; >5min → stale warning badge |
| Offline | Banner: "Real-time connection lost. Showing cached data." + retry button |

**Key WS Topics consumed:**
- `SIGNAL_ALERT` → Dashboard gauge + Signals table
- `SCORING_COMPLETE` → Dashboard dimension cards
- `DATA_FETCH_COMPLETE` → System source health
- `DATA_MOCK_FALLBACK` → System warning toast
- `PIPELINE_CYCLE_COMPLETE` → TopBar "last update" timestamp

---

## 7. Design System & Tokens

| Token | Usage |
|-------|-------|
| Color: semantic | success (online/profit), warning (degraded/LEVEL_2), danger (offline/LEVEL_3/loss), info (LEVEL_1) |
| Color: chart palette | 6-color categorical for dimensions; sequential for heatmaps |
| Spacing | 4px base grid; card padding 16/24px; section gap 24/32px |
| Radius | `rounded="square"` buttons (per Bible); cards 8px |
| Typography | Mono for numeric values (scores, prices); sans for labels |
| Elevation | Cards: subtle border + shadow-sm; Drawer/Dialog: shadow-lg |

---

## 8. Responsive Behavior

| Breakpoint | Layout Change |
|------------|---------------|
| ≥1280px (Desktop) | Full sidebar + 2-3 column grid for cards/charts |
| 768–1279px (Tablet) | Collapsed icon sidebar; 2-column grid; drawer full-width |
| <768px (Mobile) | Hidden sidebar → hamburger; single column; charts stack vertically |

Priority: Desktop-first. Tablet functional. Mobile readable but not optimized for trading.

---

## 9. Accessibility

- All charts have `aria-label` summaries
- Color-coded statuses also use icon/text (not color-only)
- Keyboard navigation for table rows, tabs, filters
- Focus rings on interactive elements (Spark Design default)
- Alert level conveyed via text badge, not just color

---

## 10. Component Inventory (Spark Design Mapping)

| Spark Component | Usage Locations |
|-----------------|-----------------|
| `Card` | Stat tiles, chart containers, analysis cards |
| `Tabs` | GEX symbol selector, section tabs |
| `Table` / `DataTable` | Signals history, source health, config KV |
| `Tag` / `Badge` | Alert levels, term structure state, status dots |
| `Button` | Actions (acknowledge, generate, save, retry) |
| `Drawer` | Signal detail panel |
| `Dialog` | Confirmations (acknowledge, config reset) |
| `Select` | Filters (level, outcome, date range) |
| `Input` / `Field` | Settings form, search |
| `Switch` | Config toggles |
| `Progress` | Pipeline phase, loading bars |
| `Spinner` | Analysis generation, chart loading |
| `Skeleton` | Initial page load placeholders |
| `Alert` | Error banners, stale data warnings |
| `Toast` | Save confirmations, mock fallback notices |
| `Tooltip` | Chart data points, metric explanations |
| `Separator` | Section dividers |
| `ScrollArea` | Long signal history, analysis text |
| `Pagination` | Signals table |
| `Breadcrumb` | Drill-down navigation (optional) |
| `SidebarMenu` | App shell navigation |
| `DropdownMenu` | TopBar actions, row context menu |

---

## 11. API Contract Summary (Existing — No Changes)

| Endpoint | Method | Consumed By |
|----------|--------|-------------|
| `/api/dashboard` | GET | Dashboard |
| `/api/gex/{symbol}/dashboard-view` | GET | GEX page |
| `/api/gex/history` | GET | GEX page |
| `/api/gex/alpha-history` | GET | GEX page |
| `/api/vix/latest` | GET | VIX page |
| `/api/vix/term-structure` | GET | VIX page |
| `/api/vix/history` | GET | VIX page |
| `/api/crypto/latest` | GET | Crypto page |
| `/api/crypto/history` | GET | Crypto page |
| `/api/darkpool/latest` | GET | Dark Pool page |
| `/api/darkpool/history` | GET | Dark Pool page |
| `/api/signals/latest` | GET | Dashboard |
| `/api/signals/history` | GET | Signals page |
| `/api/signals/{id}/acknowledge` | POST | Signals page |
| `/api/analysis/latest` | GET | Analysis page |
| `/api/analysis/generate` | POST | Analysis page |
| `/api/system/health` | GET | Dashboard, System |
| `/api/system/status` | GET | System page |
| `/api/config` | GET/PUT | Settings page |
| `/api/metrics` | GET | System page |
| `/ws` | WS | Global (real-time) |

---

## 12. Milestones

| Phase | Scope | Deliverable |
|-------|-------|-------------|
| **P1** | App Shell + Dashboard + Signals | Core monitoring loop functional |
| **P2** | GEX + VIX + Crypto + Dark Pool | Full dimension drill-down |
| **P3** | Analysis + System + Settings | Complete feature parity |
| **P4** | Polish: animations, responsive, a11y | Production-ready |

---

## 13. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | Should the gauge be a radial arc or a horizontal bar? | Dashboard hero visual |
| 2 | Do we need chart export (PNG/CSV) for analyst workflows? | Chart component choice |
| 3 | Should Analysis page support streaming (SSE) for LLM output? | Real-time architecture |
| 4 | Is dark mode required for v1 or deferred? | Token setup effort |
| 5 | Should signal acknowledge require confirmation dialog? | Interaction design |

---

## 14. Success Criteria

- [ ] Dashboard loads with real data in <2s (cold), <500ms (warm)
- [ ] WebSocket reconnects within 5s of disconnect without user action
- [ ] All 9 pages render correctly at 1280px and 768px widths
- [ ] Signal acknowledge flow completes in ≤2 clicks
- [ ] Zero `any` types in TypeScript; all API responses typed
- [ ] Spark Design tokens used for all colors/spacing (no hard-coded hex)
- [ ] Lighthouse accessibility score ≥ 90
