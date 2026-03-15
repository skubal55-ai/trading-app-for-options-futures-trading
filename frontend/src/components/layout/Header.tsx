import { RefreshCw, Bell, Clock } from 'lucide-react';
import { useEffect, useState } from 'react';

interface HeaderProps {
  marketStatus: boolean;
  onRefresh: () => void;
}

export default function Header({ marketStatus, onRefresh }: HeaderProps) {
  const [time, setTime] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const ist = new Date(now.getTime() + (5.5 * 60 * 60 * 1000));
      setTime(ist.toLocaleTimeString('en-IN', { hour12: true }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium ${
          marketStatus ? 'bg-green-900/50 text-green-400 border border-green-800' : 'bg-red-900/50 text-red-400 border border-red-800'
        }`}>
          <div className={`w-2 h-2 rounded-full ${marketStatus ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
          {marketStatus ? 'Market Open' : 'Market Closed'}
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <Clock size={14} />
          <span>{time} IST</span>
        </div>
        <button
          onClick={onRefresh}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          title="Refresh Data"
        >
          <RefreshCw size={16} />
        </button>
        <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors relative">
          <Bell size={16} />
        </button>
      </div>
    </header>
  );
}
