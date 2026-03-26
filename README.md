# PUMP Research Workspace

当前仓库已经收口为以 PUMP 研究为主，保留原有链上数据采集数据层，公开页面只保留 PUMP 行为图。

## 功能特性

- 📊 **多链支持**: Ethereum, BSC, Solana
- 🏦 **38 个主要交易所**: Binance, OKX, Bybit, KuCoin, Gate.io 等
- 📈 **可视化**: Sankey 流向图、历史趋势图、交易所排名
- ⚠️ **异常警报**: 自动检测异常流量
- 🔄 **自动更新**: 每小时通过 GitHub Actions 自动刷新

## 在线访问

🌐 **[查看页面](https://melroseee-e.github.io/data-monitoring/)**

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
# 可选：备用 key，主 key 没额度/被限流时自动切换
HELIUS_API_KEY_2=your_backup_helius_api_key
# 或者直接用逗号分隔的列表
# HELIUS_API_KEYS=key1,key2
```

### 3. 运行数据采集

```bash
# 归并交易所标签
python scripts/normalize_labels.py

# 采集链上数据
python scripts/data_collector.py
```

### 4. 查看页面

```bash
open web/pump_behavior_chart.html
```

## 项目结构

```
├── scripts/
│   ├── data_collector.py        # 主采集器
│   ├── normalize_labels.py      # 交易所标签归并
│   ├── pump/                    # PUMP 研究脚本
│   ├── ops/                     # 运维脚本
│   └── archive/                 # 调试/实验脚本归档
├── data/
│   ├── latest_data.json         # 主线最新数据
│   ├── history/                 # 主线历史数据
│   └── pump/                    # PUMP 数据分层
├── web/                         # 公开页面
│   └── pump_behavior_chart.html
├── docs/
│   ├── pump/                    # PUMP 研究报告
│   └── archive/                 # 历史项目文档
├── screenshots/
│   ├── pump/                    # PUMP 页面校验截图
│   └── archive/                 # 历史截图归档
├── archive/                     # 日志、旧页面、内部笔记归档
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
