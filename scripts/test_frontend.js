// Frontend Testing Script - No Browser Focus
const http = require('http');

// Test if server is running
const options = {
  hostname: 'localhost',
  port: 8888,
  path: '/index.html',
  method: 'GET'
};

const req = http.request(options, (res) => {
  console.log('✓ Server is running');
  console.log('Status Code:', res.statusCode);
  console.log('Content-Type:', res.headers['content-type']);

  let data = '';
  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log('✓ HTML loaded, size:', data.length, 'bytes');

    // Check for key elements
    const checks = [
      { name: 'Token Selector', pattern: /<div class="token-selector"/ },
      { name: 'KPI Bar', pattern: /<div.*class="kpi-bar"/ },
      { name: 'Dashboard Grid', pattern: /<div.*class="dashboard-grid"/ },
      { name: 'Overview Card', pattern: /id="card-overview"/ },
      { name: 'Trend Card', pattern: /id="card-trend"/ },
      { name: 'Heatmap Card', pattern: /id="card-heatmap"/ },
      { name: 'Daily Bar Card', pattern: /id="card-daily-bar"/ },
      { name: 'TGE Card', pattern: /id="card-tge"/ },
      { name: 'Sankey Card', pattern: /id="card-sankey"/ },
      { name: 'Ranking Card', pattern: /id="card-ranking"/ },
      { name: 'Daily Table Card', pattern: /id="card-daily-table"/ },
      { name: 'initTokenSelector function', pattern: /function initTokenSelector\(\)/ },
      { name: 'renderTokenDashboard function', pattern: /function renderTokenDashboard\(/ },
      { name: 'renderKpiBar function', pattern: /function renderKpiBar\(/ }
    ];

    console.log('\n=== Element Checks ===');
    checks.forEach(check => {
      const found = check.pattern.test(data);
      console.log(found ? '✓' : '✗', check.name);
    });

    // Check for potential issues
    console.log('\n=== Potential Issues ===');
    const issues = [];

    if (data.includes('filter-token') && !data.includes('<select id="filter-token"')) {
      issues.push('⚠ References to filter-token but element removed');
    }
    if (data.includes('tab-btn') && !data.includes('<button class="tab-btn"')) {
      issues.push('⚠ References to tab-btn but elements removed');
    }
    if (data.includes('token-grid') && !data.includes('<div class="token-grid"')) {
      issues.push('⚠ References to token-grid but element removed');
    }

    if (issues.length === 0) {
      console.log('✓ No obvious issues detected');
    } else {
      issues.forEach(issue => console.log(issue));
    }
  });
});

req.on('error', (e) => {
  console.error('✗ Server not running:', e.message);
  console.log('\nPlease start server with:');
  console.log('cd web && python3 -m http.server 8888');
});

req.end();
