# SPANDANA — Frontend

Premium React dashboard for the **SPANDANA** AI-powered predictive-maintenance
platform. Streams sensor telemetry, surfaces Liquid Neural Network (LTC)
predictions, and renders auditable AI maintenance reports across the fleet.

## Stack

React 19 · Vite 6 · TypeScript · Tailwind CSS · React Router 7 · Framer Motion ·
Recharts · Axios · Lucide React. UI primitives follow the shadcn/ui convention
(cva + `cn` merge) and are hand-built (no CLI generation step required).

## Getting started

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Production build / preview:

```bash
npm run build
npm run preview
```

## Backend

Services in `src/services/spandanaService.ts` call the backend at
`http://localhost:8000` (`GET /predict`, `/history`, `/report`, `/stream`,
`/machines`, `/alerts`) and **transparently fall back to realistic mock data**
when it's offline — the navbar shows "Live" vs "Demo Mode" accordingly. The API
base URL is configurable at runtime from the Settings page (persisted to
localStorage).

The TypeScript interfaces in `src/types/index.ts` mirror the real backend JSON
Schema contracts (`backend/schema/model_prediction.json`,
`backend/schemas/sensor_input.json`) field-for-field, so live data flows through
without remapping.

## Design notes

- **Theme**: light + dark, driven entirely by CSS variables in `src/index.css`
  and a `dark` class on `<html>`. Persisted to localStorage; applied pre-paint
  to avoid a flash. Toggle lives in the navbar.
- **Typography**: an editorial serif system — DM Serif Display for headings,
  Newsreader as the body serif, Inter for tabular numerics.
- **Model**: this UI is **LTC-only**, matching the actual codebase (the LSTM
  baseline was intentionally removed). The Predictions page shows a rich
  LNN-only detail panel plus the model's *real measured* metrics — no fabricated
  comparison benchmark.

## Structure

```
src/
  components/
    layout/     AppLayout, Sidebar, Navbar, Footer, PageTransition, navConfig
    ui/         Button, Card, Modal, StatusBadge, ProgressBar, SearchBar,
                ThemeToggle, NotificationBell, ProfileMenu, States, CounterStat,
                PageHeader, LoadingSkeleton
    features/   HealthCard, MachineCard, MachineTable, SensorChart, HealthGauge,
                PredictionCard, ModelInfoCard, HistoryTable, HistoryTimeline,
                ReportCard, AlertCard
  pages/        Dashboard, Machines, MachineDetail, LiveMonitoring, Predictions,
                History, Reports, Settings, NotFound
  services/     api (axios), spandanaService (fetch + fallback), mockData
  hooks/        useTheme, useClock, useStream, useMachines, useMediaQuery
  context/      ThemeContext
  types/        shared interfaces (mirror backend schema)
  utils/        cn, format, status
```
