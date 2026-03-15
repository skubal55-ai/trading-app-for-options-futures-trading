const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchApi(endpoint: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  // Market
  getMarketOverview: () => fetchApi('/api/market/overview'),
  getQuote: (symbol: string) => fetchApi(`/api/market/quote/${symbol}`),
  getHistorical: (symbol: string, period = '6mo', interval = '1d') =>
    fetchApi(`/api/market/historical/${symbol}?period=${period}&interval=${interval}`),
  getIntraday: (symbol: string, interval = '5m') =>
    fetchApi(`/api/market/intraday/${symbol}?interval=${interval}`),
  getOptionChain: (symbol: string) => fetchApi(`/api/market/option-chain/${symbol}`),
  getNifty50: () => fetchApi('/api/market/nifty50'),
  getMarketStatus: () => fetchApi('/api/market/status'),
  getWatchlist: () => fetchApi('/api/market/watchlist'),

  // Analysis
  getIndicators: (symbol: string, period = '3mo') =>
    fetchApi(`/api/analysis/indicators/${symbol}?period=${period}`),
  getFibonacci: (symbol: string) => fetchApi(`/api/analysis/fibonacci/${symbol}`),
  getPivotPoints: (symbol: string) => fetchApi(`/api/analysis/pivot-points/${symbol}`),
  getChartData: (symbol: string, period = '3mo', interval = '1d') =>
    fetchApi(`/api/analysis/chart-data/${symbol}?period=${period}&interval=${interval}`),

  // Screener
  scanStocks: (strategies?: string, signal?: string, limit = 20) => {
    const params = new URLSearchParams();
    if (strategies) params.set('strategies', strategies);
    if (signal) params.set('signal', signal);
    params.set('limit', String(limit));
    return fetchApi(`/api/screener/scan?${params}`);
  },
  getStrategies: () => fetchApi('/api/screener/strategies'),
  quickScan: (strategy: string, limit = 10) =>
    fetchApi(`/api/screener/quick-scan/${strategy}?limit=${limit}`),

  // Trading
  placeOrder: (order: {
    symbol: string;
    trade_type: string;
    order_type: string;
    quantity: number;
    price: number;
    stop_loss?: number;
    target?: number;
    segment?: string;
    mode?: string;
  }) => fetchApi('/api/trading/order', { method: 'POST', body: JSON.stringify(order) }),
  getPositions: (status = 'ALL') => fetchApi(`/api/trading/positions?status=${status}`),
  getPortfolio: () => fetchApi('/api/trading/portfolio'),
  getOrders: () => fetchApi('/api/trading/orders'),
  resetPaperTrading: () => fetchApi('/api/trading/reset', { method: 'POST' }),
  getAutoTradeSettings: () => fetchApi('/api/trading/auto-trade/settings'),
  updateAutoTradeSettings: (settings: Record<string, unknown>) =>
    fetchApi('/api/trading/auto-trade/settings', { method: 'POST', body: JSON.stringify(settings) }),

  // Backtesting
  getBacktestStrategies: () => fetchApi('/api/backtest/strategies'),
  runBacktest: (strategy: string, period = '1y', holdingDays = 10, capital = 100000, symbols?: string) => {
    const params = new URLSearchParams();
    params.set('strategy', strategy);
    params.set('period', period);
    params.set('holding_days', String(holdingDays));
    params.set('capital', String(capital));
    if (symbols) params.set('symbols', symbols);
    return fetchApi(`/api/backtest/run?${params}`);
  },
};
