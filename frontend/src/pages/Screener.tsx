import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Search, Filter, Target, ShieldAlert, TrendingUp, TrendingDown, Zap } from 'lucide-react';

interface ScreenerResult {
  symbol: string;
  name: string;
  ltp: number;
  signal: string;
  strategy: string;
  entry_price: number;
  target: number;
  stop_loss: number;
  risk_reward: number;
  confidence: number;
  segment: string;
  reason: string;
}

interface Strategy {
  id: string;
  name: string;
  description: string;
  type: string;
}

export default function Screener() {
  const [results, setResults] = useState<ScreenerResult[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');
  const [signalFilter, setSignalFilter] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getStrategies().then((res) => setStrategies(res.strategies)).catch(console.error);
  }, []);

  const runScan = async () => {
    setLoading(true);
    try {
      const res = await api.scanStocks(
        selectedStrategy || undefined,
        signalFilter || undefined,
        20
      );
      setResults(res.results || []);
    } catch (err) {
      console.error('Scan error:', err);
    } finally {
      setLoading(false);
    }
  };

  const quickScan = async (strategyId: string) => {
    setLoading(true);
    setSelectedStrategy(strategyId);
    try {
      const res = await api.quickScan(strategyId, 10);
      setResults(res.results || []);
    } catch (err) {
      console.error('Quick scan error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Search size={24} />
          Stock & Options Screener
        </h2>
        <button
          onClick={runScan}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
        >
          <Zap size={16} />
          {loading ? 'Scanning...' : 'Run Full Scan'}
        </button>
      </div>

      {/* Strategy Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {strategies.map((s) => (
          <button
            key={s.id}
            onClick={() => quickScan(s.id)}
            className={`text-left p-3 rounded-lg border transition-all ${
              selectedStrategy === s.id
                ? 'bg-blue-900/50 border-blue-500'
                : 'bg-gray-800 border-gray-700 hover:border-gray-600'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <h4 className="text-white text-sm font-medium">{s.name}</h4>
              <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">{s.type}</span>
            </div>
            <p className="text-gray-400 text-xs">{s.description}</p>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <Filter size={16} className="text-gray-400" />
        <select
          value={selectedStrategy}
          onChange={(e) => setSelectedStrategy(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Strategies</option>
          {strategies.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <select
          value={signalFilter}
          onChange={(e) => setSignalFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Signals</option>
          <option value="BUY">BUY Only</option>
          <option value="SELL">SELL Only</option>
        </select>
      </div>

      {/* Results Table */}
      {loading ? (
        <div className="flex items-center justify-center h-40">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2" />
            <p className="text-gray-400 text-sm">Scanning NIFTY 50 stocks across strategies...</p>
          </div>
        </div>
      ) : results.length > 0 ? (
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 bg-gray-900/50">
                  <th className="text-left p-3 text-gray-400 font-medium">Symbol</th>
                  <th className="text-left p-3 text-gray-400 font-medium">Signal</th>
                  <th className="text-left p-3 text-gray-400 font-medium">Strategy</th>
                  <th className="text-right p-3 text-gray-400 font-medium">LTP</th>
                  <th className="text-right p-3 text-gray-400 font-medium">Entry</th>
                  <th className="text-right p-3 text-gray-400 font-medium">Target</th>
                  <th className="text-right p-3 text-gray-400 font-medium">Stop Loss</th>
                  <th className="text-right p-3 text-gray-400 font-medium">R:R</th>
                  <th className="text-right p-3 text-gray-400 font-medium">Confidence</th>
                  <th className="text-left p-3 text-gray-400 font-medium">Reason</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={`${r.symbol}-${r.strategy}-${i}`} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                    <td className="p-3">
                      <p className="text-white font-medium">{r.symbol}</p>
                      <p className="text-gray-500 text-xs">{r.name?.slice(0, 20)}</p>
                    </td>
                    <td className="p-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-bold ${
                        r.signal === 'BUY'
                          ? 'bg-green-900/50 text-green-400 border border-green-800'
                          : 'bg-red-900/50 text-red-400 border border-red-800'
                      }`}>
                        {r.signal === 'BUY' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                        {r.signal}
                      </span>
                    </td>
                    <td className="p-3 text-gray-300 text-xs">{r.strategy.replace('_', ' ')}</td>
                    <td className="p-3 text-right text-white">{r.ltp.toFixed(2)}</td>
                    <td className="p-3 text-right text-blue-400">{r.entry_price.toFixed(2)}</td>
                    <td className="p-3 text-right">
                      <span className="flex items-center justify-end gap-1 text-green-400">
                        <Target size={12} />
                        {r.target.toFixed(2)}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <span className="flex items-center justify-end gap-1 text-red-400">
                        <ShieldAlert size={12} />
                        {r.stop_loss.toFixed(2)}
                      </span>
                    </td>
                    <td className="p-3 text-right text-yellow-400 font-medium">1:{r.risk_reward}</td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 bg-gray-700 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${
                              r.confidence >= 0.75 ? 'bg-green-500' : r.confidence >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${r.confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-gray-300 text-xs">{(r.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="p-3 text-gray-400 text-xs max-w-xs truncate">{r.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500">
          <Search size={48} className="mx-auto mb-4 opacity-50" />
          <p>Click "Run Full Scan" or select a strategy to scan NIFTY 50 stocks</p>
        </div>
      )}
    </div>
  );
}
