# Frontend Development Guide

## Current State (Iteration 1)

**Optimization Level**: 85-90%
**Status**: Nearly optimal, but not yet fully optimal

## Architecture

### File Structure
```
web/
├── index.html          # Single-page application (2761 lines)
├── implementation_report.html  # Progress report
└── (no external JS/CSS files - all inline)
```

### Key Components

1. **Token Selector** (`initTokenSelector()`)
   - Renders 8 token pills
   - Handles click and keyboard events
   - Updates active state

2. **KPI Bar** (`renderKpiBar(token)`)
   - Displays 4 metrics
   - Updates on token switch

3. **Dashboard Grid** (HTML structure)
   - 2x4 responsive grid
   - 8 cards with consistent styling

4. **Card Renderers** (8 functions)
   - `renderOverviewCard(token)`
   - `renderTrendCard(token)`
   - `renderHeatmapCard(token)` - placeholder
   - `renderDailyBarCard(token)` - placeholder
   - `renderTgeCard(token)`
   - `renderSankeyCard(token)`
   - `renderRankingCard(token)`
   - `renderDailyTableCard(token)` - placeholder

## Data Flow

```
loadData()
  ↓
fetch latest_data.json
  ↓
initTokenSelector()
  ↓
renderTokenDashboard(selectedToken)
  ↓
[renderKpiBar, renderOverviewCard, renderTrendCard, ...]
```

## Styling System

### CSS Variables
```css
--bg: #F0F4F8
--bg-card: #FFFFFF
--text: #0F172A
--text-secondary: #475569
--accent: #1E40AF
--inflow: #16A34A
--outflow: #DC2626
--net-positive: #1E40AF
--net-negative: #DC2626
```

### Key Classes
- `.token-selector` - Token pills container
- `.token-pill` - Individual token button
- `.kpi-bar` - Metrics bar
- `.kpi-item` - Individual metric
- `.dashboard-grid` - Card grid
- `.dashboard-card` - Individual card
- `.exchange-table` - Table styling
- `.card-empty` - Empty state
- `.card-loading` - Loading state

## Adding a New Card

1. **Add HTML structure** in `<div class="dashboard-grid">`
```html
<div class="dashboard-card" id="card-new">
  <div class="card-header">
    <h3>New Card Title</h3>
    <button class="expand-btn">⛶</button>
  </div>
  <div class="card-content" id="content-new">
    <!-- Content here -->
  </div>
</div>
```

2. **Create render function**
```javascript
function renderNewCard(token) {
  const data = rawData.tokens[token];
  if (!data) return;

  // Your rendering logic
  document.getElementById('content-new').innerHTML = html;
}
```

3. **Call in `renderTokenDashboard()`**
```javascript
function renderTokenDashboard(token) {
  // ... existing code ...
  renderNewCard(token);
}
```

## Completing Data-Dependent Cards

### Heatmap Card
**Requirements**:
- Daily aggregated data in `data/history/YYYY-MM-DD.jsonl`
- Format: `{ date, token, inflow, outflow, net_flow }`

**Implementation**:
```javascript
function renderHeatmapCard(token) {
  // Load daily data
  const dailyData = await loadDailyData(token);

  // Create heatmap with Plotly
  const data = [{
    type: 'heatmap',
    z: dailyData.map(d => d.net_flow),
    x: dailyData.map(d => d.date),
    y: ['Net Flow'],
    colorscale: 'RdYlGn'
  }];

  Plotly.newPlot('heatmap-mini', data, layout);
}
```

### Daily Bar Card
**Requirements**: Same as Heatmap

**Implementation**:
```javascript
function renderDailyBarCard(token) {
  const dailyData = await loadDailyData(token);

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: dailyData.map(d => d.date),
      datasets: [
        { label: 'Inflow', data: dailyData.map(d => d.inflow) },
        { label: 'Outflow', data: dailyData.map(d => d.outflow) }
      ]
    }
  });
}
```

### Daily Table Card
**Requirements**: Same as Heatmap

**Implementation**:
```javascript
function renderDailyTableCard(token) {
  const dailyData = await loadDailyData(token);

  let html = '<table class="exchange-table"><thead>...</thead><tbody>';
  dailyData.forEach(d => {
    html += `<tr>
      <td>${d.date}</td>
      <td>${formatNumber(d.inflow)}</td>
      <td>${formatNumber(d.outflow)}</td>
      <td>${formatNumber(d.net_flow)}</td>
    </tr>`;
  });
  html += '</tbody></table>';

  document.getElementById('content-daily-table').innerHTML = html;
}
```

## Testing Checklist

### Cross-Browser Testing
- [ ] Chrome 90+ (Windows, macOS, Linux)
- [ ] Firefox 88+ (Windows, macOS, Linux)
- [ ] Safari 14+ (macOS, iOS)
- [ ] Edge 90+ (Windows)

### Mobile Device Testing
- [ ] iPhone (Safari)
- [ ] iPad (Safari)
- [ ] Android Phone (Chrome)
- [ ] Android Tablet (Chrome)

### Performance Testing
- [ ] Load time < 2s
- [ ] Token switch < 500ms
- [ ] Chart render < 1s
- [ ] Memory usage < 100MB
- [ ] No memory leaks

### Accessibility Testing
- [ ] Keyboard navigation works
- [ ] Screen reader compatible
- [ ] ARIA labels correct
- [ ] Color contrast ratio > 4.5:1
- [ ] Focus indicators visible

## Performance Optimization

### Current Optimizations
- ✅ Debounced token switching
- ✅ Chart instance reuse (destroy old, create new)
- ✅ Lazy loading for charts
- ✅ Minimal DOM manipulation

### Future Optimizations
- [ ] Virtual scrolling for large tables
- [ ] Web Workers for data processing
- [ ] Service Worker for offline support
- [ ] Code splitting (if moving to build system)

## Known Issues

1. **Old Code References**
   - Some old functions (renderTokenCards, renderSankeyChart, etc.) still exist
   - They're not called by new system, but could be removed for cleanup

2. **Inline Styles**
   - Some components still use inline styles
   - Should be moved to CSS classes for consistency

3. **Error Handling**
   - Basic error handling in place
   - Could be more comprehensive

## Next Steps

### Iteration 2 Goals
1. Implement daily data aggregation (backend)
2. Complete 3 data-dependent cards
3. Cross-browser testing
4. Mobile device testing

### Iteration 3 Goals
1. Performance optimization
2. Full accessibility audit
3. Advanced features (dark mode, exports)
4. Code cleanup (remove old functions)

## Contributing

When making changes:
1. Test in multiple browsers
2. Check responsive design
3. Verify keyboard navigation
4. Update this documentation
5. Run `scripts/test_frontend.js` and `scripts/test_ui_ux.sh`

## Resources

- Chart.js Docs: https://www.chartjs.org/docs/
- Plotly Docs: https://plotly.com/javascript/
- MDN Web Docs: https://developer.mozilla.org/
- WCAG Guidelines: https://www.w3.org/WAI/WCAG21/quickref/

---

**Last Updated**: March 17, 2026 (Iteration 1)
