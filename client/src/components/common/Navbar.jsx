import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  ShieldCheck, 
  LogIn, 
  Menu, 
  X, 
  LogOut,
} from 'lucide-react';
import Button from './Button';
import { useAuth } from '../../context/AuthContext';
import Modal from './Modal';

export default function Navbar({
  isDashboard = false,
  onMobileMenuToggle,
  dashboardMenuOpen = false,
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [confirmLogout, setConfirmLogout] = useState(false);

  const isActive = (path) => location.pathname === path;

  const handleLogout = () => {
    setConfirmLogout(false);
    logout();
    navigate('/login');
  };

  const userInitials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : 'AV';

  useEffect(() => {
    if (isDashboard || !mobileMenuOpen) return undefined;
    const previousFocus = document.activeElement;
    const firstLink = document.querySelector("#public-mobile-menu a");
    firstLink?.focus();
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setMobileMenuOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      if (previousFocus instanceof HTMLElement) previousFocus.focus();
    };
  }, [isDashboard, mobileMenuOpen]);

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand Logo */}
        <div className="flex items-center space-x-3">
          {isDashboard && (
            <button
              type="button"
              onClick={onMobileMenuToggle}
              aria-label={dashboardMenuOpen ? "Close main menu" : "Open main menu"}
              aria-expanded={dashboardMenuOpen}
              aria-controls="dashboard-sidebar"
              className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            >
              {dashboardMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          )}

          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-700 flex items-center justify-center shadow-sm">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-extrabold text-lg tracking-tight text-slate-900">
                RealLens <span className="text-cyan-600">AI</span>
              </span>
              <span className="hidden sm:inline-block ml-2 text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200">
                Forensic Portal
              </span>
            </div>
          </Link>
        </div>

        {/* Public Desktop Nav Links */}
        {!isDashboard ? (
          <nav className="hidden md:flex items-center space-x-8">
            <Link
              to="/"
              className={`text-sm transition-colors ${
                isActive('/') ? 'text-cyan-600 font-bold' : 'text-slate-600 hover:text-cyan-600 font-medium'
              }`}
            >
              Home
            </Link>
            <Link
              to="/dashboard"
              className={`text-sm transition-colors ${
                isActive('/dashboard') ? 'text-cyan-600 font-bold' : 'text-slate-600 hover:text-cyan-600 font-medium'
              }`}
            >
              Dashboard
            </Link>
            <Link
              to="/analyze"
              className={`text-sm transition-colors ${
                isActive('/analyze') ? 'text-cyan-600 font-bold' : 'text-slate-600 hover:text-cyan-600 font-medium'
              }`}
            >
              Analyze Media
            </Link>
            <Link
              to="/reports"
              className={`text-sm transition-colors ${
                isActive('/reports') ? 'text-cyan-600 font-bold' : 'text-slate-600 hover:text-cyan-600 font-medium'
              }`}
            >
              Reports
            </Link>
          </nav>
        ) : (
          <div className="hidden md:flex items-center space-x-6">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-800 text-xs font-medium">
              Image, video and audio analysis
            </span>
          </div>
        )}

        {/* Auth CTA / Profile Menu */}
        <div className="flex items-center space-x-3">
          {!isAuthenticated ? (
            <div className="flex items-center space-x-2">
              <Link to="/login">
                <Button variant="ghost" size="sm" icon={LogIn}>
                  Sign In
                </Button>
              </Link>
              <Link to="/register">
                <Button variant="primary" size="sm" icon={ShieldCheck}>
                  Register Account
                </Button>
              </Link>
            </div>
          ) : (
            <div className="flex items-center space-x-3">
              <Link to="/profile">
                <div className="flex items-center space-x-3 p-1.5 rounded-lg bg-white border border-slate-200 hover:border-blue-300 transition-colors">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-800 flex items-center justify-center font-bold text-xs border border-blue-100">
                    {userInitials}
                  </div>
                  <div className="hidden sm:block text-left pr-2">
                    <p className="text-xs font-bold text-slate-900 leading-tight">{user?.name || 'Investigator'}</p>
                    <p className="text-[10px] text-slate-500 capitalize">
                      {user?.isSampleData ? "Demo session" : user?.role || 'user'}
                    </p>
                  </div>
                </div>
              </Link>

              <button
                onClick={() => setConfirmLogout(true)}
                aria-label="Sign out"
                className="p-2 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-rose-50 border border-slate-200 transition-colors"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Mobile hamburger menu toggle */}
          {!isDashboard && (
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-expanded={mobileMenuOpen}
              aria-controls="public-mobile-menu"
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          )}
        </div>
      </div>

      {/* Public Mobile Menu Drawer */}
      {!isDashboard && mobileMenuOpen && (
        <nav id="public-mobile-menu" aria-label="Mobile navigation" className="md:hidden border-b border-slate-800 bg-slate-950/95 px-4 pt-2 pb-6 space-y-3">
          <Link
            to="/"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-medium text-slate-200 hover:text-cyan-400"
          >
            Home
          </Link>
          <Link
            to="/dashboard"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-medium text-slate-200 hover:text-cyan-400"
          >
            Dashboard
          </Link>
          <Link
            to="/analyze"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-medium text-slate-200 hover:text-cyan-400"
          >
            Analyze Media
          </Link>
          <Link
            to="/reports"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-medium text-slate-200 hover:text-cyan-400"
          >
            PDF Reports
          </Link>
          <div className="pt-2 border-t border-slate-800 flex flex-col space-y-2">
            {!isAuthenticated ? (
              <>
                <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="ghost" size="sm" className="w-full">
                    Sign In
                  </Button>
                </Link>
                <Link to="/register" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="primary" size="sm" className="w-full">
                    Register Account
                  </Button>
                </Link>
              </>
            ) : (
              <Button
                variant="danger"
                size="sm"
                icon={LogOut}
                onClick={() => {
                  setMobileMenuOpen(false);
                  setConfirmLogout(true);
                }}
                className="w-full"
              >
                Sign out
              </Button>
            )}
          </div>
        </nav>
      )}
      <Modal
        isOpen={confirmLogout}
        onClose={() => setConfirmLogout(false)}
        title="Sign out of RealLens AI?"
        footer={
          <>
            <Button variant="outline" onClick={() => setConfirmLogout(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleLogout}>
              Sign out
            </Button>
          </>
        }
      >
        You will need to sign in again to access your analyses and reports.
      </Modal>
    </header>
  );
}
