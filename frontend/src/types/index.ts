export type AnalysisSection =
  | 'overview'
  | 'financials'
  | 'moat'
  | 'valuation'
  | 'growth'
  | 'debate'
  | 'investment';

export interface StockData {
  ticker: string;
  name: string;
  exchange?: string;
  currency?: string;
  price?: number;
  change?: number;
  changePercent?: number;
  marketCap?: number;
  peRatio?: number;
  roe?: number;
  revenueGrowth?: number;
  profitMargin?: number;
  debtToEquity?: number;
  updatedAt?: string;
}
