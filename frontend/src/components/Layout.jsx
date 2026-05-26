import { useState, useEffect } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, FileUp, ClipboardCheck, Leaf } from 'lucide-react';

export default function Layout() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="logo">
          <Leaf className="logo-icon" size={28} />
          <span>Breathe ESG</span>
        </div>
        <nav className="nav-links">
          <NavLink to="/" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')} end>
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </NavLink>
          <NavLink to="/ingest" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            <FileUp size={20} />
            <span>Ingest Data</span>
          </NavLink>
          <NavLink to="/review" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            <ClipboardCheck size={20} />
            <span>Review & Approve</span>
          </NavLink>
        </nav>
      </aside>
      <main className="main-content">
        <header className="top-header">
          <h2>Data Operations</h2>
          <div className="user-profile">
            <div className="avatar">A</div>
            <span>Analyst</span>
          </div>
        </header>
        <div className="content-area">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
