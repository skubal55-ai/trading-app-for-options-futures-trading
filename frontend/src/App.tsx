import { useState, useEffect } from 'react';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import Dashboard from './pages/Dashboard';
import Charts from './pages/Charts';
import Screener from './pages/Screener';
import OptionsChain from './pages/OptionsChain';
import Trading from './pages/Trading';
import Portfolio from './pages/Portfolio';
import Settings from './pages/Settings';
import Backtesting from './pages/Backtesting';
import { api } from './services/api';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [marketOpen, setMarketOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    api.getMarketStatus().then((res) => setMarketOpen(res.is_open)).catch(() => {});
    const interval = setInterval(() => {
      api.getMarketStatus().then((res) => setMarketOpen(res.is_open)).catch(() => {});
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => setRefreshKey((k) => k + 1);

  const renderPage = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard key={refreshKey} />;
      case 'charts': return <Charts key={refreshKey} />;
      case 'screener': return <Screener key={refreshKey} />;
      case 'options': return <OptionsChain key={refreshKey} />;
      case 'backtesting': return <Backtesting key={refreshKey} />;
      case 'trading': return <Trading key={refreshKey} />;
      case 'portfolio': return <Portfolio key={refreshKey} />;
      case 'settings': return <Settings />;
      default: return <Dashboard key={refreshKey} />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header marketStatus={marketOpen} onRefresh={handleRefresh} />
        <main className="flex-1 overflow-y-auto">
          {renderPage()}
        </main>
      </div>
    </div>
  );
}

export default App;
