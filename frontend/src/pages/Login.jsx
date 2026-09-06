import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Lock, Mail, AlertCircle, RefreshCw } from 'lucide-react';
import client from '../api/client';
const Login = () => {
  const [username, setUsername] = useState('admin@demo.com');
  const [password, setPassword] = useState('breathe2024');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await client.post('/auth/login/', {        username,
        password
      });

      const { access, refresh, user } = response.data;
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      localStorage.setItem('user', JSON.stringify(user));

      navigate('/');
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Invalid username or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden font-sans">
      {/* Decorative Orbs */}
      <div className="absolute top-1/4 left-1/4 w-[350px] h-[350px] bg-emerald-500/10 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-[300px] h-[300px] bg-sky-500/10 rounded-full blur-[100px] pointer-events-none"></div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="flex justify-center mb-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-brand-600 to-brand-500 flex items-center justify-center shadow-xl shadow-brand-500/25">
            <Building2 className="w-6 h-6 text-white" />
          </div>
        </div>
        <h2 className="text-center text-3xl font-extrabold tracking-tight bg-gradient-to-r from-emerald-400 to-sky-400 bg-clip-text text-transparent">
          Breathe ESG
        </h2>
        <p className="mt-2 text-center text-xs text-slate-400 font-medium">
          Emissions Ingestion & Audit Portal
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-slate-900/60 border border-slate-800/60 backdrop-blur-2xl py-8 px-4 shadow-2xl rounded-3xl sm:px-10">
          <form className="space-y-6" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-slate-500" />
                </div>
                <input
                  type="email"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="analyst@breatheesg.com"
                  className="block w-full pl-10 pr-4 py-3 bg-slate-950/80 border border-slate-800 rounded-2xl text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-slate-500" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="block w-full pl-10 pr-4 py-3 bg-slate-950/80 border border-slate-800 rounded-2xl text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all"
                />
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-3.5 px-4 rounded-2xl border border-transparent text-sm font-bold text-white bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500 shadow-lg shadow-brand-500/20 transition-all cursor-pointer disabled:opacity-50"
              >
                {loading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  'Sign In'
                )}
              </button>
            </div>
          </form>

          {/* Quick Demo Credentials Help */}
          <div className="mt-8 pt-6 border-t border-slate-800/40 text-center">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Demo Credentials</p>
            <div className="mt-2 text-xs text-slate-400 bg-slate-950/60 p-3 rounded-2xl border border-slate-800/30 flex flex-col gap-1 items-center">
              <span>Email: <strong className="text-emerald-400 font-semibold">admin@demo.com</strong></span>
              <span>Password: <strong className="text-emerald-400 font-semibold">breathe2024</strong></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
