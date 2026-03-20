import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# Add console.logs for debugging
content = re.sub(
    r"const t = entry\.tokens\[selectedToken\];",
    "const t = entry.tokens[selectedToken]; if(t.exchanges) { console.log('Found exchanges for', selectedToken, Object.keys(t.exchanges).length); }",
    content
)

content = re.sub(
    r"updateExchangeTable\(fullHistory\);",
    "console.log('Updating table with fullHistory, keys:', Object.keys(fullHistory.exchanges).length); updateExchangeTable(fullHistory);",
    content
)

content = re.sub(
    r"tbody\.innerHTML = sortedEx\.map",
    "console.log('Rendering table rows:', sortedEx.length); tbody.innerHTML = sortedEx.map",
    content
)

with open("web/terminal.html", "w") as f:
    f.write(content)
