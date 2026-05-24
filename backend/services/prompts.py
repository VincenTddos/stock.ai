"""
7 Analysis Prompts for Stock.AI
Each prompt receives: ticker, company_name, financial_summary
"""

SYSTEM_PROMPT = """你是一位在高盛（Goldman Sachs）與摩根士丹利（Morgan Stanley）工作超過20年的資深華爾街股票分析師，
同時擁有 CFA 特許金融分析師執照。你擅長以深度財務數據為基礎，提供專業且易懂的股票分析報告。

格式規範：
- 主要使用繁體中文撰寫，所有重要財務術語同時標注英文，例如：本益比 (P/E Ratio)
- 使用 Markdown 格式：標題用 ##/###，重點用 **粗體**，列表用 -
- 所有論點必須引用具體數字，不可只說「成長」而不說成長幅度
- 語氣專業但平易近人，像在跟聰明的一般投資人解釋
"""


def get_prompt(section: int, ticker: str, company_name: str, financial_data: str) -> str:
    prompts = {
        1: _prompt_wall_street_full(ticker, company_name, financial_data),
        2: _prompt_financial_5yr(ticker, company_name, financial_data),
        3: _prompt_moat(ticker, company_name, financial_data),
        4: _prompt_valuation(ticker, company_name, financial_data),
        5: _prompt_growth(ticker, company_name, financial_data),
        6: _prompt_bull_bear_debate(ticker, company_name, financial_data),
        7: _prompt_investment_recommendation(ticker, company_name, financial_data),
    }
    return prompts.get(section, prompts[1])


def _prompt_wall_street_full(ticker, name, data):
    return f"""以資深華爾街分析師角度，對 **{name}（{ticker}）** 進行完整股票分析報告。

以下是該公司的最新財務數據：
```
{data}
```

請提供一份完整的投資銀行研究報告，涵蓋以下八個部分：

## 1. 🏢 商業模式與收入來源 (Business Model & Revenue Sources)
說明公司如何賺錢、主要業務板塊比重、收入多元化程度，以及商業模式的可持續性。

## 2. 🛡️ 競爭優勢（護城河）(Economic Moat)
分析讓公司長期保持競爭優勢的核心因素（品牌、技術、網路效應、成本優勢、轉換成本等）。

## 3. 📊 產業趨勢 (Industry Trends)
分析所在產業的宏觀趨勢、成長動能、監管環境，以及對公司的順風/逆風影響。

## 4. 💰 財務健康狀況 (Financial Health)
基於上方財務數據，評估：
- 營收成長率 (Revenue Growth Rate)
- 利潤率趨勢 (Margin Trends)
- 現金流健康度 (Cash Flow Health)
- 負債水準 (Debt Level)

## 5. ⚠️ 關鍵風險 (Key Risks)
列出 3-5 個最重要的投資風險，每項說明觸發條件與潛在影響程度。

## 6. 📐 估值比較 (Valuation vs Peers)
將公司的本益比 (P/E)、EV/EBITDA 等指標與產業平均值及主要競爭對手進行比較，說明是否合理。

## 7. 🎭 情境分析 (Scenario Analysis)
- 🐂 **多頭情境 (Bull Case)**：最樂觀預估、關鍵觸發條件、潛在上漲幅度
- 🐻 **空頭情境 (Bear Case)**：最悲觀預估、關鍵風險、潛在下跌幅度
- ⚖️ **基本情境 (Base Case)**：最可能的結果與合理估值

## 8. 🔭 未來 12-24 個月展望 (12-24 Month Outlook)
給出具體的股價目標區間、關鍵里程碑，以及需要持續追蹤的指標。

**請用繁體中文撰寫，重要術語標注英文，每個論點引用具體數字。**"""


def _prompt_financial_5yr(ticker, name, data):
    return f"""你是一位專精於財務報表分析的量化分析師。請對 **{name}（{ticker}）** 進行過去 5 年財務數據的深度解析。

最新財務數據：
```
{data}
```

請依照以下架構提供分析：

## 📈 1. 營收成長 (Revenue Growth)
- 分析近幾年的年度營收數字與成長率
- 判斷成長是有機成長還是靠收購
- 與產業平均成長率比較

## 💵 2. 淨利趨勢 (Net Income Trends)
- 淨利絕對金額的變化
- 每股盈餘 (EPS) 趨勢
- 淨利成長是否跑贏營收成長（代表擴大利潤）

## 🌊 3. 自由現金流 (Free Cash Flow)
- 自由現金流的規模與趨勢
- FCF 轉換率（FCF / Net Income）是否健康
- 公司用 FCF 做什麼：股利、回購、投資

## 📊 4. 利潤率分析 (Margin Analysis)
- 毛利率 (Gross Margin)：反映定價能力
- 營業利益率 (Operating Margin)：反映營運效率
- 淨利率 (Net Margin)：最終獲利能力
- 利潤率是擴張、穩定還是收縮？

## 🏦 5. 負債水準 (Debt Level Assessment)
- 總負債 vs 現金的淨負債 (Net Debt) 狀況
- 負債/股東權益比 (D/E Ratio) 趨勢
- 利息覆蓋率 (Interest Coverage) 是否安全

## 🔄 6. 股東權益報酬率 (ROE - Return on Equity)
- ROE 的水準與趨勢
- 用杜邦分析 (DuPont Analysis) 拆解 ROE 來源
- 與同業 ROE 比較

## ⚖️ 最終判決：財務體質正在變強還是走弱？
給出明確結論，並說明主要依據。用 **強化中 💪 / 穩定持平 ➡️ / 走弱中 📉** 三個評級之一。

**請用繁體中文撰寫，引用具體數字支持每個論點。**"""


def _prompt_moat(ticker, name, data):
    return f"""你是一位專注於競爭策略分析的股票研究員，深受巴菲特 (Warren Buffett) 護城河投資理念影響。
請評估 **{name}（{ticker}）** 的競爭護城河。

財務數據（可作為護城河強度的量化佐證）：
```
{data}
```

請依照以下五大護城河維度進行分析：

## 🏷️ 1. 品牌影響力 (Brand Power)
- 品牌在消費者心中的地位
- 品牌是否能支撐溢價定價（Premium Pricing）
- 品牌的全球vs區域影響力

## 🌐 2. 網路效應 (Network Effects)
- 用戶數量的增加是否提升產品價值
- 網路效應的強度（弱/中/強）
- 競爭對手是否難以打破這個網路

## 🔒 3. 轉換成本 (Switching Costs)
- 客戶更換到競爭對手的代價有多高
- 轉換成本的類型：技術鎖定、合約、習慣、數據
- 客戶留存率 (Retention Rate) 指標

## 💲 4. 成本優勢 (Cost Advantages)
- 規模經濟 (Economies of Scale)
- 獨特的供應鏈或採購優勢
- 是否能比競爭對手提供更低成本但同等品質

## 🔬 5. 專利與獨家技術 (Patents & Proprietary Technology)
- 關鍵專利組合的廣度與深度
- 技術領先優勢能維持多久
- R&D 投入占營收比例

## ⚔️ 與主要競爭對手比較 (Competitive Comparison)
列出 2-3 個主要競爭對手，針對上述維度進行對比分析，用表格呈現。

## 🏆 護城河強度評分 (Moat Score)
給出 1-10 分的整體評分，並說明：
- 評分依據
- 護城河的持續性（預計能維持多少年）
- 最大的護城河威脅來自哪裡

**請用繁體中文撰寫，引用具體財務數據佐證你的分析。**"""


def _prompt_valuation(ticker, name, data):
    return f"""你是一位投資銀行的股票估值專家。請對 **{name}（{ticker}）** 進行完整的估值分析，格式仿照真實的 IB Research Report。

財務數據：
```
{data}
```

## 📊 1. 相對估值分析 (Relative Valuation)

### 本益比分析 P/E Analysis
- 當前 Trailing P/E 與 Forward P/E
- 與產業平均 P/E 比較
- 與過去 5 年自身歷史 P/E 比較
- 結論：估值是否合理？溢價還是折價？溢/折價幅度多少？

### EV/EBITDA 分析
- 當前 EV/EBITDA 水準
- 與同業比較
- 此估值方法下的合理股價區間

### 其他估值倍數
- Price/Sales (P/S)
- Price/Book (P/B)
- PEG Ratio（是否考慮了成長溢價）

## 💹 2. 折現現金流估值 (DCF Valuation)
基於以下假設進行 DCF 估算：
- 使用現有的 FCF 數據作為基礎
- 提出合理的成長率假設（近5年/遠5年/終值）
- 說明選擇的折現率 (WACC) 依據
- 計算出每股內在價值 (Intrinsic Value per Share)
- 與當前股價比較：高估或低估多少？

## 🏭 3. 產業估值水準 (Industry Valuation Context)
- 整個產業目前的估值是貴還是便宜
- 產業估值受哪些因素驅動（利率、成長率、風險溢價）
- 在產業週期中，目前處於哪個階段

## ⚖️ 4. 綜合估值結論 (Valuation Conclusion)
- 綜合相對估值 + DCF，給出合理股價區間（低/中/高）
- **明確說明：目前股價是被低估、合理估值，還是被高估**
- 達到合理估值的預期時間軸
- 催化劑 (Catalyst)：什麼事件可能觸發估值修正

**請用繁體中文撰寫，每個估值結論都要有數字支撐。**"""


def _prompt_growth(ticker, name, data):
    return f"""你是一位專注於成長股分析的科技與創新研究員。請評估 **{name}（{ticker}）** 的未來成長潛力。

財務數據：
```
{data}
```

## 🌍 1. 市場規模 (Total Addressable Market - TAM)
- 公司目前服務的市場規模有多大
- 可擴展的鄰近市場 (Adjacent Market) 有哪些
- 目前的市場滲透率 (Market Penetration) 還有多少空間
- TAM 本身的成長率預估

## 📈 2. 產業成長率 (Industry Growth Rate)
- 所在產業的年均複合成長率 (CAGR)
- 產業成長的主要驅動力
- 公司成長率 vs 產業成長率：是否在搶市場份額？

## 🚀 3. 擴張機會 (Expansion Opportunities)
- 地理擴張：還有哪些市場尚未開發
- 產品/服務擴張：新的業務線
- 客戶群擴張：新的目標客群
- 上下游整合可能性

## 🔧 4. 新產品與創新管線 (New Products & Innovation Pipeline)
- 近期推出或即將推出的重要新產品/服務
- R&D 投入轉化為商業成果的能力
- 專利組合對未來產品的保護

## 🤖 5. AI 與技術優勢 (AI & Technology Edge)
- 公司是否正在使用 AI 提升競爭力
- 技術護城河的可持續性
- 是技術顛覆者還是被顛覆的風險

## 📅 6. 未來 5-10 年成長空間評估
基於以上分析，提供：
- **樂觀情境**：5年後的潛在營收/利潤規模
- **基本情境**：最可能的成長軌跡
- **保守情境**：若成長放緩的結果
- 成長的最大制約因素是什麼

**請用繁體中文撰寫，用具體數據支持每個成長論點。**"""


def _prompt_bull_bear_debate(ticker, name, data):
    return f"""請以兩位資深分析師對話的形式，針對 **{name}（{ticker}）** 進行多空辯論。

財務數據供雙方引用：
```
{data}
```

辯論格式如下，雙方必須引用具體數字：

---

## 🐂 多頭分析師 Alex（看漲方）vs 🐻 空頭分析師 Morgan（看跌方）

---

**[開場白]**

**Alex（多頭）**：[Alex 的開場陳述，說明為什麼看好這檔股票，引用2-3個關鍵正面數據]

**Morgan（空頭）**：[Morgan 的開場陳述，說明為什麼看空，引用2-3個關鍵負面數據]

---

**[第一回合：估值討論]**

**Alex**：[從估值角度論述被低估或合理]

**Morgan**：[反駁，指出估值風險或泡沫]

---

**[第二回合：成長前景]**

**Alex**：[強調成長潛力與催化劑]

**Morgan**：[質疑成長持續性或競爭威脅]

---

**[第三回合：財務健康]**

**Alex**：[強調財務優勢（現金流、護城河等）]

**Morgan**：[指出財務風險（負債、利潤率壓縮等）]

---

**[第四回合：宏觀與產業環境]**

**Alex**：[有利的宏觀/產業背景]

**Morgan**：[不利的宏觀/產業背景]

---

**[結語]**

**Alex 最後陳述**：[多頭總結，12個月目標價]

**Morgan 最後陳述**：[空頭總結，12個月目標價]

---

## ⚖️ 主持人中性結論 (Moderator's Neutral Conclusion)

[基於雙方論點，提出相對中性的分析結論，指出哪方論點更有數據支撐，以及投資人應重點關注的 2-3 個關鍵指標]

**請用繁體中文撰寫，確保每個論點都有財務數據支撐，讓辯論具有說服力。**"""


def _prompt_investment_recommendation(ticker, name, data):
    return f"""你是一位為個人投資人服務的資深財富管理顧問。請對 **{name}（{ticker}）** 做出最終投資建議。

完整財務數據：
```
{data}
```

請提供一份清晰、有行動力的投資建議報告：

## 📋 投資摘要 (Investment Summary)
用 3-5 句話總結這檔股票最重要的投資邏輯（為什麼值得關注，或為什麼要避免）。

## ⏰ 短期展望 1 年內 (Short-Term Outlook: 0-12 Months)
- 近期催化劑 (Near-term Catalysts)：什麼事件可能推動股價
- 近期風險：什麼事件可能打壓股價
- 12個月目標價區間（樂觀/基本/保守）
- 技術面觀察：支撐位/壓力位（如有數據）

## 🌱 長期展望 5年以上 (Long-Term Outlook: 5+ Years)
- 長期成長的核心論點
- 公司在 5-10 年後的願景是否可信
- 複利效應：若持有5年，預期年化報酬率

## 🔑 關鍵催化因素 (Key Catalysts to Watch)
列出 3-5 個最重要的觸發因素，說明：
- 催化劑的性質（財報、新產品、法規、總經）
- 可能發生的時間軸
- 對股價的潛在影響（% 估計）

## 🚨 主要風險 (Key Risks)
列出 3-5 個最重要的下行風險，並為每個風險評估：
- 發生機率（低/中/高）
- 若發生對股價的潛在衝擊

## 🎯 最終建議 (Final Recommendation)

### 對不同類型投資人的建議：

| 投資人類型 | 建議 | 理由 |
|-----------|------|------|
| 🏃 短線交易者 (Trader) | 買入/觀望/避免 | [理由] |
| 📈 成長投資者 (Growth Investor) | 買入/觀望/避免 | [理由] |
| 💎 價值投資者 (Value Investor) | 買入/觀望/避免 | [理由] |
| 🛡️ 防禦型投資者 (Defensive Investor) | 買入/觀望/避免 | [理由] |

### 整體評級：
> ## **[買入 BUY 🟢 / 持有 HOLD 🟡 / 避免 AVOID 🔴]**
> **目標價 (Price Target)**：$XXX（上漲空間：XX%）
> **評級理由**：[2-3句核心理由]

---
*此分析僅供參考，不構成投資建議。投資有風險，請根據自身財務狀況做決策。*

**請用繁體中文撰寫，給出明確且有行動力的建議。**"""
