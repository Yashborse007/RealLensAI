import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../components/common/Navbar';
import Footer from '../components/common/Footer';

export default function PublicLayout() {
  return (
    <div className="min-h-screen flex flex-col justify-between text-slate-900 bg-slate-50">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <Navbar isDashboard={false} />
      <main id="main-content" className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
