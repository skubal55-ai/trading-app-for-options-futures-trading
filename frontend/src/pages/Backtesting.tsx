import { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  TrendingUp, TrendingDown, Target, ShieldAlert, Clock,
  BarChart3, DollarSign, Percent, Award, AlertTriangle, Play, Filter,
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts';

interface BacktestTrade {
  symbol: string;
  entry_date: string;
  exit_date: string;
  signal: string;
  strategy: string;
  entry_price: number;
  exit_price: number;
  target: number;
  stop_loss: number;
  pnl: number;
  pnl_percent: number;
  exit_reason: string;
  risk_reward: number;
  confidence: number;
  reason: string;
  quantity: number;
  absolute_pnl: number;
  max_favorable_excursion: number;
  max_adverse_excursion: number;
}

interface BacktestStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl_percent: number;
  avg_pnl_percent: number;
  avg_winner: number;
  avg_loser: number;
  max_winner: number;
  max_loser: number;
  profit_factor: number;
  expectancy: number;
  sharpe_estimate: number;
  max_drawdown: number;
  target_hit_rate: number;
  stop_loss_hit_rate: number;
  avg_holding_days: number;
}

interface SymbolSummary {
  symbol: string;
  trades: number;
  win_rate: number;
  total_pnl_pct: number;
  absolute_pnl: number;
}

interface EquityPoint {
  date: string;
  equity: number;
  cumulative_pnl: number;
  symbol: string;
}

interface BacktestStrategy {
  id: string;
  name: string;
  type: string;
}

interface BacktestResult {
  strategy: string;
  period: string;
  holding_days: number;
  capital: number;
  total_symbols_scanned: number;
  stats: BacktestStats;
  trades: BacktestTrade[];
  top_winners: BacktestTrade[];
  portfolio_equity: EquityPoint[];
  symbol_summary: SymbolSummary[];
}

export default function Backtesting() {
  const [strategies, setStrategies] = useState<BacktestStrategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState('MA_CROSSOVER');
  const [period, setPeriod] = useState('1y');
  const [holdingDays, setHoldingDays] = useState(10);
  const [capital, setCapital] = useState(100000);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'trades' | 'winners' | 'symbols'>('overview');
  const [signalFilter, setSignalFilter] = useState<string>('');

  useEffect(() => {
    api.getBacktestStrategies().then((res) => setStrategies(res.strategies)).catch(console.error);
  }, []);

  const runBacktest = async () => {
    setLoading(true);
    try {
      const res = await api.runBacktest(selectedStrategy, period, holdingDays, capital);
      setResult(res);
      setActiveTab('overview');
    } catch (err) {
      console.error('Backtest error:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredTrades = result?.trades.filter(t => {
    if (signalFilter && t.signal !== signalFilter) return false;
    return true;
  }) ?? [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <BarChart3 size={24} />
          Strategy Backtesting
        </h2>
      </div>

      {/* Controls */}
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
          <div>
            <label className="text-gray-400 text-xs mb-1 block">Strategy</label>
            <select
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            >
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>{s.name} ({s.type})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-gray-400 text-xs mb-1 block">Period</label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="6mo">6 Months</option>
              <option value="1y">1 Year</option>
              <option value="2y">2 Years</option>
            </select>
          </div>
          <div>
            <label className="text-gray-400 text-xs mb-1 block">Holding Days</label>
            <input
              type="number"
              value={holdingDays}
              onChange={(e) => setHoldingDays(Number(e.target.value))}
              min={1}
              max={60}
              className="w-full bg-gray-900 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="text-gray-400 text-xs mb-1 block">Capital (INR)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              min={10000}
              step={10000}
              className="w-full bg-gray-900 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <button
            onClick={runBacktest}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            <Play size={16} />
            {loading ? 'Running...' : 'Run Backtest'}
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-40">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2" />
            <p className="text-gray-400 text-sm">Running backtest on NIFTY 50 stocks...</p>
            <p className="text-gray-500 text-xs mt-1">This may take 30-60 seconds</p>
          </div>
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <>
          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
            <StatCard
              label="Total Trades"
              value={result.stats.total_trades.toString()}
              icon={<BarChart3 size={14} className="text-blue-400" />}
            />
            <StatCard
              label="Win Rate"
              value={`${result.stats.win_rate}%`}
              icon={<Award size={14} className={result.stats.win_rate >= 50 ? "text-green-400" : "text-red-400"} />}
              color={result.stats.win_rate >= 50 ? 'green' : 'red'}
            />
            <StatCard
              label="Total P&L"
              value={`${result.stats.total_pnl_percent >= 0 ? '+' : ''}${result.stats.total_pnl_percent}%`}
              icon={<DollarSign size={14} className={result.stats.total_pnl_percent >= 0 ? "text-green-400" : "text-red-400"} />}
              color={result.stats.total_pnl_percent >= 0 ? 'green' : 'red'}
            />
            <StatCard
              label="Profit Factor"
              value={result.stats.profit_factor.toFixed(2)}
              icon={<TrendingUp size={14} className="text-blue-400" />}
              color={result.stats.profit_factor >= 1.5 ? 'green' : result.stats.profit_factor >= 1 ? 'yellow' : 'red'}
            />
            <StatCard
              label="Avg Winner"
              value={`+${result.stats.avg_winner}%`}
              icon={<TrendingUp size={14} className="text-green-400" />}
              color="green"
            />
            <StatCard
              label="Avg Loser"
              value={`${result.stats.avg_loser}%`}
              icon={<TrendingDown size={14} className="text-red-400" />}
              color="red"
            />
            <StatCard
              label="Max Drawdown"
              value={`${result.stats.max_drawdown}%`}
              icon={<AlertTriangle size={14} className="text-yellow-400" />}
              color="yellow"
            />
            <StatCard
              label="Avg Hold"
              value={`${result.stats.avg_holding_days}d`}
              icon={<Clock size={14} className="text-gray-400" />}
            />
          </div>

          {/* Secondary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <p className="text-gray-500 text-xs">Target Hit Rate</p>
              <p className="text-green-400 text-lg font-bold">{result.stats.target_hit_rate}%</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <p className="text-gray-500 text-xs">Stop Loss Hit Rate</p>
              <p className="text-red-400 text-lg font-bold">{result.stats.stop_loss_hit_rate}%</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <p className="text-gray-500 text-xs">Sharpe Ratio (est.)</p>
              <p className="text-blue-400 text-lg font-bold">{result.stats.sharpe_estimate}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <p className="text-gray-500 text-xs">Expectancy</p>
              <p className={`text-lg font-bold ${result.stats.expectancy >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {result.stats.expectancy}%
              </p>
            </div>
          </div>

          {/* Equity Curve */}
          {result.portfolio_equity.length > 0 && (
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <h3 className="text-white font-semibold mb-4">Portfolio Equity Curve (Starting: {'\u20B9'}{capital.toLocaleString('en-IN')})</h3>
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={result.portfolio_equity}>
                  <defs>
                    <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={result.stats.total_pnl_percent >= 0 ? "#22c55e" : "#ef4444"} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={result.stats.total_pnl_percent >= 0 ? "#22c55e" : "#ef4444"} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#9ca3af', fontSize: 10 }}
                    tickFormatter={(v) => v.slice(5, 10)}
                  />
                  <YAxis
                    domain={['auto', 'auto']}
                    tick={{ fill: '#9ca3af', fontSize: 10 }}
                    tickFormatter={(v) => `${'\u20B9'}${(v / 1000).toFixed(0)}K`}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                    labelStyle={{ color: '#9ca3af' }}
                    formatter={(value: number) => [`${'\u20B9'}${value.toLocaleString('en-IN')}`, 'Equity']}
                  />
                  <Area
                    type="monotone"
                    dataKey="equity"
                    stroke={result.stats.total_pnl_percent >= 0 ? "#22c55e" : "#ef4444"}
                    fill="url(#colorEquity)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Tabs */}
          <div className="flex gap-2 border-b border-gray-700 pb-2">
            {[
              { id: 'overview' as const, label: 'Top Winners' },
              { id: 'trades' as const, label: 'All Trades' },
              { id: 'symbols' as const, label: 'By Symbol' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Top Winners Tab */}
          {activeTab === 'overview' && result.top_winners.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-white font-semibold flex items-center gap-2">
                <Award size={18} className="text-yellow-400" />
                Top Profitable Trades (Would Have Returned Profits)
              </h3>
              <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700 bg-gray-900/50">
                        <th className="text-left p-3 text-gray-400 font-medium">Symbol</th>
                        <th className="text-left p-3 text-gray-400 font-medium">Signal</th>
                        <th className="text-left p-3 text-gray-400 font-medium">Entry Date</th>
                        <th className="text-left p-3 text-gray-400 font-medium">Exit Date</th>
                        <th className="text-right p-3 text-gray-400 font-medium">Entry</th>
                        <th className="text-right p-3 text-gray-400 font-medium">Exit</th>
                        <th className="text-right p-3 text-gray-400 font-medium">P&L %</th>
                        <th className="text-right p-3 text-gray-400 font-medium">P&L (INR)</th>
                        <th className="text-left p-3 text-gray-400 font-medium">Exit Reason</th>
                        <th className="text-left p-3 text-gray-400 font-medium">Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.top_winners.map((t, i) => (
                        <TradeRow key={`winner-${i}`} trade={t} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* All Trades Tab */}
          {activeTab === 'trades' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Filter size={16} className="text-gray-400" />
                <select
                  value={signalFilter}
                  onChange={(e) => setSignalFilter(e.target.value)}
                  className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">All Signals</option>
                  <option value="BUY">BUY Only</option>
                  <option value="SELL">SELL Only</option>
                </select>
                <span className="text-gray-500 text-sm">{filteredTrades.length} trades</span>
              </div>

              <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-gray-900">
                      <tr className="border-b border-gray-700">
                        <th className="text-left p-3 text-gray-400 font-medium">Symbol</th>
                        <th className="text-left p-3 text-gray-400 font-medium">Signal</th>
                        <th className="text-left p-3 text-gray-400 font-medium">Entry Date</th>
                        <th className="text-left p-3 text-gray-400 font-medium">Exit Date</th>
                        <th className="text-right p-3 text-gray-400 font-medium">Entry</th>
                        <th className="text-right p-3 text-gray-400 font-medium">Exit</th>
                        <th className="text-right p-3 text-gray-400 font-medium">P&L %</th>
                        <th className="text-right p-3 text-gray-400 font-medium">P&L (INR)</th>
                        <th className="text-left p-3 text-gray-400 font-medium">Exit Reason</th>
                        <th className="text-left p-3 text-gray-400 font-medium">Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredTrades.map((t, i) => (
                        <TradeRow key={`trade-${i}`} trade={t} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Symbol Summary Tab */}
          {activeTab === 'symbols' && (
            <div className="space-y-4">
              <h3 className="text-white font-semibold">Performance by Symbol</h3>

              {/* Symbol Bar Chart */}
              {result.symbol_summary.length > 0 && (
                <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={result.symbol_summary}>
                      <XAxis
                        dataKey="symbol"
                        tick={{ fill: '#9ca3af', fontSize: 10 }}
                        angle={-45}
                        textAnchor="end"
                        height={60}
                      />
                      <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                        labelStyle={{ color: '#9ca3af' }}
                        formatter={(value: number) => [`${value.toFixed(2)}%`, 'Total P&L']}
                      />
                      <Bar dataKey="total_pnl_pct" radius={[4, 4, 0, 0]}>
                        {result.symbol_summary.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={entry.total_pnl_pct >= 0 ? '#22c55e' : '#ef4444'}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700 bg-gray-900/50">
                        <th className="text-left p-3 text-gray-400 font-medium">Symbol</th>
                        <th className="text-right p-3 text-gray-400 font-medium">Trades</th>
                        <th className="text-right p-3 text-gray-400 font-medium">Win Rate</th>
                        <th className="text-right p-3 text-gray-400 font-medium">Total P&L %</th>
                        <th className="text-right p-3 text-gray-400 font-medium">Absolute P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.symbol_summary.map((s, i) => (
                        <tr key={`sym-${i}`} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                          <td className="p-3 text-white font-medium">{s.symbol}</td>
                          <td className="p-3 text-right text-gray-300">{s.trades}</td>
                          <td className="p-3 text-right">
                            <span className={s.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}>
                              {s.win_rate}%
                            </span>
                          </td>
                          <td className="p-3 text-right">
                            <span className={s.total_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
                              {s.total_pnl_pct >= 0 ? '+' : ''}{s.total_pnl_pct}%
                            </span>
                          </td>
                          <td className="p-3 text-right">
                            <span className={s.absolute_pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                              {'\u20B9'}{s.absolute_pnl.toLocaleString('en-IN')}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!result && !loading && (
        <div className="text-center py-16 text-gray-500">
          <BarChart3 size={64} className="mx-auto mb-4 opacity-40" />
          <p className="text-lg">Select a strategy and click "Run Backtest"</p>
          <p className="text-sm mt-2">Backtests historical performance on NIFTY 50 stocks with entry, exit, target, and stop-loss simulation</p>
        </div>
      )}
    </div>
  );
}


function TradeRow({ trade }: { trade: BacktestTrade }) {
  const isProfitable = trade.pnl >= 0;
  return (
    <tr className="border-b border-gray-700/50 hover:bg-gray-700/30">
      <td className="p-3 text-white font-medium">{trade.symbol}</td>
      <td className="p-3">
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold ${
          trade.signal === 'BUY'
            ? 'bg-green-900/50 text-green-400 border border-green-800'
            : 'bg-red-900/50 text-red-400 border border-red-800'
        }`}>
          {trade.signal === 'BUY' ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
          {trade.signal}
        </span>
      </td>
      <td className="p-3 text-gray-400 text-xs">{trade.entry_date.slice(0, 10)}</td>
      <td className="p-3 text-gray-400 text-xs">{trade.exit_date.slice(0, 10)}</td>
      <td className="p-3 text-right text-blue-400">{'\u20B9'}{trade.entry_price.toFixed(2)}</td>
      <td className="p-3 text-right text-white">{'\u20B9'}{trade.exit_price.toFixed(2)}</td>
      <td className="p-3 text-right">
        <span className={`font-medium ${isProfitable ? 'text-green-400' : 'text-red-400'}`}>
          {isProfitable ? '+' : ''}{trade.pnl_percent.toFixed(2)}%
        </span>
      </td>
      <td className="p-3 text-right">
        <span className={`font-medium ${isProfitable ? 'text-green-400' : 'text-red-400'}`}>
          {'\u20B9'}{trade.absolute_pnl.toLocaleString('en-IN')}
        </span>
      </td>
      <td className="p-3">
        <span className={`text-xs px-2 py-0.5 rounded ${
          trade.exit_reason === 'TARGET_HIT'
            ? 'bg-green-900/40 text-green-400'
            : trade.exit_reason === 'STOP_LOSS_HIT'
            ? 'bg-red-900/40 text-red-400'
            : 'bg-gray-700 text-gray-400'
        }`}>
          {trade.exit_reason === 'TARGET_HIT' ? (
            <span className="flex items-center gap-1"><Target size={10} /> Target</span>
          ) : trade.exit_reason === 'STOP_LOSS_HIT' ? (
            <span className="flex items-center gap-1"><ShieldAlert size={10} /> SL Hit</span>
          ) : (
            'Expired'
          )}
        </span>
      </td>
      <td className="p-3 text-gray-400 text-xs max-w-[200px] truncate" title={trade.reason}>{trade.reason}</td>
    </tr>
  );
}


function StatCard({ label, value, icon, color }: {
  label: string;
  value: string;
  icon: React.ReactNode;
  color?: 'green' | 'red' | 'yellow' | 'blue';
}) {
  const colorMap = {
    green: 'text-green-400',
    red: 'text-red-400',
    yellow: 'text-yellow-400',
    blue: 'text-blue-400',
  };
  const valueColor = color ? colorMap[color] : 'text-white';

  return (
    <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
      <div className="flex items-center gap-1 mb-1">
        {icon}
        <span className="text-gray-500 text-xs">{label}</span>
      </div>
      <p className={`text-lg font-bold ${valueColor}`}>{value}</p>
    </div>
  );
}
