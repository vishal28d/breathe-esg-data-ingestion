import { useState, useEffect } from 'react';
import api from '../utils/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const tenantId = 1;

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const { data } = await api.get(`stats/?tenant=${tenantId}`);
      setStats(data);
    } catch (err) {
      console.error(err);
    }
  };

  if (!stats) return <div className="loading">Loading dashboard...</div>;

  const chartData = [
    { name: 'Scope 1', co2e: stats.co2e_by_scope.scope_1 },
    { name: 'Scope 2', co2e: stats.co2e_by_scope.scope_2 },
    { name: 'Scope 3', co2e: stats.co2e_by_scope.scope_3 },
  ];

  return (
    <div className="dashboard-page">
      <h1 className="page-title">Overview</h1>
      
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue"><Activity /></div>
          <div className="stat-info">
            <span className="stat-label">Total Records</span>
            <span className="stat-value">{stats.total_records}</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><CheckCircle2 /></div>
          <div className="stat-info">
            <span className="stat-label">Approved</span>
            <span className="stat-value">{stats.approved}</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow"><Clock /></div>
          <div className="stat-info">
            <span className="stat-label">Pending Review</span>
            <span className="stat-value">{stats.pending}</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red"><AlertTriangle /></div>
          <div className="stat-info">
            <span className="stat-label">Flagged / Errors</span>
            <span className="stat-value">{stats.flagged + stats.error}</span>
          </div>
        </div>
      </div>

      <div className="chart-section card">
        <h3>Emissions by Scope (kg CO2e)</h3>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
              <XAxis dataKey="name" tick={{fill: '#666'}} axisLine={false} tickLine={false} />
              <YAxis tick={{fill: '#666'}} axisLine={false} tickLine={false} />
              <Tooltip cursor={{fill: '#f5f5f5'}} />
              <Bar dataKey="co2e" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
