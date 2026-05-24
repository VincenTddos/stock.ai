import { useState, useCallback } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, BarChart, Bar,
} from 'recharts'
import { FlaskConical, AlertTriangle, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import { dsApi } from '../services/ds-api'
import type {
  DSTab, CorrelationResult, SignalResult,
  SentimentResult, FactorResult, StationarityResult,
} from '../types/ds'
import CorrelationHeatmap from '../components/ds/CorrelationHeatmap'
import BacktestChart from '../components/ds/BacktestChart'
import ConfusionMatrix from '../components/ds/ConfusionMatrix'
import SignalBadge from '../components/ds/SignalBadge'
import MetricCard from '../components/ds/MetricCard'

// ── Sanitize ticker input (XSS prevention) ─────────────────
function sanitizeTicker(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z0-9.^]/g, '').slice(0, 10)
}

const DS_TABS: { id: DSTab; label: string }[] = [
  { id: 'correlation', label: '① 相關性' },
  { id: 'signals',     label: '② ML 信號' },
  { id: 'sentiment',   label: '③ 情緒分析' },
  { id: 'factors',     label: '④ 因子模型' },
  { id: 'stationarity', label: '⑤ 定態性' },
]

// ── Tag-input component ─────────────────────────────────────
function TagInput({
  label, tags, onChange, placeholder,
}: {
  label: string
  tags: string[]
  onChange: (t: string[]) => void
  placeholder: string
}) {
  const [input, setInput] = useState('')

  function add() {
    const t = sanitizeTicker(input)
    if (t && !tags.includes(t)) onChange([...tags, t])
    setInput('')
  }

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-finance-muted">{label}</label>
      <div className="flex flex-wrap gap-2 rounded-lg border border-finance-border bg-finance-card p-2">
        {tags.map(t => (
          <span key={t} className="flex items-center gap-1 rounded-md bg-finance-border px-2 py-1 text-xs font-mono text-finance-text">
            {t}
            <button
              type="button"
              onClick={() => onChange(tags.filter(x => x !== t))}
              className="ml-1 text-finance-muted hover:text-finance-red min-w-[20px] min-h-[20px]"
              aria-label={`移除 ${t}`}
            >×</button>
          </span>
        ))}
        <input
          value={input}
          onChange={e => setInput(e.target.value.toUpperCase().replace(/[^A-Z0-9.^]/g, ''))}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
          onBlur={add}
          placeholder={placeholder}
          maxLength={10}
          className="flex-1 min-w-[120px] bg-transparent text-xs text-finance-text outline-none placeholder:text-finance-muted"
          aria-label={`新增${label}`}
        />
      </div>
    </div>
  )
}

// ── Loading overlay ─────────────────────────────────────────
function LoadingOverlay({ message }: { message: string }) {
  return (
    <div className="flex min-h-[20rem] flex-col items-center justify-center gap-4 text-finance-muted" role="status" aria-live="polite">
      <Loader2 className="h-10 w-10 animate-spin text-finance-green" aria-hidden />
      <p className="text-sm">{message}</p>
    </div>
  )
}

// ── Error banner ────────────────────────────────────────────
function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-finance-red/30 bg-finance-red/10 p-4 text-finance-red" role="alert">
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <p className="text-sm">{message}</p>
    </div>
  )
}

// ── Collapsible section ─────────────────────────────────────
function Collapsible({ title, children, defaultOpen = true }: {
  title: string; children: React.ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-lg border border-finance-border bg-finance-card">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center justify-between px-5 py-4 text-left font-semibold text-finance-text hover:text-finance-green transition-colors min-h-[48px]"
        aria-expanded={open}
      >
        {title}
        {open ? <ChevronUp className="h-4 w-4" aria-hidden /> : <ChevronDown className="h-4 w-4" aria-hidden />}
      </button>
      {open && <div className="px-5 pb-5">{children}</div>}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════
// Main DataScience Page
// ═══════════════════════════════════════════════════════════

export default function DataScience() {
  const [activeTab, setActiveTab] = useState<DSTab>('correlation')

  // Config state
  const [twTickers, setTwTickers]   = useState(['2330.TW', '0050.TW', '^TWII'])
  const [usTickers, setUsTickers]   = useState(['SPY', 'QQQ', '^VIX'])
  const [period, setPeriod]         = useState('3y')
  const [signalTarget, setSignalTarget] = useState('2330.TW')
  const [sentimentTicker, setSentimentTicker] = useState('2330.TW')

  // Result states
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState<string | null>(null)
  const [corrResult, setCorrResult]   = useState<CorrelationResult | null>(null)
  const [signalResult, setSignalResult] = useState<SignalResult | null>(null)
  const [sentimentResult, setSentimentResult] = useState<SentimentResult | null>(null)
  const [factorResult, setFactorResult]  = useState<FactorResult | null>(null)
  const [stationResult, setStationResult] = useState<StationarityResult | null>(null)

  const run = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      if (activeTab === 'correlation') {
        const r = await dsApi.correlation({ tw_tickers: twTickers, us_tickers: usTickers, period, rolling_window: 30 })
        setCorrResult(r)
      } else if (activeTab === 'signals') {
        const features = [...twTickers.filter(t => t !== signalTarget), ...usTickers]
        const r = await dsApi.signals({ target: signalTarget, features, period: '4y', train_ratio: 0.75 })
        setSignalResult(r)
      } else if (activeTab === 'sentiment') {
        const r = await dsApi.sentiment({ ticker: sentimentTicker, company_name: '' })
        setSentimentResult(r)
      } else if (activeTab === 'factors') {
        const r = await dsApi.factors({ tw_tickers: twTickers, market_ticker: 'SPY', period })
        setFactorResult(r)
      } else if (activeTab === 'stationarity') {
        const r = await dsApi.stationarity({ tickers: [...twTickers, ...usTickers], period })
        setStationResult(r)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '分析失敗，請稍後再試')
    } finally {
      setLoading(false)
    }
  }, [activeTab, twTickers, usTickers, period, signalTarget, sentimentTicker])

  return (
    <main className="min-h-screen bg-finance-bg px-4 py-6 text-finance-text md:px-8">
      <div className="mx-auto max-w-7xl space-y-6">

        {/* ── Header ── */}
        <header className="flex items-center gap-3 border-b border-finance-border pb-5">
          <FlaskConical className="h-7 w-7 text-finance-green" aria-hidden />
          <div>
            <h1 className="text-2xl font-bold text-finance-text md:text-3xl">數據科學分析</h1>
            <p className="mt-1 text-sm text-finance-muted">台美股關聯分析、ML 投資信號、情緒分析、因子模型</p>
          </div>
        </header>

        {/* ── Config Panel ── */}
        <Collapsible title="⚙️ 設定">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <TagInput label="台股（加 .TW 後綴或 ^TWII）" tags={twTickers} onChange={setTwTickers} placeholder="如 2330.TW" />
            <TagInput label="美股（代號或 ^VIX）" tags={usTickers} onChange={setUsTickers} placeholder="如 NVDA" />
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-finance-muted" htmlFor="period">分析期間</label>
                <div className="flex gap-2" role="group" aria-label="分析期間">
                  {['1y', '2y', '3y', '4y'].map(p => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setPeriod(p)}
                      className={`min-h-[44px] flex-1 rounded-lg text-sm font-semibold transition ${period === p ? 'bg-finance-green text-[#07140a]' : 'border border-finance-border text-finance-muted hover:border-finance-green hover:text-finance-green'}`}
                      aria-pressed={period === p}
                    >{p}</button>
                  ))}
                </div>
              </div>
              {activeTab === 'signals' && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-finance-muted" htmlFor="signal-target">預測目標股票</label>
                  <input
                    id="signal-target"
                    value={signalTarget}
                    onChange={e => setSignalTarget(sanitizeTicker(e.target.value))}
                    maxLength={10}
                    className="h-11 w-full rounded-lg border border-finance-border bg-finance-card px-3 font-mono text-sm text-finance-text outline-none focus:border-finance-green"
                    placeholder="如 2330.TW"
                  />
                </div>
              )}
              {activeTab === 'sentiment' && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-finance-muted" htmlFor="sentiment-ticker">情緒分析股票</label>
                  <input
                    id="sentiment-ticker"
                    value={sentimentTicker}
                    onChange={e => setSentimentTicker(sanitizeTicker(e.target.value))}
                    maxLength={10}
                    className="h-11 w-full rounded-lg border border-finance-border bg-finance-card px-3 font-mono text-sm text-finance-text outline-none focus:border-finance-green"
                    placeholder="如 AAPL"
                  />
                </div>
              )}
            </div>
          </div>
        </Collapsible>

        {/* ── Module Tabs ── */}
        <nav aria-label="分析模組" className="flex gap-2 overflow-x-auto rounded-xl border border-finance-border bg-finance-card p-2">
          {DS_TABS.map(tab => (
            <button
              key={tab.id}
              type="button"
              onClick={() => { setActiveTab(tab.id); setError(null) }}
              aria-pressed={activeTab === tab.id}
              className={`min-h-[44px] shrink-0 rounded-lg px-4 text-sm font-semibold transition ${
                activeTab === tab.id
                  ? 'bg-finance-green text-[#07140a]'
                  : 'text-finance-muted hover:bg-finance-bg hover:text-finance-text'
              }`}
            >{tab.label}</button>
          ))}
        </nav>

        {/* ── Run Button ── */}
        <button
          type="button"
          onClick={run}
          disabled={loading}
          className="flex min-h-[52px] w-full items-center justify-center gap-3 rounded-xl bg-finance-green font-bold text-[#07140a] transition hover:bg-[#51d368] disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto sm:px-10"
          aria-busy={loading}
        >
          {loading ? (
            <><Loader2 className="h-5 w-5 animate-spin" aria-hidden /> 分析中，請稍候…</>
          ) : '🚀 開始分析'}
        </button>

        {/* ── Error ── */}
        {error && <ErrorBanner message={error} />}

        {/* ── Results ── */}
        <section aria-live="polite" aria-label="分析結果">
          {loading && (
            <LoadingOverlay message={
              activeTab === 'signals' ? '正在訓練 ML 模型、Walk-Forward 驗證中…（約 30-60 秒）' :
              activeTab === 'sentiment' ? '正在抓取新聞並用 AI 評分…' :
              '正在分析資料…'
            } />
          )}

          {!loading && activeTab === 'correlation' && corrResult && (
            <CorrelationResults result={corrResult} />
          )}
          {!loading && activeTab === 'signals' && signalResult && (
            <SignalResults result={signalResult} />
          )}
          {!loading && activeTab === 'sentiment' && sentimentResult && (
            <SentimentResults result={sentimentResult} />
          )}
          {!loading && activeTab === 'factors' && factorResult && (
            <FactorResults result={factorResult} />
          )}
          {!loading && activeTab === 'stationarity' && stationResult && (
            <StationarityResults result={stationResult} />
          )}
        </section>
      </div>
    </main>
  )
}

// ═══════════════════════════════════════════════════════════
// Sub-result Components
// ═══════════════════════════════════════════════════════════

function CorrelationResults({ result }: { result: CorrelationResult }) {
  const pairs = result.rolling_correlations
  const lagData = result.lag_analysis

  return (
    <div className="space-y-4">
      <Collapsible title="📊 相關係數矩陣（靜態 Pearson Correlation）">
        <CorrelationHeatmap matrix={result.correlation_matrix} />
      </Collapsible>

      {pairs.length > 0 && (
        <Collapsible title="📈 滾動相關係數（30 天滾動視窗）">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={pairs[0].data.filter((_, i) => i % 3 === 0)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                <XAxis dataKey="date" tick={{ fill: '#8b949e', fontSize: 9 }} tickLine={false} interval="preserveStartEnd" />
                <YAxis domain={[-1, 1]} tick={{ fill: '#8b949e', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }}
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  formatter={(v: any) => [(v as number).toFixed(3), '相關係數']}
                />
                <Line type="monotone" dataKey="correlation" stroke="#3fb950" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-finance-muted">{pairs[0].pair}</p>
        </Collapsible>
      )}

      {lagData.length > 0 && (
        <Collapsible title="⏱️ 落後期分析（Cross-Correlation Function）">
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={lagData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                <XAxis dataKey="lag" tick={{ fill: '#8b949e', fontSize: 10 }} tickLine={false} label={{ value: '落後天數', position: 'insideBottom', fill: '#8b949e', fontSize: 10 }} />
                <YAxis domain={[-1, 1]} tick={{ fill: '#8b949e', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }}
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  formatter={(v: any, _: any, props: any) => [(v as number).toFixed(3), props?.payload?.label ?? '']}
                />
                <Bar dataKey="correlation" fill="#388bfd" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-finance-muted">負值 = 美股領先台股；正值 = 台股領先美股</p>
        </Collapsible>
      )}

      {result.granger_causality.length > 0 && (
        <Collapsible title="🔗 Granger 因果檢定">
          <ul className="space-y-2 text-sm">
            {result.granger_causality.map((g, i) => (
              <li key={i} className="rounded-lg bg-finance-bg p-3">
                {g.error ? (
                  <span className="text-finance-red">{g.error}</span>
                ) : (
                  <span className={g.conclusion?.includes('[YES]') ? 'text-finance-green' : 'text-finance-muted'}>
                    {g.conclusion}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Collapsible>
      )}

      {result.stats && (
        <Collapsible title="📋 基本統計摘要（EDA）">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" role="table">
              <thead>
                <tr className="border-b border-finance-border text-xs text-finance-muted">
                  <th className="py-2 text-left">股票</th>
                  <th className="py-2 text-right">年化報酬</th>
                  <th className="py-2 text-right">年化波動</th>
                  <th className="py-2 text-right">Sharpe</th>
                  <th className="py-2 text-right">偏態</th>
                  <th className="py-2 text-right">峰態</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result.stats).map(([ticker, s]) => (
                  <tr key={ticker} className="border-b border-finance-border/50 hover:bg-finance-card/50">
                    <td className="py-2 font-mono text-xs">{ticker}</td>
                    <td className={`py-2 text-right tabular-nums font-semibold ${s.annualized_return >= 0 ? 'text-finance-green' : 'text-finance-red'}`}>
                      {s.annualized_return >= 0 ? '+' : ''}{(s.annualized_return * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 text-right tabular-nums text-finance-muted">{(s.annualized_volatility * 100).toFixed(1)}%</td>
                    <td className={`py-2 text-right tabular-nums ${s.sharpe_approx >= 1 ? 'text-finance-green' : s.sharpe_approx >= 0 ? 'text-finance-amber' : 'text-finance-red'}`}>
                      {s.sharpe_approx.toFixed(2)}
                    </td>
                    <td className="py-2 text-right tabular-nums text-finance-muted">{s.skewness.toFixed(2)}</td>
                    <td className="py-2 text-right tabular-nums text-finance-muted">{s.kurtosis.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Collapsible>
      )}

      {result.market_regimes?.current_regime && (
        <Collapsible title="🎯 當前市場狀態（K-Means 分群）" defaultOpen={false}>
          <div className="rounded-xl border-2 border-finance-green/40 bg-finance-green/10 p-5 text-center">
            <p className="text-xs text-finance-muted">當前市場狀態</p>
            <p className="text-3xl font-black text-finance-green">{result.market_regimes.current_regime.regime_name}</p>
            <p className="mt-1 text-xs text-finance-muted">{result.market_regimes.current_regime.date}</p>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            {Object.entries(result.market_regimes.regime_stats).map(([name, stat]) => (
              <div key={name} className="rounded-lg bg-finance-bg p-3 text-center">
                <p className="text-xs font-semibold text-finance-text">{name}</p>
                <p className="text-sm text-finance-muted">佔時間 {stat.pct_of_time}%</p>
                <p className={`text-sm tabular-nums ${stat.avg_daily_return >= 0 ? 'text-finance-green' : 'text-finance-red'}`}>
                  日均 {stat.avg_daily_return >= 0 ? '+' : ''}{(stat.avg_daily_return * 100).toFixed(3)}%
                </p>
              </div>
            ))}
          </div>
        </Collapsible>
      )}
    </div>
  )
}

function SignalResults({ result }: { result: SignalResult }) {
  const { current_signal, test_performance, backtest, walk_forward, feature_importance, meta } = result

  return (
    <div className="space-y-4">
      <Collapsible title="🎯 當前投資信號">
        <SignalBadge
          signal={current_signal.recommendation}
          confidence={current_signal.confidence}
          probUp={current_signal.probability_up}
        />
        <div className="mt-4 rounded-lg bg-finance-bg p-4">
          <p className="mb-2 text-xs font-semibold text-finance-muted">防資料洩漏措施</p>
          <ul className="space-y-1">
            {meta.anti_leakage_measures.map((m, i) => (
              <li key={i} className="flex gap-2 text-xs text-finance-muted">
                <span className="text-finance-green shrink-0">✓</span>{m}
              </li>
            ))}
          </ul>
        </div>
      </Collapsible>

      <Collapsible title="🔄 Walk-Forward 驗證結果">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-4">
          <MetricCard label="平均 AUC-ROC" value={walk_forward.mean_auc_roc.toFixed(3)} color={walk_forward.mean_auc_roc >= 0.6 ? 'green' : 'amber'} />
          <MetricCard label="平均準確率" value={`${(walk_forward.mean_accuracy * 100).toFixed(1)}%`} />
          <MetricCard label="訓練樣本" value={meta.train_samples.toLocaleString()} />
          <MetricCard label="測試樣本" value={meta.test_samples.toLocaleString()} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-finance-border text-xs text-finance-muted">
                <th className="py-2 text-left">折</th>
                <th className="py-2 text-right">AUC</th>
                <th className="py-2 text-right">準確率</th>
                <th className="py-2 text-right">訓練</th>
                <th className="py-2 text-right">驗證</th>
              </tr>
            </thead>
            <tbody>
              {walk_forward.folds.map(f => (
                <tr key={f.fold} className="border-b border-finance-border/30">
                  <td className="py-1.5">第 {f.fold} 折</td>
                  <td className={`py-1.5 text-right tabular-nums ${f.auc_roc >= 0.6 ? 'text-finance-green' : 'text-finance-amber'}`}>{f.auc_roc}</td>
                  <td className="py-1.5 text-right tabular-nums text-finance-muted">{(f.accuracy * 100).toFixed(1)}%</td>
                  <td className="py-1.5 text-right tabular-nums text-finance-muted">{f.n_train}</td>
                  <td className="py-1.5 text-right tabular-nums text-finance-muted">{f.n_val}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Collapsible>

      <Collapsible title="📊 模型評估與混淆矩陣">
        <ConfusionMatrix perf={test_performance} />
      </Collapsible>

      <Collapsible title="💹 回測績效（策略 vs 買入持有）">
        <BacktestChart backtest={backtest} />
      </Collapsible>

      {feature_importance.length > 0 && (
        <Collapsible title="🔑 特徵重要性（Top 10）" defaultOpen={false}>
          <div className="space-y-2">
            {feature_importance.slice(0, 10).map(f => (
              <div key={f.feature} className="flex items-center gap-3">
                <span className="w-48 shrink-0 truncate font-mono text-xs text-finance-muted">{f.feature}</span>
                <div className="flex-1 h-5 overflow-hidden rounded-full bg-finance-border">
                  <div
                    className="h-full rounded-full bg-finance-green transition-all"
                    style={{ width: `${(f.importance / feature_importance[0].importance) * 100}%` }}
                  />
                </div>
                <span className="w-16 text-right font-mono text-xs text-finance-green">{(f.importance * 100).toFixed(2)}%</span>
              </div>
            ))}
          </div>
        </Collapsible>
      )}
    </div>
  )
}

function SentimentResults({ result }: { result: SentimentResult }) {
  const s = result.sentiment_score
  const score = typeof s.overall_score === 'number' ? s.overall_score : 0

  return (
    <div className="space-y-4">
      <Collapsible title="💬 情緒評分">
        <div className="flex flex-wrap items-start gap-6">
          <div className="text-center">
            <p className="text-xs text-finance-muted">整體情緒分數</p>
            <p className={`text-5xl font-black tabular-nums ${score > 0.2 ? 'text-finance-green' : score < -0.2 ? 'text-finance-red' : 'text-finance-amber'}`}>
              {score > 0 ? '+' : ''}{score.toFixed(2)}
            </p>
            <p className={`mt-1 text-sm font-semibold ${score > 0.2 ? 'text-finance-green' : score < -0.2 ? 'text-finance-red' : 'text-finance-amber'}`}>
              {result.trading_signal}
            </p>
          </div>
          <div className="flex-1 grid grid-cols-3 gap-3">
            <MetricCard label="正面新聞" value={s.positive_count} color="green" size="sm" />
            <MetricCard label="中性新聞" value={s.neutral_count} size="sm" />
            <MetricCard label="負面新聞" value={s.negative_count} color="red" size="sm" />
          </div>
        </div>
        {s.summary && (
          <p className="mt-4 rounded-lg bg-finance-bg p-4 text-sm text-finance-text">{s.summary}</p>
        )}
        {s.opportunity_signals?.length > 0 && (
          <div className="mt-3">
            <p className="mb-2 text-xs font-semibold text-finance-green">機會信號</p>
            <ul className="space-y-1">{s.opportunity_signals.map((sig, i) => <li key={i} className="text-xs text-finance-muted before:text-finance-green before:content-['▲_']">{sig}</li>)}</ul>
          </div>
        )}
        {s.risk_signals?.length > 0 && (
          <div className="mt-3">
            <p className="mb-2 text-xs font-semibold text-finance-red">風險信號</p>
            <ul className="space-y-1">{s.risk_signals.map((sig, i) => <li key={i} className="text-xs text-finance-muted before:text-finance-red before:content-['▼_']">{sig}</li>)}</ul>
          </div>
        )}
      </Collapsible>

      {result.news_items.length > 0 && (
        <Collapsible title="📰 最新新聞" defaultOpen={false}>
          <ul className="space-y-2">
            {result.news_items.map((n, i) => (
              <li key={i} className="flex gap-3 rounded-lg bg-finance-bg p-3">
                <span className="shrink-0 text-xs text-finance-muted">{i + 1}.</span>
                <div>
                  <p className="text-sm text-finance-text">{n.title}</p>
                  {n.publisher && <p className="mt-0.5 text-xs text-finance-muted">{n.publisher}</p>}
                </div>
              </li>
            ))}
          </ul>
        </Collapsible>
      )}

      <p className="text-xs text-finance-muted px-1">{result.disclaimer}</p>
    </div>
  )
}

function FactorResults({ result }: { result: FactorResult }) {
  const entries = Object.entries(result).filter(([k]) =>
    !['latest_factor_scores', 'low_snr_warning'].includes(k)
  )

  return (
    <div className="space-y-4">
      {entries.map(([ticker, data]) => {
        const d = data as { alpha_beta?: { beta: number; annual_alpha_pct: number; interpretation: string }; momentum_12m_pct?: number; volatility_regime?: string }
        if (!d?.alpha_beta) return null
        return (
          <Collapsible key={ticker} title={`${ticker} — 因子分析`}>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-4">
              <MetricCard label="Beta (β)" value={d.alpha_beta.beta.toFixed(2)} sub="系統性風險" color={Math.abs(d.alpha_beta.beta - 1) < 0.2 ? 'default' : 'amber'} />
              <MetricCard label="年化 Alpha (α)" value={`${d.alpha_beta.annual_alpha_pct > 0 ? '+' : ''}${d.alpha_beta.annual_alpha_pct.toFixed(2)}%`} color={d.alpha_beta.annual_alpha_pct >= 0 ? 'green' : 'red'} />
              <MetricCard label="12月動量因子" value={`${d.momentum_12m_pct ?? 0 > 0 ? '+' : ''}${(d.momentum_12m_pct ?? 0).toFixed(1)}%`} color={(d.momentum_12m_pct ?? 0) >= 0 ? 'green' : 'red'} />
              <MetricCard label="波動狀態" value={(d.volatility_regime ?? '').split('（')[0]} size="sm" />
            </div>
            <p className="rounded-lg bg-finance-bg p-3 text-xs text-finance-muted">{d.alpha_beta.interpretation}</p>
          </Collapsible>
        )
      })}

      {result.low_snr_warning && (
        <Collapsible title="⚠️ 低信噪比警告（Low SNR）" defaultOpen={false}>
          <p className="mb-3 text-sm text-finance-amber">{result.low_snr_warning.message}</p>
          <ul className="space-y-2">
            {result.low_snr_warning.mitigation.map((m, i) => (
              <li key={i} className="flex gap-2 text-sm text-finance-muted">
                <span className="text-finance-green shrink-0">✓</span>{m}
              </li>
            ))}
          </ul>
        </Collapsible>
      )}
    </div>
  )
}

function StationarityResults({ result }: { result: StationarityResult }) {
  return (
    <Collapsible title="📉 ADF 定態性檢定（Augmented Dickey-Fuller Test）">
      <p className="mb-4 text-xs text-finance-muted">H0：序列為非定態（有單根）；p &lt; 0.05 → 拒絕 H0 → 定態 ✓，可直接用於建模</p>
      <div className="space-y-3">
        {Object.entries(result.stationarity_tests).map(([ticker, r]) => (
          <div key={ticker} className="rounded-lg border border-finance-border bg-finance-bg p-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-mono text-sm font-bold">{ticker}</span>
              <span className={`rounded-full px-3 py-0.5 text-xs font-semibold ${r.is_stationary ? 'bg-finance-green/20 text-finance-green' : 'bg-finance-red/20 text-finance-red'}`}>
                {r.is_stationary ? '✓ 定態' : '✗ 非定態'}
              </span>
              <span className="text-xs text-finance-muted">p-value = {r.p_value.toFixed(4)}</span>
              <span className="text-xs text-finance-muted">ADF = {r.adf_statistic.toFixed(3)}</span>
            </div>
            <p className="mt-2 text-xs text-finance-muted">{r.verdict}</p>
          </div>
        ))}
      </div>
    </Collapsible>
  )
}
