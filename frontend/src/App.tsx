import { useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  PlayCircle,
  History,
  Settings,
  Youtube,
  Menu,
  X,
  Search,
  ChevronRight,
} from 'lucide-react';

import Dashboard from './pages/Dashboard';
import NewAnalysis from './pages/NewAnalysis';
import JobHistory from './pages/JobHistory';
import JobDetail from './pages/JobDetail';

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/new', icon: PlayCircle, label: 'New Analysis' },
  { path: '/history', icon: History, label: 'History' },
];

function Sidebar() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile menu button */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2.5 bg-sidebar text-white rounded-xl shadow-lg"
        onClick={() => setMobileOpen(!mobileOpen)}
      >
        {mobileOpen ? <X size={22} /> : <Menu size={22} />}
      </button>

      {/* Overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-72 bg-sidebar transform transition-transform duration-300 ease-out ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center gap-3 px-6 py-6">
            <div className="relative">
              <div className="w-11 h-11 bg-gradient-to-br from-primary-400 to-primary-600 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/30">
                <Youtube className="w-6 h-6 text-white" />
              </div>
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full border-2 border-sidebar"></div>
            </div>
            <div>
              <h1 className="font-bold text-white text-lg">Analytics</h1>
              <p className="text-xs text-gray-400">Video Intelligence</p>
            </div>
          </div>

          {/* Search */}
          <div className="px-4 mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search..."
                className="w-full pl-10 pr-4 py-2.5 bg-sidebar-light text-white placeholder-gray-500 rounded-xl border border-transparent focus:border-primary-500/50 focus:bg-sidebar-accent text-sm transition-all"
              />
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 space-y-1.5">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 mb-3">Menu</p>
            {navItems.map((item) => {
              const isActive = location.pathname === item.path || 
                (item.path === '/history' && location.pathname.startsWith('/job/'));
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
                    isActive
                      ? 'bg-gradient-to-r from-primary-500/20 to-primary-600/10 text-white'
                      : 'text-gray-400 hover:bg-sidebar-light hover:text-white'
                  }`}
                >
                  <div className={`p-2 rounded-lg transition-colors ${
                    isActive 
                      ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/30' 
                      : 'bg-sidebar-light text-gray-400 group-hover:text-white'
                  }`}>
                    <item.icon size={18} />
                  </div>
                  <span className="font-medium">{item.label}</span>
                  {isActive && <ChevronRight size={16} className="ml-auto text-primary-400" />}
                </Link>
              );
            })}
          </nav>

          {/* Pro Card */}
          <div className="px-4 pb-4">
            <div className="relative overflow-hidden rounded-2xl p-5" style={{
              background: 'linear-gradient(135deg, #ff6b9d 0%, #c44569 100%)'
            }}>
              <div className="absolute top-0 right-0 w-20 h-20 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2"></div>
              <div className="absolute bottom-0 left-0 w-16 h-16 bg-white/10 rounded-full translate-y-1/2 -translate-x-1/2"></div>
              <div className="relative z-10">
                <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center mb-3">
                  <Settings className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-white font-semibold mb-1">Need Help?</h3>
                <p className="text-white/70 text-xs mb-3">Check our documentation</p>
                <button className="w-full py-2 bg-white text-primary-600 rounded-lg text-sm font-medium hover:bg-white/90 transition-colors">
                  View Docs
                </button>
              </div>
            </div>
          </div>

          {/* User */}
          <div className="px-4 py-4 border-t border-white/5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white font-semibold">
                R
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white font-medium text-sm truncate">Researcher</p>
                <p className="text-gray-500 text-xs truncate">Market Analyst</p>
              </div>
              <button className="p-2 text-gray-500 hover:text-white transition-colors">
                <Settings size={18} />
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-gray-100">
        <Sidebar />
        <main className="flex-1 lg:ml-0 overflow-auto">
          <div className="p-6 lg:p-8 pt-20 lg:pt-8 max-w-7xl mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/new" element={<NewAnalysis />} />
              <Route path="/history" element={<JobHistory />} />
              <Route path="/job/:id" element={<JobDetail />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
