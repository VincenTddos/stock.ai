interface MetricCardProps {
  label: string
  value: string | number
  sub?: string
  color?: 'green' | 'red' | 'amber' | 'default'
  size?: 'sm' | 'md'
}

const colorMap = {
  green:   'text-finance-green',
  red:     'text-finance-red',
  amber:   'text-finance-amber',
  default: 'text-finance-text',
}

export default function MetricCard({
  label, value, sub, color = 'default', size = 'md',
}: MetricCardProps) {
  return (
    <div className="rounded-lg border border-finance-border bg-finance-bg p-4">
      <p className="mb-1 text-xs text-finance-muted">{label}</p>
      <p className={`font-bold tabular-nums ${colorMap[color]} ${size === 'md' ? 'text-2xl' : 'text-lg'}`}>
        {value}
      </p>
      {sub && <p className="mt-1 text-xs text-finance-muted">{sub}</p>}
    </div>
  )
}
