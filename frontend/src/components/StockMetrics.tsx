import { Activity, Banknote, BarChart3, LineChart, Percent, Scale } from 'lucide-react';
import type { StockData } from '../types';

interface StockMetricsProps {
  stock: StockData | null;
  isLoading: boolean;
}

const formatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
});

function compactCurrency(value?: number, currency = 'USD') {
  if (value === undefined || value === null) {
    return 'N/A';
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    notation: 'compact',
    maximumFractionDigits: 2,
  }).format(value);
}

function percent(value?: number) {
  if (value === undefined || value === null) {
    return 'N/A';
  }

  return `${formatter.format(value)}%`;
}

export default function StockMetrics({ stock, isLoading }: StockMetricsProps) {
  const currency = stock?.currency ?? 'USD';
  const metrics = [
    {
      label: '股價',
      value: compactCurrency(stock?.price, currency),
      icon: Banknote,
    },
    {
      label: '市值',
      value: compactCurrency(stock?.marketCap, currency),
      icon: BarChart3,
    },
    {
      label: 'P/E',
      value: stock?.peRatio ? formatter.format(stock.peRatio) : 'N/A',
      icon: LineChart,
    },
    {
      label: 'ROE',
      value: percent(stock?.roe),
      icon: Percent,
    },
    {
      label: '利潤率',
      value: percent(stock?.profitMargin),
      icon: Activity,
    },
    {
      label: '負債權益比',
      value: stock?.debtToEquity ? formatter.format(stock.debtToEquity) : 'N/A',
      icon: Scale,
    },
  ];

  return (
    <section className="rounded-lg border border-finance-border bg-finance-card p-5 shadow-panel">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-finance-muted">股票資訊</p>
          <h2 className="mt-1 text-2xl font-semibold text-finance-text">
            {stock ? `${stock.name} (${stock.ticker})` : '等待搜尋'}
          </h2>
          {stock?.exchange && (
            <p className="mt-1 text-sm text-finance-muted">{stock.exchange}</p>
          )}
        </div>
        {stock?.changePercent !== undefined && (
          <div
            className={`rounded-md px-3 py-2 text-sm font-semibold ${
              stock.changePercent >= 0
                ? 'bg-finance-green/10 text-finance-green'
                : 'bg-finance-red/10 text-finance-red'
            }`}
          >
            {stock.changePercent >= 0 ? '+' : ''}
            {formatter.format(stock.changePercent)}%
          </div>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.map((metric) => {
          const Icon = metric.icon;

          return (
            <div
              key={metric.label}
              className="rounded-md border border-finance-border bg-finance-bg p-4"
            >
              <div className="mb-3 flex items-center justify-between text-finance-muted">
                <span className="text-sm">{metric.label}</span>
                <Icon aria-hidden="true" className="h-4 w-4" />
              </div>
              <div className="text-xl font-semibold text-finance-text">
                {isLoading ? '載入中' : metric.value}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
