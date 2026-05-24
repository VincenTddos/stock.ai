import type { CorrelationMatrix } from '../../types/ds'

interface Props { matrix: CorrelationMatrix }

function cellColor(v: number): string {
  // -1 → red, 0 → neutral, +1 → green
  if (v >= 0.7)  return 'bg-finance-green text-[#07140a]'
  if (v >= 0.4)  return 'bg-[#1a4731] text-finance-green'
  if (v >= 0.1)  return 'bg-[#162318] text-[#4ade80]'
  if (v >= -0.1) return 'bg-finance-card text-finance-muted'
  if (v >= -0.4) return 'bg-[#2d1515] text-[#f87171]'
  if (v >= -0.7) return 'bg-[#3d1515] text-finance-red'
  return 'bg-finance-red text-white'
}

export default function CorrelationHeatmap({ matrix }: Props) {
  const { tickers, cells } = matrix
  const getValue = (row: string, col: string) =>
    cells.find(c => c.y === row && c.x === col)?.value ?? 0

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-center text-sm" role="grid" aria-label="相關係數矩陣">
        <thead>
          <tr>
            <th className="p-2 text-finance-muted" scope="col" />
            {tickers.map(t => (
              <th key={t} className="p-2 font-mono text-xs text-finance-muted" scope="col">{t}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tickers.map(row => (
            <tr key={row}>
              <td className="p-2 text-left font-mono text-xs text-finance-muted">{row}</td>
              {tickers.map(col => {
                const v = getValue(row, col)
                return (
                  <td
                    key={col}
                    className={`p-2 font-bold tabular-nums transition-colors ${cellColor(v)}`}
                    title={`${row} vs ${col}: ${v}`}
                  >
                    {v.toFixed(2)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 flex items-center gap-3 text-xs text-finance-muted">
        <span>相關性：</span>
        {[[-1,'強負相關'],[-0.5,'負相關'],[0,'中性'],[0.5,'正相關'],[1,'強正相關']].map(([v,l]) => (
          <span key={String(v)} className={`rounded px-2 py-0.5 ${cellColor(Number(v))}`}>{l}</span>
        ))}
      </div>
    </div>
  )
}
