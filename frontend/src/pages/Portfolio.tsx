import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Briefcase, TrendingUp, TrendingDown, DollarSign, BarChart3 } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';

interface PortfolioData {
  balance: number;
  initial_balance: number;
  total_pnl: number;
  total_pnl_percent: number;
  open_positions: number;
  closed_positions: number;
  winning_trades: number;
  losing_trades: number;
  invested_value?: number;
  available_balance?: number;
}

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
  status: string;
  timestamp: string;
}

export default function Portfolio() {
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [portRes, posRes] = await Promise.all([
        api.getPortfolio(),
        api.getPositions(),
      ]);
      setPortfolio(portRes);
      setPositions(posRes.positions || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  const winRate = portfolio
    ? portfolio.winning_trades + portfolio.losing_trades > 0
      ? ((portfolio.winning_trades / (portfolio.winning_trades + portfolio.losing_trades)) * 100).toFixed(1)
      : '0.0'
    : '0.0';

  const pieData = [
    { name: 'Available', value: portfolio?.available_balance ?? portfolio?.balance ?? 0, color: '#3b82f6' },
    { name: 'Invested', value: portfolio?.invested_value ?? 0, color: '#f59e0b' },
  ];

  const tradeData = [
    { name: 'Winning', value: portfolio?.winning_trades ?? 0, fill: '#10b981' },
    { name: 'Losing', value: portfolio?.losing_trades ?? 0, fill: '#ef4444' },
  ];

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold text-white flex items-center gap-2">
        <Briefcase size={24} />
        Portfolio (Paper Trading)
      </h2>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Balance"
          value={`${(portfolio?.balance ?? 0).toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}`}
          icon={<DollarSign size={18} className="text-blue-400" />}
        />
        <StatCard
          label="Total P&L"
          value={`${(portfolio?.total_pnl ?? 0) >= 0 ? '+' : ''}${(portfolio?.total_pnl ?? 0).toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}`}
          icon={(portfolio?.total_pnl ?? 0) >= 0
            ? <TrendingUp size={18} className="text-green-400" />
            : <TrendingDown size={18} className="text-red-400" />}
          valueColor={(portfolio?.total_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}
          sub={`${(portfolio?.total_pnl_percent ?? 0).toFixed(2)}%`}
        />
        <StatCard
          label="Win Rate"
          value={`${winRate}%`}
          icon={<BarChart3 size={18} className="text-yellow-400" />}
          sub={`${portfolio?.winning_trades ?? 0}W / ${portfolio?.losing_trades ?? 0}L`}
        />
        <StatCard
          label="Positions"
          value={`${portfolio?.open_positions ?? 0} Open`}
          icon={<Briefcase size={18} className="text-purple-400" />}
          sub={`${portfolio?.closed_positions ?? 0} Closed`}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <h3 className="text-white font-semibold mb-4">Capital Allocation</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} dataKey="value" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}>
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => value.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <h3 className="text-white font-semibold mb-4">Trade Performance</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={tradeData}>
              <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="value" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* All Positions */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-white font-semibold">All Positions</h3>
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
                <th className="text-center p-3">Status</th>
                <th className="text-left p-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.id} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                  <td className="p-3 text-white font-medium">{p.symbol}</td>
                  <td className={`p-3 ${p.trade_type === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{p.trade_type}</td>
                  <td className="p-3 text-right text-gray-300">{p.quantity}</td>
                  <td className="p-3 text-right text-gray-300">{p.entry_price.toFixed(2)}</td>
                  <td className="p-3 text-right text-white">{p.current_price.toFixed(2)}</td>
                  <td className={`p-3 text-right font-medium ${p.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {p.pnl >= 0 ? '+' : ''}{p.pnl.toFixed(2)}
                  </td>
                  <td className="p-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      p.status === 'OPEN' ? 'bg-blue-900/50 text-blue-400'
                        : p.status === 'TARGET_HIT' ? 'bg-green-900/50 text-green-400'
                        : p.status === 'SL_HIT' ? 'bg-red-900/50 text-red-400'
                        : 'bg-gray-700 text-gray-400'
                    }`}>{p.status}</span>
                  </td>
                  <td className="p-3 text-gray-500 text-xs">{new Date(p.timestamp).toLocaleDateString()}</td>
                </tr>
              ))}
              {positions.length === 0 && (
                <tr><td colSpan={8} className="p-6 text-center text-gray-500">No positions yet. Start trading!</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, valueColor = 'text-white', sub }: {
  label: string;
  value: string;
  icon: React.ReactNode;
  valueColor?: string;
  sub?: string;
}) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <p className="text-gray-400 text-xs">{label}</p>
      </div>
      <p className={`text-lg font-bold ${valueColor}`}>{value}</p>
      {sub && <p className="text-gray-500 text-xs mt-1">{sub}</p>}
    </div>
  );
}
