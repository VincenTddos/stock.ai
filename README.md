# 📈 Stock.AI — 華爾街級股市分析系統

以 AI 驅動的 7 維度股票分析平台，結合 Yahoo Finance 真實財務數據與 Claude AI 分析能力。

## 功能一覽

| # | 分析模組 | 說明 |
|---|---------|------|
| ① | 華爾街完整分析 | 商業模式、護城河、產業趨勢、財務健康、風險、情境分析 |
| ② | 5年財務數據解析 | 營收、淨利、自由現金流、利潤率、負債、ROE 趨勢 |
| ③ | 競爭護城河評估 | 品牌、網路效應、轉換成本、成本優勢、專利（1-10分） |
| ④ | 估值分析報告 | P/E比較、DCF估值、產業平均、高估/低估結論 |
| ⑤ | 未來成長潛力 | 市場規模、產業成長率、擴張機會、AI優勢、5-10年展望 |
| ⑥ | 多空辯論 | 兩位分析師對話式辯論，數據支撐，中性結論 |
| ⑦ | 投資建議 | 短期/長期展望、催化劑、風險、買入/持有/避免 |

## 快速啟動

### 前置需求
- Python 3.10+
- Node.js 18+
- Anthropic API Key（[取得](https://console.anthropic.com/)）

### 1. 設定 API Key
```bash
# 複製環境變數範本
copy .env.example .env

# 編輯 .env，填入你的 ANTHROPIC_API_KEY
```

### 2. 一鍵啟動（Windows）
```bash
# 直接雙擊 start.bat
# 或在命令列執行：
start.bat
```

### 3. 手動啟動（開發模式）

**後端：**
```bash
cd backend
pip install -r requirements.txt
python main.py
# → http://localhost:8000
```

**前端：**
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## 技術架構

```
stock.ai/
├── backend/              # Python FastAPI 後端
│   ├── main.py          # API 路由 + SSE 串流
│   └── services/
│       ├── financial_data.py   # yfinance 財務數據
│       ├── prompts.py          # 7 個 AI 分析 Prompt
│       └── claude_analysis.py  # Anthropic API 串流
├── frontend/             # React + Vite + Tailwind 前端
│   └── src/
│       ├── App.tsx
│       ├── components/
│       └── services/
├── .env.example
├── start.bat
└── README.md
```

## API 文件

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/health` | 健康檢查 |
| GET | `/api/stock/{ticker}` | 取得股票基本資訊 |
| GET | `/api/analyze/{ticker}/{section}` | 串流 AI 分析（SSE） |

## 使用範例

```bash
# 搜尋 Apple 股票資訊
curl http://localhost:8000/api/stock/AAPL

# 串流分析（section 1-7）
curl http://localhost:8000/api/analyze/AAPL/1
```
