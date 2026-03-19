import re

with open("web/cosmic.html", "r") as f:
    content = f.read()

new_style = """<style>
  :root {
    /* Cosmic Latte / Tech White Glassmorphism Theme */
    --bg: #FAF8F5; /* Cosmic Latte Tint */
    --bg-overlay: rgba(255, 255, 255, 0.6);
    --bg-card: rgba(255, 255, 255, 0.85);
    --bg-card-hover: rgba(255, 255, 255, 1);
    --text: #111827;
    --text-secondary: #4B5563;
    --accent: #2563EB;
    --accent-secondary: #4F46E5;
    --accent-light: rgba(37, 99, 235, 0.1);
    --border: rgba(0, 0, 0, 0.06);
    --inflow: #059669; /* Tech Green */
    --outflow: #DC2626; /* Tech Red */
    --net-positive: #059669;
    --net-negative: #DC2626;
    --alert-bg: rgba(220, 38, 38, 0.05);
    --alert-border: rgba(220, 38, 38, 0.2);
    --shadow-sm: 0 4px 12px rgba(0, 0, 0, 0.03), inset 0 1px 0 rgba(255,255,255,1);
    --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255,255,255,1);
    --shadow-lg: 0 16px 48px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,1);
    --font-heading: 'Inter', sans-serif;
    --font-body: 'Inter', sans-serif;
    --font-mono: 'Roboto Mono', monospace;
    --glass-bg: rgba(250, 248, 245, 0.7);
    --glass-border: rgba(0, 0, 0, 0.05);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: var(--font-body);
    background: var(--bg);
    background-attachment: fixed;
    color: var(--text);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    position: relative;
    background-image: 
      radial-gradient(circle at 15% 50%, rgba(37, 99, 235, 0.04) 0%, transparent 50%),
      radial-gradient(circle at 85% 30%, rgba(5, 150, 105, 0.04) 0%, transparent 50%);
  }

  /* Header & Nav */
  .top-nav {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--glass-bg);
    backdrop-filter: blur(24px) saturate(150%);
    -webkit-backdrop-filter: blur(24px) saturate(150%);
    border-bottom: 1px solid var(--glass-border);
    box-shadow: var(--shadow-sm);
    padding: 16px 24px;
  }

  .nav-content {
    max-width: 1600px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
  }

  .nav-brand {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .logo-dot {
    width: 10px;
    height: 10px;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-secondary) 100%);
    border-radius: 50%;
    animation: pulse-latte 2s infinite;
    box-shadow: 0 0 12px rgba(37, 99, 235, 0.4);
  }

  @keyframes pulse-latte {
    0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.4); }
    70% { box-shadow: 0 0 0 8px rgba(37, 99, 235, 0); }
    100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
  }

  h1 {
    font-family: var(--font-heading);
    font-size: clamp(18px, 2vw, 24px);
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #111827 0%, #374151 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .live-badge {
    font-size: 10px;
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 99px;
    background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%);
    color: white;
    border: none;
    letter-spacing: 0.5px;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
    animation: pulse-red 2s infinite;
  }

  @keyframes pulse-red {
    0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
    70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
    100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
  }

  .timestamp {
    font-size: 13px;
    color: var(--text-secondary);
    font-weight: 500;
  }

  .container {
    max-width: 1600px;
    margin: 0 auto;
    padding: 32px 24px;
  }

  /* Filters */
  .filters {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
    flex-wrap: wrap;
    align-items: center;
  }

  .filter-group {
    display: flex;
    align-items: center;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 6px 16px 6px 14px;
    transition: all 0.2s;
    box-shadow: var(--shadow-sm);
  }

  .filter-group:hover {
    border-color: var(--accent);
    box-shadow: var(--shadow-md);
  }

  .filter-group label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    margin-right: 8px;
  }

  .filter-group select {
    border: none;
    background: transparent;
    font-size: 14px;
    color: var(--text);
    font-family: var(--font-body);
    font-weight: 600;
    cursor: pointer;
    outline: none;
    appearance: none;
    padding-right: 18px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%234B5563'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right center;
    background-size: 14px;
  }

  .filter-group select option {
    background: #FFFFFF;
    color: var(--text);
  }

  /* Summary Cards */
  .summary-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px;
    margin-bottom: 32px;
  }

  .summary-card {
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: var(--shadow-md);
    position: relative;
    overflow: hidden;
  }

  .summary-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0; width: 4px;
    background: linear-gradient(180deg, var(--accent) 0%, var(--accent-secondary) 100%);
    opacity: 0.8;
  }

  .summary-card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
    border-color: rgba(37, 99, 235, 0.2);
  }

  .summary-card .label {
    font-size: 13px;
    font-weight: 700;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .summary-card .value {
    font-family: var(--font-heading);
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: var(--text);
  }

  .summary-card .value.positive { 
    background: linear-gradient(135deg, #059669 0%, #10B981 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .summary-card .value.negative { 
    background: linear-gradient(135deg, #DC2626 0%, #EF4444 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  /* Tabs */
  .tab-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 32px;
    background: rgba(0,0,0,0.03);
    padding: 6px;
    border-radius: 12px;
    overflow-x: auto;
    scrollbar-width: none;
    border: 1px solid var(--border);
  }
  .tab-bar::-webkit-scrollbar { display: none; }

  .tab-btn {
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
    font-family: var(--font-body);
    border: none;
    background: transparent;
    color: var(--text-secondary);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    white-space: nowrap;
  }

  .tab-btn:hover {
    color: var(--text);
    background: rgba(255,255,255,0.5);
  }

  .tab-btn.active {
    color: var(--accent);
    background: #FFFFFF;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  }

  .tab-panel {
    display: none;
    animation: fadeIn 0.4s ease-out;
  }
  .tab-panel.active { display: block; }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  h2 {
    font-family: var(--font-heading);
    font-size: 20px;
    font-weight: 800;
    margin-bottom: 24px;
    color: var(--text);
    letter-spacing: -0.3px;
  }

  /* Token Cards */
  .token-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(540px, 1fr));
    gap: 24px;
  }

  .token-card {
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: var(--shadow-md);
    cursor: pointer;
    position: relative;
    overflow: hidden;
  }

  .token-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, var(--accent) 0%, var(--accent-secondary) 100%);
    opacity: 0;
    transition: opacity 0.4s ease;
  }

  .token-card:hover {
    border-color: rgba(37, 99, 235, 0.3);
    transform: translateY(-6px);
    box-shadow: var(--shadow-lg);
  }

  .token-card:hover::before {
    opacity: 1;
  }

  .token-card.alert {
    border-color: var(--alert-border);
    box-shadow: 0 0 0 1px var(--alert-border), var(--shadow-md);
  }

  .token-card.alert::before {
    background: linear-gradient(90deg, #DC2626 0%, #EF4444 100%);
    opacity: 1;
  }

  .token-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 20px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 16px;
  }

  .token-name {
    font-family: var(--font-heading);
    font-size: 24px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.5px;
  }

  .token-chain {
    font-size: 11px;
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 6px;
    background: rgba(0,0,0,0.04);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    vertical-align: super;
    margin-left: 8px;
  }

  .alert-badge {
    display: inline-block;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 6px;
    background: var(--alert-bg);
    border: 1px solid var(--alert-border);
    color: #DC2626;
    margin-left: 8px;
    font-weight: 800;
    vertical-align: super;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .token-net {
    font-family: var(--font-mono);
    font-size: 20px;
    font-weight: 700;
    display: block;
    margin-bottom: 4px;
  }

  .chart-container {
    position: relative;
    height: 200px;
    margin-bottom: 24px;
  }

  /* Tables */
  .exchange-table, .ranking-table, .daily-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 13px;
  }

  .exchange-table th, .ranking-table th, .daily-table th {
    text-align: right;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    background: rgba(0,0,0,0.02);
    transition: background 0.2s;
  }
  
  .exchange-table th:first-child, .ranking-table th:first-child, .daily-table th:first-child {
    text-align: left;
    border-top-left-radius: 8px;
  }
  .exchange-table th:last-child, .ranking-table th:last-child, .daily-table th:last-child {
    border-top-right-radius: 8px;
  }

  .exchange-table th.sortable, .ranking-table th.sortable, .daily-table th.sortable {
    cursor: pointer;
    user-select: none;
  }

  .exchange-table th.sortable::after, .ranking-table th.sortable::after, .daily-table th.sortable::after {
    content: ' \21D5';
    opacity: 0.3;
    font-size: 10px;
    margin-left: 4px;
  }

  .exchange-table th.sortable.sort-asc::after, .ranking-table th.sortable.sort-asc::after, .daily-table th.sortable.sort-asc::after {
    content: ' \25B2';
    opacity: 0.8;
  }

  .exchange-table th.sortable.sort-desc::after, .ranking-table th.sortable.sort-desc::after, .daily-table th.sortable.sort-desc::after {
    content: ' \25BC';
    opacity: 0.8;
  }

  .exchange-table td, .ranking-table td, .daily-table td {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    font-weight: 600;
    color: var(--text);
    text-align: right;
    font-family: var(--font-mono);
  }
  
  .exchange-table td:first-child, .ranking-table td:first-child, .daily-table td:first-child {
    text-align: left;
    font-family: var(--font-body);
  }

  .exchange-table tr:nth-child(even) td, .ranking-table tr:nth-child(even) td, .daily-table tr:nth-child(even) td {
    background-color: transparent;
  }

  .exchange-table tr:hover td, .ranking-table tr:hover td, .daily-table tr:hover td {
    background-color: rgba(37, 99, 235, 0.04);
  }

  .exchange-table tr:last-child td, .ranking-table tr:last-child td, .daily-table tr:last-child td {
    border-bottom: none;
  }

  .ranking-table td.positive { color: var(--net-positive); }
  .ranking-table td.negative { color: var(--net-negative); }

  /* Section Cards */
  .section-card {
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 32px;
    box-shadow: var(--shadow-lg);
    position: relative;
    overflow: hidden;
  }

  .section-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, var(--accent) 0%, var(--accent-secondary) 100%);
    opacity: 0.8;
  }

  /* Sankey */
  #sankey-chart { width: 100%; min-height: 500px; }
  .sankey-section { position: relative; overflow: hidden; border-radius: 12px; }
  #particle-canvas {
    position: absolute;
    inset: 0;
    pointer-events: none;
    display: none;
    z-index: 2;
  }

  /* Chart Styles & Containers */
  .trend-chart-container { position: relative; height: 360px; }
  .tge-chart-container { position: relative; height: 360px; }
  .daily-chart-container { position: relative; height: 320px; }

  .zoom-reset-btn { 
    position:absolute; 
    top:8px; 
    right:8px; 
    z-index:10; 
    padding:6px 12px; 
    font-size:12px; 
    font-weight: 600;
    background: #FFFFFF; 
    border: 1px solid var(--border); 
    border-radius: 6px; 
    cursor:pointer; 
    color: var(--text-secondary);
    box-shadow: var(--shadow-sm);
    transition: all 0.2s;
  }
  .zoom-reset-btn:hover { 
    background: #F3F4F6; 
    color: var(--text);
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
  }

  @media (max-width: 768px) {
    .token-grid { grid-template-columns: 1fr; }
    .summary-row { grid-template-columns: 1fr 1fr; }
    .nav-content { flex-direction: column; align-items: flex-start; }
    .top-nav { position: relative; }
  }

  /* ── Token Selector Pills ────────────────────────────────────────── */
  .token-selector {
    display: flex;
    gap: 12px;
    padding: 24px;
    background: var(--glass-bg);
    backdrop-filter: blur(24px) saturate(150%);
    -webkit-backdrop-filter: blur(24px) saturate(150%);
    border-bottom: 1px solid var(--glass-border);
    overflow-x: auto;
    scrollbar-width: thin;
    position: relative;
    z-index: 1;
    box-shadow: var(--shadow-sm);
  }

  .token-selector::-webkit-scrollbar {
    height: 6px;
  }

  .token-selector::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 3px;
  }

  .token-selector::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.15);
    border-radius: 3px;
  }
  
  .token-selector::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.25);
  }

  .token-pill {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 20px;
    border: 1px solid var(--border);
    border-radius: 99px;
    background: #FFFFFF;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    white-space: nowrap;
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
    box-shadow: var(--shadow-sm);
  }

  .token-pill:hover {
    background: #FFFFFF;
    border-color: rgba(37, 99, 235, 0.3);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  .token-pill.active {
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-secondary) 100%);
    border-color: transparent;
    color: #FFFFFF;
    box-shadow: 0 8px 24px rgba(37, 99, 235, 0.3);
    transform: translateY(-2px);
  }

  .token-pill .token-chain {
    font-size: 10px;
    opacity: 0.8;
    text-transform: uppercase;
    background: none;
    border: none;
    padding: 0;
    margin: 0;
  }
  
  .token-pill.active .token-chain {
    color: rgba(255, 255, 255, 0.9);
  }

  /* ── KPI Bar ─────────────────────────────────────────────────────── */
  .kpi-bar {
    display: flex;
    justify-content: space-around;
    padding: 32px 24px;
    background: var(--bg-card);
    backdrop-filter: blur(24px) saturate(150%);
    -webkit-backdrop-filter: blur(24px) saturate(150%);
    border-bottom: 1px solid var(--border);
    position: relative;
    z-index: 1;
    box-shadow: var(--shadow-sm);
  }

  .kpi-item {
    text-align: center;
    border-right: 1px solid var(--border);
    padding: 0 32px;
    flex: 1;
    transition: transform 0.3s ease;
  }

  .kpi-item:hover {
    transform: translateY(-4px);
  }

  .kpi-item:last-child {
    border-right: none;
  }

  .kpi-label {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 8px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .kpi-value {
    font-size: 36px;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    margin-bottom: 6px;
    font-family: var(--font-heading);
    transition: all 0.3s ease;
    background: linear-gradient(135deg, #111827 0%, #4B5563 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .kpi-value.positive {
    background: linear-gradient(135deg, #059669 0%, #10B981 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .kpi-value.negative {
    background: linear-gradient(135deg, #DC2626 0%, #EF4444 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .kpi-change {
    font-size: 13px;
    color: var(--text-secondary);
    font-weight: 600;
    background: rgba(0,0,0,0.04);
    padding: 4px 12px;
    border-radius: 99px;
    display: inline-block;
  }

  /* ── Dashboard Grid ──────────────────────────────────────────────── */
  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 32px;
    padding: 40px 32px;
    max-width: 1600px;
    margin: 0 auto;
    position: relative;
    z-index: 1;
  }

  .dashboard-card {
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    padding: 32px;
    box-shadow: var(--shadow-md);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
  }

  .dashboard-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, var(--accent) 0%, var(--accent-secondary) 100%);
    opacity: 0.8;
    transition: opacity 0.4s ease;
  }

  .dashboard-card:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-6px);
    border-color: rgba(37, 99, 235, 0.2);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
  }

  .card-header h3 {
    font-size: 18px;
    font-weight: 800;
    color: var(--text);
    font-family: var(--font-heading);
    letter-spacing: -0.3px;
  }

  .expand-btn {
    background: #FFFFFF;
    border: 1px solid var(--border);
    cursor: pointer;
    font-size: 16px;
    color: var(--text-secondary);
    transition: all 0.3s ease;
    padding: 8px 12px;
    border-radius: 8px;
    font-weight: bold;
    box-shadow: var(--shadow-sm);
  }

  .expand-btn:hover {
    transform: scale(1.05);
    background: var(--bg-card-hover);
    color: var(--accent);
    border-color: var(--accent);
  }

  .card-content {
    min-height: 300px;
    position: relative;
  }
</style>"""

new_content = re.sub(r'<style>.*?</style>', new_style, content, flags=re.DOTALL)

script_update = """// Arkham Global Chart Styles (Cosmic Latte Theme)
Chart.defaults.color = '#6B7280';
Chart.defaults.font.family = "'Roboto Mono', monospace";
Chart.defaults.scale.grid.color = 'rgba(0, 0, 0, 0.05)';
Chart.defaults.scale.grid.borderColor = 'transparent';

let rawData = null;
let historyData = null;
let dailySummaryData = null;
let tgeNetflows = null;
let tgeChartData = null;

function formatNumber(n) {
  if (n === null || n === undefined) return 'N/A';
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(2) + 'K';
  const val = typeof n.toFixed === 'function' ? n.toFixed(2) : n;
  return val;
}

const ZOOM_OPTS = {
  pan: { enabled: true, mode: 'x' },
  zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' }
};

const TOOLTIP_OPTS = {
  mode: 'index', intersect: false,
  backgroundColor: 'rgba(255, 255, 255, 0.95)',
  titleColor: '#111827', bodyColor: '#4B5563',
  borderColor: 'rgba(0, 0, 0, 0.1)', borderWidth: 1,
  padding: 16, cornerRadius: 12,
  titleFont: { size: 13, family: "'Inter', sans-serif", weight: 'bold' },
  bodyFont: { size: 14, family: "'Roboto Mono', monospace" },
  usePointStyle: true,
  boxPadding: 8,"""

# We need to target the block starting with // Arkham Global Chart Styles to boxPadding
new_content = re.sub(r"// Arkham Global Chart Styles.*?boxPadding: \d+,", script_update, new_content, flags=re.DOTALL)


# Also need to replace colors inside chart scripts:
# 1. Update line chart fill
new_content = re.sub(r"backgroundColor: 'rgba\(16, 185, 129, 0\.1\)'", "backgroundColor: 'rgba(5, 150, 105, 0.15)'", new_content)
new_content = re.sub(r"backgroundColor: 'rgba\(239, 68, 68, 0\.1\)'", "backgroundColor: 'rgba(220, 38, 38, 0.15)'", new_content)
# 2. Update border color
new_content = re.sub(r"borderColor: '#10B981'", "borderColor: '#059669'", new_content)
new_content = re.sub(r"borderColor: '#EF4444'", "borderColor: '#DC2626'", new_content)
new_content = re.sub(r"backgroundColor: '#10B981'", "backgroundColor: '#059669'", new_content)
new_content = re.sub(r"backgroundColor: '#EF4444'", "backgroundColor: '#DC2626'", new_content)
# 3. Update Sankey colors
new_content = re.sub(r"rgba\(16, 185, 129, 0\.35\)", "rgba(5, 150, 105, 0.35)", new_content)
new_content = re.sub(r"rgba\(239, 68, 68, 0\.35\)", "rgba(220, 38, 38, 0.35)", new_content)

with open("web/cosmic.html", "w") as f:
    f.write(new_content)
