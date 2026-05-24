import { useEffect, useState } from 'react';
import { AlertTriangle, BrainCircuit, FlaskConical, TrendingUp } from 'lucide-react';
import AnalysisContent from './components/AnalysisContent';
import AnalysisTabs from './components/AnalysisTabs';
import StockMetrics from './components/StockMetrics';
import StockSearch from './components/StockSearch';
import DataScience from './pages/DataScience';
import { fetchStockInfo } from './services/api';
import type { AnalysisSection, StockData } from './types';

type Page = 'analysis' | 'datascience';

const NAV_ITEMS: { id: Page; label: string; icon: React.ReactNode }[] = [
  { id: 'analysis',    label: '股票分析', icon: <TrendingUp  className="h-4 w-4" aria-hidden="true" /> },
  { id: 'datascience', label: '數據科學', icon: <FlaskConical className="h-4 w-4" aria-hidden="true" /> },
];

export default function App() {
  const [page, setPage] = useState<Page>('analysis');

  /* ── Stock Analysis state ────────────────────────────── */
  const [ticker, setTicker]               = useState('AAPL');
  const [activeSection, setActiveSection] = useState<AnalysisSection>('overview');
  const [stock, setStock]                 = useState<StockData | null>(null);
  const [isLoadingStock, setIsLoadingStock] = useState(false);
  const [stockError, setStockError]       = useState<string | null>(null);

  useEffect(() => {
    if (page !== 'analysis') return;
    let ignore = false;

    async function loadStock() {
      setIsLoadingStock(true);
      setStockError(null);
      try {
        const data = await fetchStockInfo(ticker);
        if (!ignore) setStock(data);
      } catch (error) {
        if (!ignore) {
          setStock(null);
          setStockError(error instanceof Error ? error.message : '股票資料讀取失敗');
        }
      } finally {
        if (!ignore) setIsLoadingStock(false);
      }
    }

    loadStock();
    return () => { ignore = true; };
  }, [ticker, page]);

  function handleSearch(nextTicker: string) {
    setTicker(nextTicker);
    setActiveSection('overview');
  }

  /* ── Render ──────────────────────────────────────────── */
  return (
    <div className="min-h-screen bg-finance-bg text-finance-text">

      {/* ── Global header ───────────────────────────────── */}
      <header className="sticky top-0 z-30 border-b border-finance-border bg-finance-bg/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 md:px-8">

          {/* Brand */}
          <div className="flex items-center gap-2 shrink-0">
            <BrainCircuit className="h-6 w-6 text-finance-green" aria-hidden="true" />
            <span className="text-xl font-bold tracking-tight">Stock.AI</span>
          </div>

          {/* Primary nav */}
          <nav aria-label="主導航" className="flex gap-1">
            {NAV_ITEMS.map(({ id, label, icon }) => (
              <button
                key={id}
                onClick={() => setPage(id)}
                aria-current={page === id ? 'page' : undefined}
                className={[
                  'flex min-h-[44px] items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                  page === id
                    ? 'bg-finance-green/20 text-finance-green'
                    : 'text-finance-muted hover:bg-finance-card hover:text-finance-text',
                ].join(' ')}
              >
                {icon}
                <span>{label}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* ── Page content ────────────────────────────────── */}
      <main id="main-content" className="mx-auto max-w-7xl px-4 py-6 md:px-8">

        {/* ─── Stock Analysis page ─────────────────────── */}
        {page === 'analysis' && (
          <div className="flex flex-col gap-6">

            {/* Sub-header */}
            <div className="flex flex-col gap-5 border-b border-finance-border pb-6 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="mb-2 inline-flex items-center gap-2 rounded-md border border-finance-border bg-finance-card px-3 py-1 text-sm text-finance-muted">
                  <TrendingUp aria-hidden="true" className="h-4 w-4 text-finance-green" />
                  華爾街分析框架
                </div>
                <h1 className="text-3xl font-bold tracking-normal text-finance-text md:text-4xl">
                  股票分析
                </h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-finance-muted md:text-base">
                  輸入股票代號後，系統會串接後端資料與 AI 分析，產出完整股票研究、財務拆解、護城河、估值、成長、多空辯論與投資建議。
                </p>
              </div>
              <div className="w-full lg:max-w-xl">
                <StockSearch
                  initialTicker={ticker}
                  isLoading={isLoadingStock}
                  onSearch={handleSearch}
                />
              </div>
            </div>

            {stockError && (
              <div
                role="alert"
                className="flex items-center gap-3 rounded-lg border border-finance-red/30 bg-finance-red/10 px-4 py-3 text-finance-red"
              >
                <AlertTriangle aria-hidden="true" className="h-5 w-5 shrink-0" />
                <span>{stockError}</span>
              </div>
            )}

            <div className="grid gap-6 xl:grid-cols-[24rem_minmax(0,1fr)]">
              <aside aria-label="股票指標">
                <StockMetrics stock={stock} isLoading={isLoadingStock} />
              </aside>

              <section aria-label="AI 分析" className="space-y-4">
                <AnalysisTabs
                  activeSection={activeSection}
                  onChange={setActiveSection}
                />
                <AnalysisContent ticker={ticker} section={activeSection} />
              </section>
            </div>
          </div>
        )}

        {/* ─── Data Science page ───────────────────────── */}
        {page === 'datascience' && <DataScience />}

      </main>

      {/* ── Footer ──────────────────────────────────────── */}
      <footer className="mt-12 border-t border-finance-border py-6 text-center text-xs text-finance-muted">
        <p>Stock.AI — 僅供個人研究參考，不構成投資建議。市場有風險，投資需謹慎。</p>
      </footer>
    </div>
  );
}
