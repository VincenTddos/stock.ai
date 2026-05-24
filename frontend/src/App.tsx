import { useEffect, useState } from 'react';
import { AlertTriangle, BrainCircuit } from 'lucide-react';
import AnalysisContent from './components/AnalysisContent';
import AnalysisTabs from './components/AnalysisTabs';
import StockMetrics from './components/StockMetrics';
import StockSearch from './components/StockSearch';
import { fetchStockInfo } from './services/api';
import type { AnalysisSection, StockData } from './types';

export default function App() {
  const [ticker, setTicker] = useState('AAPL');
  const [activeSection, setActiveSection] = useState<AnalysisSection>('overview');
  const [stock, setStock] = useState<StockData | null>(null);
  const [isLoadingStock, setIsLoadingStock] = useState(false);
  const [stockError, setStockError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function loadStock() {
      setIsLoadingStock(true);
      setStockError(null);

      try {
        const data = await fetchStockInfo(ticker);
        if (!ignore) {
          setStock(data);
        }
      } catch (error) {
        if (!ignore) {
          setStock(null);
          setStockError(error instanceof Error ? error.message : '股票資料讀取失敗');
        }
      } finally {
        if (!ignore) {
          setIsLoadingStock(false);
        }
      }
    }

    loadStock();

    return () => {
      ignore = true;
    };
  }, [ticker]);

  function handleSearch(nextTicker: string) {
    setTicker(nextTicker);
    setActiveSection('overview');
  }

  return (
    <main className="min-h-screen bg-finance-bg px-4 py-6 text-finance-text md:px-8">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="flex flex-col gap-5 border-b border-finance-border pb-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-md border border-finance-border bg-finance-card px-3 py-1 text-sm text-finance-muted">
              <BrainCircuit aria-hidden="true" className="h-4 w-4 text-finance-green" />
              華爾街分析框架
            </div>
            <h1 className="text-3xl font-bold tracking-normal text-finance-text md:text-4xl">
              Stock.AI
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
        </header>

        {stockError && (
          <div className="flex items-center gap-3 rounded-lg border border-finance-red/30 bg-finance-red/10 px-4 py-3 text-finance-red">
            <AlertTriangle aria-hidden="true" className="h-5 w-5 shrink-0" />
            <span>{stockError}</span>
          </div>
        )}

        <div className="grid gap-6 xl:grid-cols-[24rem_minmax(0,1fr)]">
          <aside className="space-y-6">
            <StockMetrics stock={stock} isLoading={isLoadingStock} />
          </aside>

          <section className="space-y-4">
            <AnalysisTabs
              activeSection={activeSection}
              onChange={setActiveSection}
            />
            <AnalysisContent ticker={ticker} section={activeSection} />
          </section>
        </div>
      </div>
    </main>
  );
}
