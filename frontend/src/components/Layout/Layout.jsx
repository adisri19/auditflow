import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  BarChart3, 
  CheckSquare, 
  UploadCloud, 
  Database, 
  LogOut, 
  User, 
  ShieldAlert, 
  Building2 
} from 'lucide-react';

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  
  const userJson = localStorage.getItem('user');
  const user = userJson ? JSON.parse(userJson) : { username: 'Analyst', email: 'analyst@demo.com', tenant: { name: 'Demo Corp' } };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', path: '/', icon: BarChart3 },
    { name: 'Review Console', path: '/review', icon: CheckSquare },
    { name: 'Upload Data', path: '/upload', icon: UploadCloud },
    { name: 'Ingestion Logs', path: '/batches', icon: Database },
  ];

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden text-slate-100 font-sans">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800/60 bg-slate-900/60 backdrop-blur-xl flex flex-col justify-between shrink-0">
        <div>
          {/* Logo / Brand */}
          <div className="p-6 border-b border-slate-800/40 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-brand-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-extrabold text-lg leading-tight tracking-tight bg-gradient-to-r from-emerald-400 to-sky-400 bg-clip-text text-transparent">
                BREATHE ESG
              </h1>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Emissions Engine</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="p-4 space-y-1.5">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-brand-600/20 to-brand-500/10 text-emerald-400 border border-brand-500/20 shadow-md shadow-brand-500/5'
                      : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-100 border border-transparent'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Footer / Tenant Details */}
        <div className="p-4 border-t border-slate-800/40 space-y-3">
          <div className="flex items-center gap-3 px-2">
            <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
              <User className="w-4 h-4 text-slate-400" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-200 truncate">{user.username}</p>
              <p className="text-[10px] text-slate-500 truncate">{user.tenant?.name || 'No Tenant'}</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-rose-400 hover:text-rose-300 bg-rose-500/5 hover:bg-rose-500/10 border border-rose-500/10 transition-all cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header / Top Bar */}
        <header className="h-16 border-b border-slate-800/60 bg-slate-900/40 backdrop-blur-xl px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <Building2 className="w-4 h-4 text-slate-500" />
            <span className="text-xs font-bold text-slate-400 bg-slate-800 px-2.5 py-1 rounded-md">
              Tenant: {user.tenant?.name || 'Local Workspace'}
            </span>
          </div>

          <div className="flex items-center gap-4">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-xs text-slate-400 font-medium">Audit Pipeline Active</span>
          </div>
        </header>

        {/* Children content */}
        <main className="flex-1 overflow-y-auto bg-slate-950 p-8">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
