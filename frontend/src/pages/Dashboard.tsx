import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { TrendingUp, TrendingDown, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface Quote {
  symbol: string;
  name: string;
  ltp: number;
  change: number;
  change_percent: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface MarketData {
  nifty50?: Quote;
  nifty_bank?: Quote;
  india_vix?: number;
  market_status: string;
  top_gainers: Quote[];
  top_losers: Quote[];
  most_active: Quote[];
}

export default function Dashboard() {
  const [data, setData] = useState<MarketData | null>(null);
  const [niftyChart, setNiftyChart] = useState<{ date: string; close: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [overview, historical] = await Promise.all([
        api.getMarketOverview(),
        api.getHistorical('NIFTY_50', '1mo', '1d').catch(() => ({ data: [] })),
      ]);
      setData(overview);
      if (historical.data) {
        setNiftyChart(historical.data.map((d: { date: string; close: number }) => ({
          date: d.date.split('T')[0],
          close: d.close,
        })));
      }
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4" />
          <p className="text-gray-400">Loading market data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold text-white">Market Dashboard</h2>

      {/* Index Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {data?.nifty50 && (
          <IndexCard title="NIFTY 50" quote={data.nifty50} />
        )}
        {data?.nifty_bank && (
          <IndexCard title="BANK NIFTY" quote={data.nifty_bank} />
        )}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-gray-400 text-sm">INDIA VIX</p>
          <p className="text-2xl font-bold text-white mt-1">{data?.india_vix ?? 'N/A'}</p>
          <p className="text-xs text-gray-500 mt-1">Volatility Index</p>
        </div>
      </div>

      {/* Nifty Chart */}
      {niftyChart.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <h3 className="text-white font-semibold mb-4">NIFTY 50 - 1 Month</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={niftyChart}>
              <defs>
                <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                labelStyle={{ color: '#9ca3af' }}
                itemStyle={{ color: '#3b82f6' }}
              />
              <Area type="monotone" dataKey="close" stroke="#3b82f6" fill="url(#colorClose)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Gainers / Losers / Active */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StockList title="Top Gainers" stocks={data?.top_gainers ?? []} icon={<TrendingUp className="text-green-400" size={18} />} />
        <StockList title="Top Losers" stocks={data?.top_losers ?? []} icon={<TrendingDown className="text-red-400" size={18} />} />
        <StockList title="Most Active" stocks={data?.most_active ?? []} icon={<Activity className="text-blue-400" size={18} />} />
      </div>
    </div>
  );
}

function IndexCard({ title, quote }: { title: string; quote: Quote }) {
  const isPositive = quote.change >= 0;
  return (
    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-gray-400 text-sm">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{quote.ltp.toLocaleString('en-IN')}</p>
        </div>
        <div className={`flex items-center gap-1 px-2 py-1 rounded text-sm font-medium ${
          isPositive ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
        }`}>
          {isPositive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
          {quote.change_percent.toFixed(2)}%
        </div>
      </div>
      <div className="mt-2 text-sm text-gray-500">
        Change: <span className={isPositive ? 'text-green-400' : 'text-red-400'}>
          {isPositive ? '+' : ''}{quote.change.toFixed(2)}
        </span>
      </div>
      <div className="mt-1 flex gap-4 text-xs text-gray-500">
        <span>O: {quote.open}</span>
        <span>H: {quote.high}</span>
        <span>L: {quote.low}</span>
      </div>
    </div>
  );
}

function StockList({ title, stocks, icon }: { title: string; stocks: Quote[]; icon: React.ReactNode }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h3 className="text-white font-semibold text-sm">{title}</h3>
      </div>
      <div className="space-y-2">
        {stocks.map((stock) => (
          <div key={stock.symbol} className="flex justify-between items-center py-1.5 border-b border-gray-700/50 last:border-0">
            <div>
              <p className="text-white text-sm font-medium">{stock.symbol}</p>
              <p className="text-gray-500 text-xs">{stock.name?.slice(0, 20)}</p>
            </div>
            <div className="text-right">
              <p className="text-white text-sm">{stock.ltp.toFixed(2)}</p>
              <p className={`text-xs ${stock.change_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
              </p>
            </div>
          </div>
        ))}
        {stocks.length === 0 && <p className="text-gray-500 text-sm">No data available</p>}
      </div>
    </div>
  );
}
