# On-Chain Exchange Flow Monitor

实时监控代币在中心化交易所的流入流出数据。

## 功能特性

- 📊 **多链支持**: Ethereum, BSC, Solana
- 🏦 **38 个主要交易所**: Binance, OKX, Bybit, KuCoin, Gate.io 等
- 📈 **可视化**: Sankey 流向图、历史趋势图、交易所排名
- ⚠️ **异常警报**: 自动检测异常流量
- 🔄 **自动更新**: 每小时通过 GitHub Actions 自动刷新

## 在线访问

🌐 **[查看实时数据](https://YOUR_USERNAME.github.io/data-monitoring/)**

## 本地运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Keys

复制 `.env.example` 为 `.env` 并填入你的 API keys:

```bash
cp .env.example .env
```

编辑 `.env`:
```
ETHERSCAN_API_KEY=your_etherscan_api_key
BSCTrace_API_KEY=your_nodereal_api_key
HELIUS_API_KEY=your_helius_api_key
```

### 3. 运行数据采集

```bash
# 归并交易所标签
python scripts/normalize_labels.py

# 采集链上数据
python scripts/data_collector.py
```

### 4. 查看前端

```bash
open web/index.html
```

## 项目结构

```
├── scripts/
│   ├── normalize_labels.py      # 交易所标签归并
│   └── data_collector.py        # 数据采集器
├── data/
│   ├── tokens.json              # 监控的代币列表
│   ├── exchange_addresses.json  # 交易所地址
│   ├── latest_data.json         # 最新数据
│   └── history/                 # 历史数据
├── web/
│   └── index.html               # 前端界面
└── .github/workflows/
    └── update-data.yml          # 自动化工作流
```

## API 使用情况

| API | 免费额度 | 月使用量 | 占用率 |
|-----|---------|---------|--------|
| Etherscan | 100k calls/day | ~2,880 | 0.096% |
| BSCTrace | 10M CU/month | ~118k | 1.19% |
| Helius | 1M credits/month | ~144k | 14.4% |

## 技术栈

- **后端**: Python 3.9+
- **前端**: HTML + Chart.js + Plotly.js
- **部署**: GitHub Pages + GitHub Actions
- **API**: Etherscan V2, NodeReal BSCTrace, Helius RPC

## License

MIT
