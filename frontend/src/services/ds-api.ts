import type {
  CorrelationResult, SignalResult,
  SentimentResult, FactorResult, StationarityResult,
} from '../types/ds'

const BASE = '/api/ds'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? '請求失敗')
  }
  return res.json()
}

export const dsApi = {
  correlation: (params: {
    tw_tickers: string[]
    us_tickers: string[]
    period: string
    rolling_window: number
  }) => post<CorrelationResult>('/correlation', params),

  signals: (params: {
    target: string
    features: string[]
    period: string
    train_ratio: number
  }) => post<SignalResult>('/signals', params),

  sentiment: (params: { ticker: string; company_name: string }) =>
    post<SentimentResult>('/sentiment', params),

  factors: (params: {
    tw_tickers: string[]
    market_ticker: string
    period: string
  }) => post<FactorResult>('/factors', params),

  stationarity: (params: { tickers: string[]; period: string }) =>
    post<StationarityResult>('/stationarity', params),
}
