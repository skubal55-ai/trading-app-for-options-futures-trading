import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Activity, Search } from 'lucide-react';

interface OptionEntry {
  strike_price: number;
  expiry: string;
  call_oi: number;
  call_change_oi: number;
  call_ltp: number;
  call_volume: number;
  call_iv: number | null;
  put_oi: number;
  put_change_oi: number;
  put_ltp: number;
  put_volume: number;
  put_iv: number | null;
}

export default function OptionsChain() {
  const [symbol, setSymbol] = useState('NIFTY');
  const [searchInput, setSearchInput] = useState('NIFTY');
  const [data, setData] = useState<OptionEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadChain();
  }, [symbol]);

  const loadChain = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.getOptionChain(symbol);
      if (res.error) {
        setError(res.error);
        setData([]);
      } else {
        setData(res.data || []);
      }
    } catch (err) {
      setError('Failed to load option chain');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    if (searchInput.trim()) {
      setSymbol(searchInput.trim().toUpperCase());
    }
  };

  const maxOI = Math.max(
    ...data.map((d) => Math.max(d.call_oi, d.put_oi, 1))
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4 flex-wrap">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Activity size={24} />
          Options Chain
        </h2>
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {['NIFTY', 'BANKNIFTY', 'RELIANCE', 'TCS', 'INFY'].map((s) => (
              <button
                key={s}
                onClick={() => { setSymbol(s); setSearchInput(s); }}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  symbol === s ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              className="bg-gray-800 border border-gray-700 rounded-lg pl-8 pr-3 py-1.5 text-white text-sm focus:outline-none focus:border-blue-500 w-32"
              placeholder="Symbol"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <p className="text-red-400">{error}</p>
          <p className="text-gray-500 text-sm mt-2">Option chain data may not be available for this symbol</p>
        </div>
      ) : data.length > 0 ? (
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="p-3 border-b border-gray-700 bg-gray-900/50">
            <p className="text-gray-400 text-sm">Expiry: <span className="text-white">{data[0]?.expiry}</span></p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th colSpan={5} className="p-2 text-center text-green-400 font-medium bg-green-900/10 border-r border-gray-700">CALLS</th>
                  <th className="p-2 text-center text-yellow-400 font-medium bg-yellow-900/10">STRIKE</th>
                  <th colSpan={5} className="p-2 text-center text-red-400 font-medium bg-red-900/10 border-l border-gray-700">PUTS</th>
                </tr>
                <tr className="border-b border-gray-700 text-xs text-gray-400">
                  <th className="p-2 text-right">OI</th>
                  <th className="p-2 text-right">Volume</th>
                  <th className="p-2 text-right">IV%</th>
                  <th className="p-2 text-right">LTP</th>
                  <th className="p-2 border-r border-gray-700">
                    <div className="w-20" />
                  </th>
                  <th className="p-2 text-center font-bold text-yellow-400">Price</th>
                  <th className="p-2 border-l border-gray-700">
                    <div className="w-20" />
                  </th>
                  <th className="p-2 text-left">LTP</th>
                  <th className="p-2 text-left">IV%</th>
                  <th className="p-2 text-left">Volume</th>
                  <th className="p-2 text-left">OI</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row) => (
                  <tr key={row.strike_price} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                    <td className="p-2 text-right text-gray-300">{row.call_oi.toLocaleString()}</td>
                    <td className="p-2 text-right text-gray-300">{row.call_volume.toLocaleString()}</td>
                    <td className="p-2 text-right text-gray-300">{row.call_iv?.toFixed(1) ?? '-'}</td>
                    <td className="p-2 text-right text-green-400 font-medium">{row.call_ltp.toFixed(2)}</td>
                    <td className="p-2 border-r border-gray-700">
                      <div className="w-20 bg-gray-700 rounded-full h-1.5">
                        <div
                          className="bg-green-500 h-1.5 rounded-full"
                          style={{ width: `${(row.call_oi / maxOI) * 100}%` }}
                        />
                      </div>
                    </td>
                    <td className="p-2 text-center text-yellow-400 font-bold bg-yellow-900/5">{row.strike_price}</td>
                    <td className="p-2 border-l border-gray-700">
                      <div className="w-20 bg-gray-700 rounded-full h-1.5">
                        <div
                          className="bg-red-500 h-1.5 rounded-full"
                          style={{ width: `${(row.put_oi / maxOI) * 100}%` }}
                        />
                      </div>
                    </td>
                    <td className="p-2 text-left text-red-400 font-medium">{row.put_ltp.toFixed(2)}</td>
                    <td className="p-2 text-left text-gray-300">{row.put_iv?.toFixed(1) ?? '-'}</td>
                    <td className="p-2 text-left text-gray-300">{row.put_volume.toLocaleString()}</td>
                    <td className="p-2 text-left text-gray-300">{row.put_oi.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500">
          <Activity size={48} className="mx-auto mb-4 opacity-50" />
          <p>Select a symbol to view its option chain</p>
        </div>
      )}
    </div>
  );
}
