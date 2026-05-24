import { Search } from 'lucide-react';
import { FormEvent, useState } from 'react';

interface StockSearchProps {
  initialTicker: string;
  isLoading: boolean;
  onSearch: (ticker: string) => void;
}

export default function StockSearch({
  initialTicker,
  isLoading,
  onSearch,
}: StockSearchProps) {
  const [value, setValue] = useState(initialTicker);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const ticker = value.trim().toUpperCase();

    if (ticker) {
      onSearch(ticker);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full gap-3">
      <div className="relative flex-1">
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-finance-muted"
        />
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="輸入股票代號，例如 AAPL、TSM、NVDA"
          className="h-12 w-full rounded-md border border-finance-border bg-finance-card pl-12 pr-4 text-finance-text outline-none transition focus:border-finance-green focus:ring-2 focus:ring-finance-green/25"
        />
      </div>
      <button
        type="submit"
        disabled={isLoading}
        className="inline-flex h-12 items-center gap-2 rounded-md bg-finance-green px-5 font-semibold text-[#07140a] transition hover:bg-[#51d368] disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Search aria-hidden="true" className="h-4 w-4" />
        搜尋
      </button>
    </form>
  );
}
