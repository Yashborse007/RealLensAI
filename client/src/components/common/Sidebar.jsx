import React, { useEffect, useRef } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  UploadCloud,
  History,
  FileText,
  UserCheck,
  ShieldCheck,
  ChevronRight,
  LogOut,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import Modal from "./Modal";
import Button from "./Button";

export default function Sidebar({ isOpen, onClose }) {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const [confirmLogout, setConfirmLogout] = React.useState(false);
  const sidebarRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    if (!isOpen) return undefined;
    const previousFocus = document.activeElement;
    sidebarRef.current?.querySelector("a")?.focus();
    const closeOnEscape = (event) => {
      if (event.key === "Escape") closeRef.current?.();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      if (previousFocus instanceof HTMLElement) previousFocus.focus();
    };
  }, [isOpen]);

  const handleLogout = () => {
    setConfirmLogout(false);
    logout();
    onClose && onClose();
    navigate("/login");
  };

  const menuItems = [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    {
      name: "Analyze Media",
      path: "/analyze",
      icon: UploadCloud,
      highlight: true,
    },
    { name: "Analysis history", path: "/history", icon: History },
    { name: "Reports", path: "/reports", icon: FileText },
    { name: "Profile", path: "/profile", icon: UserCheck },
    ...(user?.role === "admin"
      ? [{ name: "Admin Console", path: "/admin", icon: ShieldCheck }]
      : []),
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          aria-hidden="true"
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        ref={sidebarRef}
        id="dashboard-sidebar"
        aria-label="Main navigation"
        className={`fixed lg:static top-0 left-0 bottom-0 z-40 w-64 bg-slate-950/95 border-r border-slate-800/80 flex flex-col justify-between transition-transform duration-300 transform ${
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0 sidebar-closed"
        }`}
      >
        {/* Top Brand & Links */}
        <div className="p-4 space-y-6">
          {/* Dashboard Header Brand */}
          <div className="px-3 py-2 flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-lg bg-cyan-950 text-cyan-400 flex items-center justify-center border border-cyan-800/50">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h2 className="font-extrabold text-sm text-white font-['Outfit'] tracking-wide">
                  RealLens <span className="text-cyan-400">AI</span>
                </h2>
                <p className="text-[10px] text-slate-400">
                  Media analysis
                </p>
              </div>
            </div>
          </div>

          {/* Quick Action CTA */}
          <NavLink
            to="/analyze"
            onClick={onClose}
            className="w-full flex items-center justify-center space-x-2 px-4 py-3 rounded-lg bg-blue-700 hover:bg-blue-800 text-white font-semibold text-sm border border-blue-700 transition-colors"
          >
            <UploadCloud className="w-4 h-4 stroke-[2.5]" />
            <span>New analysis</span>
          </NavLink>

          {/* Nav List */}
          <nav className="space-y-1.5 pt-2">
            <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Workspace
            </p>

            {menuItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all group ${
                      isActive
                        ? "bg-blue-50 text-blue-800 border border-blue-100 font-semibold"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    }`
                  }
                >
                  <div className="flex items-center space-x-3">
                    <Icon className="w-4 h-4" />
                    <span>{item.name}</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-slate-500" />
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Bottom Quota & Info Widget */}
        <div className="p-4 border-t border-slate-800/80 space-y-4">
          <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
            <p className="text-xs font-medium text-slate-700">
              Automated results are not a substitute for human review.
            </p>
            <p className="break-all text-[11px] text-slate-500">
              {user?.email || "Signed in"}
            </p>
          </div>

          <button
            type="button"
            onClick={() => setConfirmLogout(true)}
            className="w-full flex items-center space-x-2.5 px-3 py-2 text-xs font-medium text-slate-400 hover:text-rose-400 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
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
    </>
  );
}
