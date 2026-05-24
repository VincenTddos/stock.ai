import { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Loader2, PlayCircle } from 'lucide-react';
import { streamAnalysis } from '../services/api';
import type { AnalysisSection } from '../types';

interface AnalysisContentProps {
  ticker: string;
  section: AnalysisSection;
}

const sectionTitles: Record<AnalysisSection, string> = {
  overview: '完整股票分析',
  financials: '五年財務拆解',
  moat: '競爭護城河評估',
  valuation: '投資銀行式估值',
  growth: '未來成長潛力',
  debate: '多空分析師辯論',
  investment: '投資建議',
};

export default function AnalysisContent({ ticker, section }: AnalysisContentProps) {
  const [content, setContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const title = useMemo(() => sectionTitles[section], [section]);

  useEffect(() => {
    const controller = new AbortController();

    async function runAnalysis() {
      if (!ticker) {
        return;
      }

      setContent('');
      setError(null);
      setIsStreaming(true);

      try {
        await streamAnalysis(
          ticker,
          section,
          (text) => setContent((current) => current + text),
          controller.signal,
        );
      } catch (streamError) {
        if (!controller.signal.aborted) {
          setError(
            streamError instanceof Error ? streamError.message : '分析時發生未知錯誤',
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsStreaming(false);
        }
      }
    }

    runAnalysis();

    return () => controller.abort();
  }, [ticker, section]);

  return (
    <section className="min-h-[32rem] rounded-lg border border-finance-border bg-finance-card shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-finance-border px-5 py-4">
        <div>
          <p className="text-sm text-finance-muted">{ticker}</p>
          <h2 className="text-xl font-semibold text-finance-text">{title}</h2>
        </div>
        <div className="flex items-center gap-2 text-sm text-finance-muted">
          {isStreaming ? (
            <>
              <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
              生成中
            </>
          ) : (
            <>
              <PlayCircle aria-hidden="true" className="h-4 w-4" />
              已就緒
            </>
          )}
        </div>
      </div>

      <div className="prose prose-invert max-w-none px-5 py-5 prose-headings:text-finance-text prose-p:text-[#c9d1d9] prose-strong:text-finance-text prose-a:text-finance-green prose-li:text-[#c9d1d9] prose-table:text-sm prose-th:border-finance-border prose-td:border-finance-border">
        {error && (
          <div className="rounded-md border border-finance-red/30 bg-finance-red/10 p-4 text-finance-red">
            {error}
          </div>
        )}
        {!error && content && (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        )}
        {!error && !content && (
          <div className="rounded-md border border-dashed border-finance-border bg-finance-bg p-6 text-finance-muted">
            正在連接分析引擎，請稍候。
          </div>
        )}
      </div>
    </section>
  );
}
