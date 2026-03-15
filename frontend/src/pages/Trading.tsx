import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { ShoppingCart } from 'lucide-react';

interface Position {
  id: string;
  symbol: string;
  trade_type: string;
  entry_price: number;
  current_price: number;
  quantity: number;
  pnl: number;
  pnl_percent: number;
  stop_loss: number | null;
  target: number | null;
  segment: string;
  mode: string;
  status: string;
  timestamp: string;
}

interface Order {
  id: string;
  symbol: string;
  trade_type: string;
  order_type: string;
  quantity: number;
  price: number;
  status: string;
  timestamp: string;
}

export default function Trading() {
  const [mode, setMode] = useState<'PAPER' | 'LIVE'>('PAPER');
  const [positions, setPositions] = useState<Position[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);

  // Order form
  const [symbol, setSymbol] = useState('');
  const [tradeType, setTradeType] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType] = useState('MARKET');
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState(0);
  const [stopLoss, setStopLoss] = useState<number | undefined>();
  const [target, setTarget] = useState<number | undefined>();
  const [segment, setSegment] = useState('EQUITY');
  const [orderMessage, setOrderMessage] = useState('');
  const [fetchingPrice, setFetchingPrice] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [posRes, ordRes] = await Promise.all([
        api.getPositions(),
        api.getOrders(),
      ]);
      setPositions(posRes.positions || []);
      setOrders(ordRes.orders || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchPrice = async () => {
    if (!symbol) return;
    setFetchingPrice(true);
    try {
      const quote = await api.getQuote(symbol.toUpperCase());
      if (quote.ltp) {
        setPrice(quote.ltp);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setFetchingPrice(false);
    }
  };

  const placeOrder = async () => {
    if (!symbol || !price || !quantity) {
      setOrderMessage('Please fill all required fields');
      return;
    }
    setLoading(true);
    setOrderMessage('');
    try {
      const result = await api.placeOrder({
        symbol: symbol.toUpperCase(),
        trade_type: tradeType,
        order_type: orderType,
        quantity,
        price,
        stop_loss: stopLoss,
        target,
        segment,
        mode,
      });
      if (result.error) {
        setOrderMessage(`Error: ${result.error}`);
      } else {
        setOrderMessage(`Order ${result.status}: ${tradeType} ${quantity} ${symbol.toUpperCase()} @ ${price}`);
        loadData();
        setSymbol('');
        setPrice(0);
        setQuantity(1);
        setStopLoss(undefined);
        setTarget(undefined);
      }
    } catch (err) {
      setOrderMessage('Order failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const resetPaper = async () => {
    if (confirm('Reset paper trading? All positions and orders will be cleared.')) {
      await api.resetPaperTrading();
      loadData();
      setOrderMessage('Paper trading account reset');
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <ShoppingCart size={24} />
          Trading Terminal
        </h2>
        <div className="flex items-center gap-2">
          <div className="bg-gray-800 rounded-lg p-1 flex">
            <button
              onClick={() => setMode('PAPER')}
              className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                mode === 'PAPER' ? 'bg-yellow-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Paper Trade
            </button>
            <button
              onClick={() => setMode('LIVE')}
              className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                mode === 'LIVE' ? 'bg-green-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Live Trade
            </button>
          </div>
          {mode === 'PAPER' && (
            <button onClick={resetPaper} className="text-xs text-red-400 hover:text-red-300 px-2">
              Reset Account
            </button>
          )}
        </div>
      </div>

      {mode === 'LIVE' && (
        <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-3 text-yellow-300 text-sm">
          Live trading requires broker API integration (Zerodha/Angel One/Upstox). Configure in Settings.
        </div>
      )}

      {/* Order Form */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 className="text-white font-semibold mb-4">Place Order ({mode})</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="text-gray-400 text-xs block mb-1">Symbol</label>
            <div className="flex gap-1">
              <input
                className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                placeholder="e.g. RELIANCE"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              />
              <button onClick={fetchPrice} disabled={fetchingPrice} className="bg-gray-700 hover:bg-gray-600 text-white px-2 py-2 rounded-lg text-xs">
                {fetchingPrice ? '...' : 'Get'}
              </button>
            </div>
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Type</label>
            <div className="flex gap-1">
              <button
                onClick={() => setTradeType('BUY')}
                className={`flex-1 py-2 rounded-lg text-sm font-medium ${
                  tradeType === 'BUY' ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-400'
                }`}
              >
                BUY
              </button>
              <button
                onClick={() => setTradeType('SELL')}
                className={`flex-1 py-2 rounded-lg text-sm font-medium ${
                  tradeType === 'SELL' ? 'bg-red-600 text-white' : 'bg-gray-700 text-gray-400'
                }`}
              >
                SELL
              </button>
            </div>
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Quantity</label>
            <input
              type="number"
              min={1}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
            />
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Price</label>
            <input
              type="number"
              step={0.05}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={price || ''}
              onChange={(e) => setPrice(Number(e.target.value))}
            />
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Segment</label>
            <select
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={segment}
              onChange={(e) => setSegment(e.target.value)}
            >
              <option value="EQUITY">Equity</option>
              <option value="OPTIONS">Options</option>
              <option value="FUTURES">Futures</option>
            </select>
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Stop Loss</label>
            <input
              type="number"
              step={0.05}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={stopLoss || ''}
              onChange={(e) => setStopLoss(Number(e.target.value) || undefined)}
              placeholder="Optional"
            />
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Target</label>
            <input
              type="number"
              step={0.05}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={target || ''}
              onChange={(e) => setTarget(Number(e.target.value) || undefined)}
              placeholder="Optional"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={placeOrder}
              disabled={loading}
              className={`w-full py-2 rounded-lg text-sm font-bold transition-colors ${
                tradeType === 'BUY'
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-red-600 hover:bg-red-700 text-white'
              } disabled:opacity-50`}
            >
              {loading ? 'Placing...' : `${tradeType} ${symbol || 'Stock'}`}
            </button>
          </div>
        </div>
        {orderMessage && (
          <p className={`mt-3 text-sm ${orderMessage.startsWith('Error') ? 'text-red-400' : 'text-green-400'}`}>
            {orderMessage}
          </p>
        )}
      </div>

      {/* Open Positions */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-white font-semibold">Open Positions</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-gray-400 text-xs">
                <th className="text-left p-3">Symbol</th>
                <th className="text-left p-3">Type</th>
                <th className="text-right p-3">Qty</th>
                <th className="text-right p-3">Entry</th>
                <th className="text-right p-3">Current</th>
                <th className="text-right p-3">P&L</th>
                <th className="text-right p-3">SL</th>
                <th className="text-right p-3">Target</th>
                <th className="text-center p-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {positions.filter(p => p.status === 'OPEN').map((p) => (
                <tr key={p.id} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                  <td className="p-3 text-white font-medium">{p.symbol}</td>
                  <td className="p-3">
                    <span className={p.trade_type === 'BUY' ? 'text-green-400' : 'text-red-400'}>
                      {p.trade_type}
                    </span>
                  </td>
                  <td className="p-3 text-right text-gray-300">{p.quantity}</td>
                  <td className="p-3 text-right text-gray-300">{p.entry_price.toFixed(2)}</td>
                  <td className="p-3 text-right text-white">{p.current_price.toFixed(2)}</td>
                  <td className={`p-3 text-right font-medium ${p.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {p.pnl >= 0 ? '+' : ''}{p.pnl.toFixed(2)} ({p.pnl_percent.toFixed(2)}%)
                  </td>
                  <td className="p-3 text-right text-red-300">{p.stop_loss?.toFixed(2) ?? '-'}</td>
                  <td className="p-3 text-right text-green-300">{p.target?.toFixed(2) ?? '-'}</td>
                  <td className="p-3 text-center">
                    <span className="px-2 py-0.5 rounded text-xs bg-blue-900/50 text-blue-400">{p.status}</span>
                  </td>
                </tr>
              ))}
              {positions.filter(p => p.status === 'OPEN').length === 0 && (
                <tr>
                  <td colSpan={9} className="p-6 text-center text-gray-500">No open positions</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Order History */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-white font-semibold">Order History</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-gray-400 text-xs">
                <th className="text-left p-3">ID</th>
                <th className="text-left p-3">Symbol</th>
                <th className="text-left p-3">Type</th>
                <th className="text-right p-3">Qty</th>
                <th className="text-right p-3">Price</th>
                <th className="text-center p-3">Status</th>
                <th className="text-left p-3">Time</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                  <td className="p-3 text-gray-500 text-xs">{o.id}</td>
                  <td className="p-3 text-white">{o.symbol}</td>
                  <td className={`p-3 ${o.trade_type === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{o.trade_type}</td>
                  <td className="p-3 text-right text-gray-300">{o.quantity}</td>
                  <td className="p-3 text-right text-gray-300">{o.price.toFixed(2)}</td>
                  <td className="p-3 text-center">
                    <span className="px-2 py-0.5 rounded text-xs bg-green-900/50 text-green-400">{o.status}</span>
                  </td>
                  <td className="p-3 text-gray-500 text-xs">{new Date(o.timestamp).toLocaleString()}</td>
                </tr>
              ))}
              {orders.length === 0 && (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-gray-500">No orders placed yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
