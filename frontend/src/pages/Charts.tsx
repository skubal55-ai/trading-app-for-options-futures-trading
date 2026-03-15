import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ComposedChart, Bar, Legend } from 'recharts';
import { Search, TrendingUp } from 'lucide-react';

interface ChartDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma_20?: number;
  sma_50?: number;
  ema_9?: number;
  ema_21?: number;
}

interface Indicators {
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  macd_histogram?: number;
  bollinger_upper?: number;
  bollinger_lower?: number;
  supertrend?: number;
  supertrend_direction?: string;
  adx?: number;
  atr?: number;
  vwap?: number;
  stochastic_k?: number;
  stochastic_d?: number;
  [key: string]: number | string | undefined;
}

interface FibLevel {
  trend: string;
  level_0: number;
  level_236: number;
  level_382: number;
  level_500: number;
  level_618: number;
  level_786: number;
  level_1: number;
}

interface PivotPoints {
  pivot: number;
  r1: number;
  r2: number;
  r3: number;
  s1: number;
  s2: number;
  s3: number;
}

export default function Charts() {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [searchInput, setSearchInput] = useState('RELIANCE');
  const [period, setPeriod] = useState('3mo');
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [indicators, setIndicators] = useState<Indicators>({});
  const [fibonacci, setFibonacci] = useState<FibLevel | null>(null);
  const [pivots, setPivots] = useState<PivotPoints | null>(null);
  const [loading, setLoading] = useState(false);
  const [showMA, setShowMA] = useState(true);
  const [showVolume, setShowVolume] = useState(true);

  useEffect(() => {
    loadChart();
  }, [symbol, period]);

  const loadChart = async () => {
    setLoading(true);
    try {
      const res = await api.getChartData(symbol, period, '1d');
      if (res.chart_data) setChartData(res.chart_data.map((d: ChartDataPoint) => ({
        ...d,
        date: d.date.split('T')[0],
      })));
      if (res.indicators) setIndicators(res.indicators);
      if (res.fibonacci) setFibonacci(res.fibonacci);
      if (res.pivot_points) setPivots(res.pivot_points);
    } catch (err) {
      console.error('Chart load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    if (searchInput.trim()) {
      setSymbol(searchInput.trim().toUpperCase());
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-4 flex-wrap">
        <h2 className="text-2xl font-bold text-white">Technical Charts</h2>
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-4 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              placeholder="Enter symbol (e.g. RELIANCE, TCS)"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <button onClick={handleSearch} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition-colors">
            Analyze
          </button>
        </div>
        <div className="flex gap-1">
          {['1mo', '3mo', '6mo', '1y', '2y'].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                period === p ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {p.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Toggles */}
      <div className="flex gap-3">
        <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
          <input type="checkbox" checked={showMA} onChange={(e) => setShowMA(e.target.checked)} className="accent-blue-500" />
          Moving Averages
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
          <input type="checkbox" checked={showVolume} onChange={(e) => setShowVolume(e.target.checked)} className="accent-blue-500" />
          Volume
        </label>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      ) : (
        <>
          {/* Price Chart */}
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <h3 className="text-white font-semibold mb-2">{symbol} - Price Chart</h3>
            <ResponsiveContainer width="100%" height={350}>
              <ComposedChart data={chartData}>
                <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => v.slice(5)} />
                <YAxis yAxisId="price" domain={['auto', 'auto']} tick={{ fill: '#9ca3af', fontSize: 10 }} />
                {showVolume && <YAxis yAxisId="volume" orientation="right" tick={{ fill: '#9ca3af', fontSize: 10 }} />}
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#9ca3af' }}
                />
                <Legend />
                <Line yAxisId="price" type="monotone" dataKey="close" stroke="#3b82f6" dot={false} strokeWidth={2} name="Close" />
                {showMA && (
                  <>
                    <Line yAxisId="price" type="monotone" dataKey="sma_20" stroke="#f59e0b" dot={false} strokeWidth={1} name="SMA 20" strokeDasharray="3 3" />
                    <Line yAxisId="price" type="monotone" dataKey="sma_50" stroke="#ef4444" dot={false} strokeWidth={1} name="SMA 50" strokeDasharray="5 5" />
                    <Line yAxisId="price" type="monotone" dataKey="ema_9" stroke="#10b981" dot={false} strokeWidth={1} name="EMA 9" />
                    <Line yAxisId="price" type="monotone" dataKey="ema_21" stroke="#8b5cf6" dot={false} strokeWidth={1} name="EMA 21" />
                  </>
                )}
                {showVolume && <Bar yAxisId="volume" dataKey="volume" fill="#374151" opacity={0.5} name="Volume" />}
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Indicators Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <IndicatorCard label="RSI (14)" value={indicators.rsi} suffix="" color={
              (indicators.rsi ?? 50) > 70 ? 'text-red-400' : (indicators.rsi ?? 50) < 30 ? 'text-green-400' : 'text-white'
            } />
            <IndicatorCard label="MACD" value={indicators.macd} color={
              (indicators.macd ?? 0) > 0 ? 'text-green-400' : 'text-red-400'
            } />
            <IndicatorCard label="ADX" value={indicators.adx} color="text-blue-400" />
            <IndicatorCard label="ATR" value={indicators.atr} color="text-yellow-400" />
            <IndicatorCard label="Supertrend" value={indicators.supertrend} color={
              indicators.supertrend_direction === 'UP' ? 'text-green-400' : 'text-red-400'
            } suffix={indicators.supertrend_direction ? ` (${indicators.supertrend_direction})` : ''} />
            <IndicatorCard label="VWAP" value={indicators.vwap} color="text-purple-400" />
            <IndicatorCard label="Stoch %K" value={indicators.stochastic_k} color="text-cyan-400" />
            <IndicatorCard label="Stoch %D" value={indicators.stochastic_d} color="text-cyan-300" />
          </div>

          {/* Fibonacci & Pivot Points */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {fibonacci && (
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                  <TrendingUp size={16} className="text-yellow-400" />
                  Fibonacci Levels ({fibonacci.trend})
                </h3>
                <div className="space-y-1.5">
                  {[
                    { label: '0%', value: fibonacci.level_0 },
                    { label: '23.6%', value: fibonacci.level_236 },
                    { label: '38.2%', value: fibonacci.level_382 },
                    { label: '50%', value: fibonacci.level_500 },
                    { label: '61.8%', value: fibonacci.level_618 },
                    { label: '78.6%', value: fibonacci.level_786 },
                    { label: '100%', value: fibonacci.level_1 },
                  ].map((l) => (
                    <div key={l.label} className="flex justify-between text-sm">
                      <span className="text-gray-400">{l.label}</span>
                      <span className="text-white font-medium">{l.value?.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {pivots && (
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <h3 className="text-white font-semibold mb-3">Pivot Points</h3>
                <div className="space-y-1.5">
                  {[
                    { label: 'R3', value: pivots.r3, color: 'text-red-400' },
                    { label: 'R2', value: pivots.r2, color: 'text-red-300' },
                    { label: 'R1', value: pivots.r1, color: 'text-red-200' },
                    { label: 'Pivot', value: pivots.pivot, color: 'text-yellow-400' },
                    { label: 'S1', value: pivots.s1, color: 'text-green-200' },
                    { label: 'S2', value: pivots.s2, color: 'text-green-300' },
                    { label: 'S3', value: pivots.s3, color: 'text-green-400' },
                  ].map((p) => (
                    <div key={p.label} className="flex justify-between text-sm">
                      <span className={p.color}>{p.label}</span>
                      <span className="text-white font-medium">{p.value?.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function IndicatorCard({ label, value, color = 'text-white', suffix = '' }: {
  label: string;
  value?: number | string;
  color?: string;
  suffix?: string;
}) {
  return (
    <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
      <p className="text-gray-400 text-xs mb-1">{label}</p>
      <p className={`text-lg font-bold ${color}`}>
        {typeof value === 'number' ? value.toFixed(2) : value ?? 'N/A'}{suffix}
      </p>
    </div>
  );
}
