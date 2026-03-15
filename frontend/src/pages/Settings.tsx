import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Settings as SettingsIcon, Save, Zap, Clock, Shield } from 'lucide-react';

interface AutoTradeConfig {
  enabled: boolean;
  mode: string;
  strategies: string[];
  max_trades_per_day: number;
  max_capital_per_trade: number;
  stop_loss_percent: number;
  target_percent: number;
  segments: string[];
  trading_start_time: string;
  trading_end_time: string;
}

const ALL_STRATEGIES = [
  { id: 'MA_CROSSOVER', name: 'Moving Average Crossover' },
  { id: 'RSI_DIVERGENCE', name: 'RSI Divergence' },
  { id: 'MACD_SIGNAL', name: 'MACD Signal' },
  { id: 'FIBONACCI_RETRACEMENT', name: 'Fibonacci Retracement' },
  { id: 'BOLLINGER_BREAKOUT', name: 'Bollinger Breakout' },
  { id: 'SUPERTREND', name: 'Supertrend' },
  { id: 'VWAP_STRATEGY', name: 'VWAP Strategy' },
];

const ALL_SEGMENTS = [
  { id: 'EQUITY', name: 'Equity' },
  { id: 'OPTIONS', name: 'Options' },
  { id: 'FUTURES', name: 'Futures' },
];

export default function Settings() {
  const [config, setConfig] = useState<AutoTradeConfig>({
    enabled: false,
    mode: 'PAPER',
    strategies: [],
    max_trades_per_day: 5,
    max_capital_per_trade: 10000,
    stop_loss_percent: 2.0,
    target_percent: 4.0,
    segments: ['EQUITY'],
    trading_start_time: '09:15',
    trading_end_time: '15:15',
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [brokerApi, setBrokerApi] = useState('');
  const [brokerSecret, setBrokerSecret] = useState('');
  const [broker, setBroker] = useState('zerodha');

  useEffect(() => {
    api.getAutoTradeSettings().then(setConfig).catch(console.error);
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      await api.updateAutoTradeSettings(config as unknown as Record<string, unknown>);
      setMessage('Settings saved successfully!');
    } catch (err) {
      setMessage('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const toggleStrategy = (id: string) => {
    setConfig((prev) => ({
      ...prev,
      strategies: prev.strategies.includes(id)
        ? prev.strategies.filter((s) => s !== id)
        : [...prev.strategies, id],
    }));
  };

  const toggleSegment = (id: string) => {
    setConfig((prev) => ({
      ...prev,
      segments: prev.segments.includes(id)
        ? prev.segments.filter((s) => s !== id)
        : [...prev.segments, id],
    }));
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <h2 className="text-2xl font-bold text-white flex items-center gap-2">
        <SettingsIcon size={24} />
        Settings
      </h2>

      {/* Auto Trading */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Zap size={20} className="text-yellow-400" />
            <div>
              <h3 className="text-white font-semibold">Automated Trading</h3>
              <p className="text-gray-400 text-xs">Auto-execute trades based on strategy signals</p>
            </div>
          </div>
          <button
            onClick={() => setConfig((p) => ({ ...p, enabled: !p.enabled }))}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              config.enabled ? 'bg-green-600' : 'bg-gray-600'
            }`}
          >
            <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
              config.enabled ? 'left-6' : 'left-0.5'
            }`} />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-gray-400 text-xs block mb-1">Trading Mode</label>
            <select
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={config.mode}
              onChange={(e) => setConfig((p) => ({ ...p, mode: e.target.value }))}
            >
              <option value="PAPER">Paper Trading</option>
              <option value="LIVE">Live Trading</option>
            </select>
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Max Trades Per Day</label>
            <input
              type="number"
              min={1}
              max={50}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={config.max_trades_per_day}
              onChange={(e) => setConfig((p) => ({ ...p, max_trades_per_day: Number(e.target.value) }))}
            />
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Max Capital Per Trade (INR)</label>
            <input
              type="number"
              min={1000}
              step={1000}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={config.max_capital_per_trade}
              onChange={(e) => setConfig((p) => ({ ...p, max_capital_per_trade: Number(e.target.value) }))}
            />
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Stop Loss %</label>
            <input
              type="number"
              min={0.5}
              max={10}
              step={0.5}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={config.stop_loss_percent}
              onChange={(e) => setConfig((p) => ({ ...p, stop_loss_percent: Number(e.target.value) }))}
            />
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Target %</label>
            <input
              type="number"
              min={1}
              max={20}
              step={0.5}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={config.target_percent}
              onChange={(e) => setConfig((p) => ({ ...p, target_percent: Number(e.target.value) }))}
            />
          </div>
        </div>

        {/* Trading Hours */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Clock size={16} className="text-blue-400" />
            <label className="text-gray-400 text-sm">Trading Hours</label>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="time"
              className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={config.trading_start_time}
              onChange={(e) => setConfig((p) => ({ ...p, trading_start_time: e.target.value }))}
            />
            <span className="text-gray-400">to</span>
            <input
              type="time"
              className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={config.trading_end_time}
              onChange={(e) => setConfig((p) => ({ ...p, trading_end_time: e.target.value }))}
            />
          </div>
        </div>

        {/* Strategies Selection */}
        <div>
          <label className="text-gray-400 text-sm block mb-2">Active Strategies</label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {ALL_STRATEGIES.map((s) => (
              <button
                key={s.id}
                onClick={() => toggleStrategy(s.id)}
                className={`text-left px-3 py-2 rounded-lg text-sm transition-all border ${
                  config.strategies.includes(s.id)
                    ? 'bg-blue-900/50 border-blue-500 text-white'
                    : 'bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600'
                }`}
              >
                {s.name}
              </button>
            ))}
          </div>
        </div>

        {/* Segments */}
        <div>
          <label className="text-gray-400 text-sm block mb-2">Trading Segments</label>
          <div className="flex gap-2">
            {ALL_SEGMENTS.map((s) => (
              <button
                key={s.id}
                onClick={() => toggleSegment(s.id)}
                className={`px-4 py-2 rounded-lg text-sm transition-all border ${
                  config.segments.includes(s.id)
                    ? 'bg-green-900/50 border-green-500 text-white'
                    : 'bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600'
                }`}
              >
                {s.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Broker Integration */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 space-y-4">
        <div className="flex items-center gap-3">
          <Shield size={20} className="text-green-400" />
          <div>
            <h3 className="text-white font-semibold">Broker Integration (Live Trading)</h3>
            <p className="text-gray-400 text-xs">Connect your broker for live order execution</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-gray-400 text-xs block mb-1">Broker</label>
            <select
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={broker}
              onChange={(e) => setBroker(e.target.value)}
            >
              <option value="zerodha">Zerodha (Kite)</option>
              <option value="angelone">Angel One</option>
              <option value="upstox">Upstox</option>
              <option value="fyers">Fyers</option>
              <option value="5paisa">5Paisa</option>
            </select>
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">API Key</label>
            <input
              type="password"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              placeholder="Enter API Key"
              value={brokerApi}
              onChange={(e) => setBrokerApi(e.target.value)}
            />
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">API Secret</label>
            <input
              type="password"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              placeholder="Enter API Secret"
              value={brokerSecret}
              onChange={(e) => setBrokerSecret(e.target.value)}
            />
          </div>
        </div>
        <p className="text-gray-500 text-xs">
          Broker API credentials are stored locally and never sent to our servers. Required for live trading only.
        </p>
      </div>

      {/* Save Button */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
        >
          <Save size={16} />
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
        {message && (
          <p className={`text-sm ${message.includes('success') ? 'text-green-400' : 'text-red-400'}`}>
            {message}
          </p>
        )}
      </div>
    </div>
  );
}
