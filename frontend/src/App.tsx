import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect, createContext, useContext } from 'react'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Trading from './pages/Trading'
import Strategy from './pages/Strategy'
import Risk from './pages/Risk'
import Models from './pages/Models'
import Logs from './pages/Logs'
import Settings from './pages/Settings'
import Onboarding from './pages/Onboarding'

// App Context
interface AppContextType {
  isConnected: boolean;
  setIsConnected: (v: boolean) => void;
  isPaperTrading: boolean;
  setIsPaperTrading: (v: boolean) => void;
  isAgentRunning: boolean;
  setIsAgentRunning: (v: boolean) => void;
  showCommandPalette: boolean;
  setShowCommandPalette: (v: boolean) => void;
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
}

export const AppContext = createContext<AppContextType | null>(null);

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
}

function App() {
  const [isOnboarded, setIsOnboarded] = useState(() => {
    return localStorage.getItem('vertex_onboarded') === 'true';
  });
  const [isConnected, setIsConnected] = useState(false);
  const [isPaperTrading, setIsPaperTrading] = useState(true);
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = (toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { ...toast, id }]);
    setTimeout(() => removeToast(id), 4000);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowCommandPalette(prev => !prev);
      }
      if (e.key === 'Escape') {
        setShowCommandPalette(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleOnboardingComplete = () => {
    localStorage.setItem('vertex_onboarded', 'true');
    setIsOnboarded(true);
    setIsConnected(true);
    addToast({ type: 'success', message: 'Connected to Binance Testnet' });
  };

  if (!isOnboarded) {
    return <Onboarding onComplete={handleOnboardingComplete} />;
  }

  return (
    <AppContext.Provider value={{
      isConnected,
      setIsConnected,
      isPaperTrading,
      setIsPaperTrading,
      isAgentRunning,
      setIsAgentRunning,
      showCommandPalette,
      setShowCommandPalette,
      toasts,
      addToast,
      removeToast,
    }}>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/trading" element={<Trading />} />
          <Route path="/strategy" element={<Strategy />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/models" element={<Models />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </AppContext.Provider>
  );
}

export default App
