import type { AnalysisSection } from '../types';

interface TabItem {
  id: AnalysisSection;
  label: string;
}

interface AnalysisTabsProps {
  activeSection: AnalysisSection;
  onChange: (section: AnalysisSection) => void;
}

export const analysisTabs: TabItem[] = [
  { id: 'overview', label: '① 全析' },
  { id: 'financials', label: '② 財務' },
  { id: 'moat', label: '③ 護城河' },
  { id: 'valuation', label: '④ 估值' },
  { id: 'growth', label: '⑤ 成長' },
  { id: 'debate', label: '⑥ 多空辯論' },
  { id: 'investment', label: '⑦ 投資建議' },
];

export default function AnalysisTabs({
  activeSection,
  onChange,
}: AnalysisTabsProps) {
  return (
    <nav className="flex gap-2 overflow-x-auto rounded-lg border border-finance-border bg-finance-card p-2">
      {analysisTabs.map((tab) => {
        const isActive = tab.id === activeSection;

        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`h-10 shrink-0 rounded-md px-4 text-sm font-semibold transition ${
              isActive
                ? 'bg-finance-green text-[#07140a]'
                : 'text-finance-muted hover:bg-finance-bg hover:text-finance-text'
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}
