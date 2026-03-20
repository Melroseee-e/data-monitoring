# On-Chain Exchange Flow Monitor - User Guide

## Overview

A real-time dashboard for monitoring token transfers between centralized exchanges and users across Ethereum, BSC, and Solana networks.

## Features

### Token Selector
- **8 Tokens**: AZTEC, UAI, TRIA, SKR, BIRB, SPACE, GWEI, PUMP
- **Click** any token pill to view its dashboard
- **Keyboard Navigation**: Use Arrow keys (←/→) to switch tokens, Enter/Space to select

### KPI Bar
Displays 4 key metrics for the selected token:
1. **Total Inflow**: Tokens flowing into exchanges (selling pressure)
2. **Total Outflow**: Tokens leaving exchanges (accumulation)
3. **Net Flow**: Inflow - Outflow (positive = selling, negative = buying)
4. **TGE Cumulative**: Total net flow since Token Generation Event

### Dashboard Cards

#### 1. Real-time Flow Overview
- Table showing top 10 exchanges by activity
- Columns: Exchange, Inflow, Outflow, Net Flow
- Sorted by absolute net flow (largest first)

#### 2. 24h Trend
- Line chart showing last 24 hours of activity
- Green line: Inflow
- Red line: Outflow
- Hover to see exact values

#### 3. Historical Heatmap
- *Coming soon* - Requires daily aggregated data

#### 4. Daily Bar Chart
- *Coming soon* - Requires daily aggregated data

#### 5. TGE Cumulative Net Flow
- Line chart from Token Generation Event to today
- Shows cumulative exchange net flow over time
- Positive trend = selling pressure
- Negative trend = accumulation

#### 6. Flow Diagram
- Sankey diagram showing token ↔ exchange flows
- Green flows: Inflow (to exchanges)
- Red flows: Outflow (from exchanges)
- Width represents volume

#### 7. Exchange Ranking
- Top 10 exchanges by total volume
- Sorted by (Inflow + Outflow)

#### 8. Daily Data Table
- *Coming soon* - Requires daily aggregated data

## How to Use

### Basic Navigation
1. Open the dashboard in your browser
2. Click any token pill at the top to view its data
3. Scroll down to see all 8 dashboard cards
4. Hover over charts for detailed information

### Keyboard Shortcuts
- **Arrow Left (←)**: Previous token
- **Arrow Right (→)**: Next token
- **Enter / Space**: Select focused token
- **Tab**: Navigate between interactive elements

### Responsive Design
- **Desktop (>1280px)**: 2-column grid layout
- **Tablet (768-1280px)**: 1-column layout
- **Mobile (<768px)**: 1-column layout with horizontal scroll for token selector

## Data Sources

- **Latest Data**: Real-time data from last hour (`data/latest_data.json`)
- **Historical Data**: Hourly snapshots (`data/history_summary.json`)
- **TGE Data**: Cumulative flows since TGE (`data/tge_chart_data.json`)

## Update Frequency

- **Real-time Data**: Updated hourly via GitHub Actions
- **Last Updated**: Displayed in header (top right)

## Browser Support

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Accessibility

- ✅ Keyboard navigation
- ✅ ARIA labels
- ✅ Screen reader friendly
- ✅ High contrast colors

## Known Limitations

1. **Daily Cards**: Heatmap, Daily Bar, and Daily Table require daily aggregated data (not yet available)
2. **Historical Data**: Limited to data collected since system deployment
3. **Real-time**: Data updates hourly, not real-time streaming

## Troubleshooting

### No Data Showing
- Check "Last Updated" timestamp in header
- Refresh the page (Ctrl+R / Cmd+R)
- Check browser console for errors (F12)

### Charts Not Loading
- Ensure JavaScript is enabled
- Check internet connection (charts use CDN libraries)
- Try a different browser

### Slow Performance
- Close other browser tabs
- Clear browser cache
- Use a modern browser

## Technical Details

- **Framework**: Vanilla JavaScript (no framework)
- **Charts**: Chart.js (line charts), Plotly (Sankey diagrams)
- **Styling**: Custom CSS with CSS Grid
- **File Size**: ~83 KB (optimized)

## Feedback

For issues or feature requests, please contact the development team or open an issue in the project repository.

---

**Version**: 1.0 (Iteration 1)
**Last Updated**: March 17, 2026
