import type { AnalysisSection, StockData } from '../types';

export async function fetchStockInfo(ticker: string): Promise<StockData> {
  const response = await fetch(`/api/stock/${encodeURIComponent(ticker)}`);

  if (!response.ok) {
    throw new Error(`無法取得 ${ticker.toUpperCase()} 的股票資訊`);
  }

  return response.json();
}

export async function streamAnalysis(
  ticker: string,
  section: AnalysisSection,
  onChunk: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(
    `/api/analyze/${encodeURIComponent(ticker)}/${section}`,
    {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream',
      },
      signal,
    },
  );

  if (!response.ok || !response.body) {
    throw new Error('分析串流啟動失敗');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() ?? '';

    for (const event of events) {
      const dataLine = event
        .split('\n')
        .find((line) => line.startsWith('data:'));

      if (!dataLine) {
        continue;
      }

      const payload = dataLine.replace(/^data:\s*/, '').trim();

      if (payload === '[DONE]') {
        return;
      }

      try {
        const parsed = JSON.parse(payload) as { text?: string };
        if (parsed.text) {
          onChunk(parsed.text);
        }
      } catch {
        onChunk(payload);
      }
    }
  }
}
