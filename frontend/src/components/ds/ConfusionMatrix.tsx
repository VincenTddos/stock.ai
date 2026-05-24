import type { ConfusionMatrixData, TestPerformance } from '../../types/ds'

interface Props { perf: TestPerformance }

export default function ConfusionMatrix({ perf }: Props) {
  const { confusion_matrix: cm, auc_roc, accuracy, f1_score, precision, recall } = perf

  return (
    <section aria-label="模型評估" className="space-y-5">
      {/* Metrics row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {([
          ['AUC-ROC', auc_roc],
          ['準確率', accuracy],
          ['F1-Score', f1_score],
          ['Precision', precision],
          ['Recall', recall],
        ] as [string, number][]).map(([label, val]) => (
          <div key={label} className="rounded-lg border border-finance-border bg-finance-bg p-3 text-center">
            <p className="text-xs text-finance-muted">{label}</p>
            <p className={`text-xl font-bold tabular-nums ${val >= 0.7 ? 'text-finance-green' : val >= 0.55 ? 'text-finance-amber' : 'text-finance-red'}`}>
              {val.toFixed(3)}
            </p>
          </div>
        ))}
      </div>

      {/* Confusion Matrix Grid */}
      <div>
        <h4 className="mb-2 text-sm font-semibold text-finance-text">混淆矩陣 (Confusion Matrix)</h4>
        <div className="grid max-w-xs grid-cols-3 gap-1 text-center text-sm">
          <div />
          <div className="py-1 text-xs text-finance-muted">預測：下跌</div>
          <div className="py-1 text-xs text-finance-muted">預測：上漲</div>
          <div className="py-1 text-left text-xs text-finance-muted">實際：下跌</div>
          <div className="rounded-lg bg-finance-green/20 p-4 font-bold text-finance-green">
            TN<br />{cm.TN}
          </div>
          <div className="rounded-lg bg-finance-red/20 p-4 font-bold text-finance-red">
            FP<br />{cm.FP}
          </div>
          <div className="py-1 text-left text-xs text-finance-muted">實際：上漲</div>
          <div className="rounded-lg bg-finance-red/20 p-4 font-bold text-finance-red">
            FN<br />{cm.FN}
          </div>
          <div className="rounded-lg bg-finance-green/20 p-4 font-bold text-finance-green">
            TP<br />{cm.TP}
          </div>
        </div>

        <ul className="mt-3 space-y-1 text-xs text-finance-muted">
          <li><span className="text-finance-green">■</span> TP={cm.TP} — {cm.note.TP}</li>
          <li><span className="text-finance-green">■</span> TN={cm.TN} — {cm.note.TN}</li>
          <li><span className="text-finance-red">■</span> FP={cm.FP} — {cm.note.FP}</li>
          <li><span className="text-finance-red">■</span> FN={cm.FN} — {cm.note.FN}</li>
        </ul>
      </div>
    </section>
  )
}
