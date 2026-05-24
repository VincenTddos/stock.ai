import type { SignalType, Confidence } from '../../types/ds'

interface Props {
  signal: SignalType
  confidence: Confidence
  probUp: number
}

const signalStyle: Record<SignalType, string> = {
  BUY:   'bg-finance-green/20 border-finance-green text-finance-green',
  HOLD:  'bg-finance-amber/20 border-finance-amber text-finance-amber',
  AVOID: 'bg-finance-red/20 border-finance-red text-finance-red',
}

const signalLabel: Record<SignalType, string> = {
  BUY:   '買入 BUY',
  HOLD:  '觀望 HOLD',
  AVOID: '避開 AVOID',
}

const confLabel: Record<Confidence, string> = {
  HIGH:   '高信心',
  MEDIUM: '中信心',
  LOW:    '低信心',
}

export default function SignalBadge({ signal, confidence, probUp }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      {/* Main signal */}
      <div className={`rounded-xl border-2 px-6 py-4 text-center ${signalStyle[signal]}`}>
        <p className="text-xs text-finance-muted">當前建議</p>
        <p className="text-2xl font-black">{signalLabel[signal]}</p>
        <p className="text-xs">{confLabel[confidence]}</p>
      </div>

      {/* Probability bar */}
      <div className="flex-1 min-w-[160px]">
        <p className="mb-1 text-xs text-finance-muted">上漲機率 P(↑)</p>
        <div className="flex items-center gap-2">
          <div className="h-4 flex-1 overflow-hidden rounded-full bg-finance-border">
            <div
              className="h-full rounded-full bg-finance-green transition-all"
              style={{ width: `${probUp * 100}%` }}
              role="progressbar"
              aria-valuenow={Math.round(probUp * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
          <span className="w-12 text-right font-bold tabular-nums text-finance-green">
            {(probUp * 100).toFixed(1)}%
          </span>
        </div>
        <div className="mt-1 flex justify-between text-xs text-finance-muted">
          <span>0%</span>
          <span className="text-finance-amber">50%</span>
          <span>100%</span>
        </div>
      </div>
    </div>
  )
}
