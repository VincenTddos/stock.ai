// ── Data Science Module Types ──────────────────────────────

export type DSTab = 'correlation' | 'signals' | 'sentiment' | 'factors' | 'stationarity'

export type SignalType = 'BUY' | 'HOLD' | 'AVOID'
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW'

// ── Correlation Analysis ───────────────────────────────────

export interface CorrelationCell {
  x: string
  y: string
  value: number
}

export interface CorrelationMatrix {
  tickers: string[]
  cells: CorrelationCell[]
}

export interface RollingCorrPoint {
  date: string
  correlation: number
}

export interface RollingCorrPair {
  pair: string
  data: RollingCorrPoint[]
}

export interface GrangerResult {
  cause?: string
  effect?: string
  conclusion?: string
  error?: string
}

export interface LagPoint {
  lag: number
  correlation: number
  label: string
}

export interface AssetStats {
  annualized_return: number
  annualized_volatility: number
  sharpe_approx: number
  skewness: number
  kurtosis: number
}

export interface CorrelationResult {
  tw_tickers: string[]
  us_tickers: string[]
  period: string
  period_days: number
  correlation_matrix: CorrelationMatrix
  rolling_correlations: RollingCorrPair[]
  granger_causality: GrangerResult[]
  lag_analysis: LagPoint[]
  stats: Record<string, AssetStats>
  pca?: PCASummary
  market_regimes?: MarketRegimeResult
}

// ── ML Signals ─────────────────────────────────────────────

export interface WalkForwardFold {
  fold: number
  auc_roc: number
  accuracy: number
  n_train: number
  n_val: number
}

export interface WalkForwardResult {
  folds: WalkForwardFold[]
  mean_auc_roc: number
  mean_accuracy: number
  note: string
}

export interface ConfusionMatrixData {
  TP: number
  TN: number
  FP: number
  FN: number
  note: Record<string, string>
}

export interface TestPerformance {
  auc_roc: number
  accuracy: number
  f1_score: number
  precision: number
  recall: number
  confusion_matrix: ConfusionMatrixData
  n_samples: number
}

export interface StrategyPerf {
  total_return_pct: number
  sharpe_ratio: number
  max_drawdown_pct: number
  win_rate_pct: number
  days_in_market_pct: number
}

export interface BacktestPoint {
  date: string
  strategy_cum_return: number
  benchmark_cum_return: number
  position: number
  signal_prob: number
}

export interface BacktestResult {
  strategy: StrategyPerf
  benchmark: { total_return_pct: number; sharpe_ratio: number; max_drawdown_pct: number }
  alpha_pct: number
  timeseries: BacktestPoint[]
}

export interface FeatureImportance {
  feature: string
  importance: number
}

export interface SignalPoint {
  date: string
  probability_up: number
  signal: SignalType
  actual_return_pct: number
}

export interface CurrentSignal {
  probability_up: number
  probability_down: number
  recommendation: SignalType
  confidence: Confidence
}

export interface SignalMeta {
  target: string
  feature_tickers: string[]
  period: string
  total_samples: number
  train_samples: number
  test_samples: number
  train_end_date: string
  anti_leakage_measures: string[]
}

export interface SignalResult {
  walk_forward: WalkForwardResult
  test_performance: TestPerformance
  backtest: BacktestResult
  feature_importance: FeatureImportance[]
  signals: SignalPoint[]
  current_signal: CurrentSignal
  meta: SignalMeta
}

// ── Sentiment ──────────────────────────────────────────────

export interface NewsItem {
  title: string
  publisher: string
}

export interface SentimentScore {
  overall_score: number
  confidence: number
  positive_count: number
  negative_count: number
  neutral_count: number
  key_themes: string[]
  risk_signals: string[]
  opportunity_signals: string[]
  summary: string
}

export interface SentimentResult {
  ticker: string
  news_items: NewsItem[]
  sentiment_score: SentimentScore
  trading_signal: string
  disclaimer: string
}

// ── PCA / Unsupervised ─────────────────────────────────────

export interface PCASummary {
  n_components: number
  explained_variance_ratio: number[]
  cumulative_explained: number[]
  eigenvalues: number[]
  interpretation: Record<string, string>
}

export interface RegimeStat {
  regime_id: number
  n_days: number
  pct_of_time: number
  avg_daily_return: number
  volatility: number
}

export interface RegimePoint {
  date: string
  regime_id: number
  regime_name: string
  is_train: boolean
}

export interface MarketRegimeResult {
  n_regimes: number
  regime_names: Record<number, string>
  regime_stats: Record<string, RegimeStat>
  timeseries: RegimePoint[]
  current_regime: RegimePoint | null
}

// ── Factors ────────────────────────────────────────────────

export interface AlphaBeta {
  beta: number
  annual_alpha_pct: number
  interpretation: string
}

export interface FactorEntry {
  alpha_beta: AlphaBeta
  momentum_12m_pct: number
  recent_volatility_annual: number
  historical_volatility_annual: number
  volatility_regime: string
}

export type LowSnrWarning = { message: string; mitigation: string[] }

export interface FactorResult {
  [ticker: string]: FactorEntry | Record<string, number> | LowSnrWarning
  latest_factor_scores: Record<string, number>
  low_snr_warning: LowSnrWarning
}

// ── Stationarity ───────────────────────────────────────────

export interface AdfResult {
  adf_statistic: number
  p_value: number
  is_stationary: boolean
  critical_values: Record<string, number>
  verdict: string
}

export interface StationarityResult {
  tickers: string[]
  stationarity_tests: Record<string, AdfResult>
}
