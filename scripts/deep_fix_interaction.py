import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. FIX THE "DOUBLE CLICK" ISSUE: 
# The issue was renderTokenList(filter) RE-WRITING innerHTML inside the click listener.
# This destroyed the DOM element immediately, so subsequent logic might fail or browser gets confused.
# Let's use event delegation or just update classes.

new_token_list_func = """function renderTokenList(filter = '') {
  if(!rawData) return;
  const list = document.getElementById('tokenList');
  let tokens = Object.keys(rawData.tokens).sort();
  if(filter) {
    tokens = tokens.filter(t => t.toLowerCase().includes(filter));
  }
  
  if(!selectedToken && tokens.length > 0) {
    selectedToken = tokens[0];
  }
  
  list.innerHTML = tokens.map(t => {
    const d = rawData.tokens[t];
    const net = d.net_flow || 0;
    const isPos = net >= 0;
    const chain = d.deployments[0]?.chain || '';
    
    return `<div class="token-item ${t === selectedToken ? 'active' : ''}" data-token="${t}">
      <div class="token-info">
        <span class="token-symbol">${t}</span>
        <span class="token-chain">${chain}</span>
      </div>
      <div class="token-net ${isPos ? 'pos' : 'neg'}">
        ${isPos ? '+' : ''}${formatNum(net)}
      </div>
    </div>`;
  }).join('');
  
  // Use a single delegated listener on the list instead of individual listeners that get destroyed
  list.onclick = (e) => {
    const item = e.target.closest('.token-item');
    if (!item) return;
    
    const targetToken = item.dataset.token;
    if (selectedToken === targetToken) return;
    
    selectedToken = targetToken;
    
    // Update active class manually
    list.querySelectorAll('.token-item').forEach(el => el.classList.remove('active'));
    item.classList.add('active');
    
    updateDashboard();
  };
  
  updateDashboard();
}"""

content = re.sub(r"function renderTokenList\(filter = ''\) \{.*?updateDashboard\(\);\n\}", new_token_list_func, content, flags=re.DOTALL)

# 2. FIX PLOTLY MEMORY/STATE ISSUE: Use Plotly.purge
# Replace .innerHTML = '' with Plotly.purge to properly clean up
content = re.sub(
    r"document\.getElementById\('trendChart'\)\.innerHTML = '';",
    "Plotly.purge('trendChart');",
    content
)
content = re.sub(
    r"document\.getElementById\('sankeyChart'\)\.innerHTML = '';",
    "Plotly.purge('sankeyChart');",
    content
)

# 3. ENSURE SANKEY SHOWS FULL STATE INSTANTLY: 
# Disable static/animation effects
content = re.sub(
    r"Plotly\.newPlot\('sankeyChart', plotData, layout, \{displayModeBar: false, responsive: true\}\); setTimeout",
    "Plotly.newPlot('sankeyChart', plotData, layout, {displayModeBar: false, responsive: true, staticPlot: false}); setTimeout",
    content
)

with open("web/terminal.html", "w") as f:
    f.write(content)
