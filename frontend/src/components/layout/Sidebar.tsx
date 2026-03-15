import { BarChart3, TrendingUp, Search, Briefcase, Settings, Activity, LayoutDashboard } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'charts', label: 'Charts', icon: BarChart3 },
  { id: 'screener', label: 'Screener', icon: Search },
  { id: 'options', label: 'Options Chain', icon: Activity },
  { id: 'trading', label: 'Trading', icon: TrendingUp },
  { id: 'portfolio', label: 'Portfolio', icon: Briefcase },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <div className="w-64 bg-gray-900 text-white flex flex-col h-full border-r border-gray-800">
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <TrendingUp className="text-green-400" size={24} />
          <span>Naksha</span>
        </h1>
        <p className="text-xs text-gray-400 mt-1">The Profitable Trading App</p>
      </div>
      <nav className="flex-1 p-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-1 transition-colors text-left ${
                activeTab === item.id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Icon size={18} />
              <span className="text-sm font-medium">{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="p-4 border-t border-gray-800">
        <div className="text-xs text-gray-500">
          <p>Market Hours: 9:15 AM - 3:30 PM IST</p>
          <p className="mt-1">Data powered by NSE India & Kite</p>
        </div>
      </div>
    </div>
  );
}
