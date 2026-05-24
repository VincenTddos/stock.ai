import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import type { BacktestResult } from '../../types/ds'
import MetricCard from './MetricCard'

interface Props { backtest: BacktestResult }

function fmt(n: number, suffix = '%') {
  return `${n > 0 ? '+' : ''}${n.toFixed(2)}${suffix}`
}

export default function BacktestChart({ backtest }: Props) {
  const { strategy, benchmark, alpha_pct, timeseries } = backtest

  // Sample every N points for performance (keep ≤ 300 points)
  const step = Math.max(1, Math.floor(timeseries.length / 300))
  const data = timeseries.filter((_, i) => i % step === 0)

  return (
    <section aria-label="回測績效">
      {/* KPI Row */}
      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard
          label="策略總報酬"
          value={fmt(strategy.total_return_pct)}
          color={strategy.total_return_pct >= 0 ? 'green' : 'red'}
        />
        <MetricCard
          label="超額報酬 (Alpha)"
          value={fmt(alpha_pct)}
          sub="策略 vs 買入持有"
          color={alpha_pct >= 0 ? 'green' : 'red'}
        />
        <MetricCard
          label="夏普比率"
          value={strategy.sharpe_ratio.toFixed(2)}
          sub="年化"
          color={strategy.sharpe_ratio >= 1 ? 'green' : strategy.sharpe_ratio >= 0 ? 'default' : 'red'}
        />
        <MetricCard
          label="最大回撤 (MDD)"
          value={fmt(strategy.max_drawdown_pct)}
          color="red"
        />
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <MetricCard label="勝率" value={`${strategy.win_rate_pct.toFixed(1)}%`} />
        <MetricCard label="在場時間" value={`${strategy.days_in_market_pct.toFixed(1)}%`} />
        <MetricCard
          label="基準報酬"
          value={fmt(benchmark.total_return_pct)}
          sub="買入持有"
          color={benchmark.total_return_pct >= 0 ? 'green' : 'red'}
        />
      </div>

      {/* Cumulative Return Chart */}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#8b949e', fontSize: 10 }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: '#8b949e', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={v => `${v}%`}
            />
            <Tooltip
              contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }}
              labelStyle={{ color: '#8b949e' }}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(value: any, name: any) => [
                `${(value as number).toFixed(2)}%`,
                name === 'strategy_cum_return' ? '策略報酬' : '買入持有',
              ]}
            />
            <Legend
              formatter={v => v === 'strategy_cum_return' ? '策略報酬' : '買入持有'}
              wrapperStyle={{ color: '#8b949e', fontSize: 12 }}
            />
            <ReferenceLine y={0} stroke="#30363d" />
            <Line
              type="monotone"
              dataKey="strategy_cum_return"
              stroke="#3fb950"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="benchmark_cum_return"
              stroke="#8b949e"
              strokeWidth={1.5}
              strokeDasharray="4 2"
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
