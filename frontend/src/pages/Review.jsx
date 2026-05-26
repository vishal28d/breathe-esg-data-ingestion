import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import api from '../utils/api';
import { Check, X, AlertTriangle, Eye, Info } from 'lucide-react';

export default function Review() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [filter, setFilter] = useState('PENDING'); // PENDING, FLAGGED, ERROR, APPROVED, ALL
  const tenantId = 1;

  useEffect(() => {
    fetchRecords();
  }, [filter]);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const url = filter === 'ALL' ? `records/?tenant=${tenantId}` : `records/?tenant=${tenantId}&status=${filter}`;
      const { data } = await api.get(url);
      setRecords(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id) => {
    try {
      await api.post(`records/${id}/approve/`);
      fetchRecords(); // refresh list
    } catch (err) {
      console.error(err);
    }
  };

  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return;
    try {
      await api.post('records/bulk-approve/', { ids: Array.from(selectedIds) });
      setSelectedIds(new Set());
      fetchRecords();
    } catch (err) {
      console.error(err);
    }
  };

  const toggleSelect = (id) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === records.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(records.map(r => r.id)));
    }
  };

  const StatusBadge = ({ status }) => {
    const config = {
      PENDING: { color: 'yellow', icon: <Clock size={14} /> },
      APPROVED: { color: 'green', icon: <Check size={14} /> },
      FLAGGED: { color: 'orange', icon: <AlertTriangle size={14} /> },
      ERROR: { color: 'red', icon: <X size={14} /> }
    };
    const c = config[status] || config.PENDING;
    return <span className={`badge ${c.color}`}>{c.icon} {status}</span>;
  };

  // Helper just for the badge since Clock isn't imported from lucide above
  // (Let's just use CSS classes for simplicity)
  const getStatusClass = (status) => {
    switch (status) {
      case 'APPROVED': return 'badge-green';
      case 'FLAGGED': return 'badge-orange';
      case 'ERROR': return 'badge-red';
      default: return 'badge-yellow';
    }
  };

  return (
    <div className="review-page">
      <div className="page-header">
        <h1 className="page-title">Review & Approve</h1>
        <div className="actions">
          <select value={filter} onChange={(e) => setFilter(e.target.value)} className="select-filter">
            <option value="PENDING">Pending Review</option>
            <option value="FLAGGED">Flagged / Suspicious</option>
            <option value="ERROR">Errors</option>
            <option value="APPROVED">Approved</option>
            <option value="ALL">All Records</option>
          </select>
          <button 
            className="btn primary" 
            onClick={handleBulkApprove}
            disabled={selectedIds.size === 0 || filter === 'APPROVED'}
          >
            <Check size={16} /> Approve Selected ({selectedIds.size})
          </button>
        </div>
      </div>

      <div className="card table-container">
        {loading ? (
          <div className="loading">Loading records...</div>
        ) : records.length === 0 ? (
          <div className="empty-state">No {filter.toLowerCase()} records found.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>
                  <input 
                    type="checkbox" 
                    checked={selectedIds.size === records.length && records.length > 0}
                    onChange={toggleSelectAll}
                  />
                </th>
                <th>Source</th>
                <th>Date</th>
                <th>Category</th>
                <th>Value</th>
                <th>CO2e (kg)</th>
                <th>Status</th>
                <th>Warnings</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map(record => {
                const warnings = JSON.parse(record.validation_warnings || '[]');
                
                return (
                  <tr key={record.id} className={selectedIds.has(record.id) ? 'selected' : ''}>
                    <td>
                      <input 
                        type="checkbox" 
                        checked={selectedIds.has(record.id)}
                        onChange={() => toggleSelect(record.id)}
                      />
                    </td>
                    <td><span className="source-tag">{record.import_source}</span></td>
                    <td>{record.activity_date_start ? format(new Date(record.activity_date_start), 'MMM d, yyyy') : 'N/A'}</td>
                    <td className="capitalize">{record.category.replace('_', ' ')}</td>
                    <td>
                      {record.normalized_value ? (
                        `${parseFloat(record.normalized_value).toLocaleString(undefined, {maximumFractionDigits: 2})} ${record.normalized_unit}`
                      ) : (
                        <span className="text-gray">N/A</span>
                      )}
                    </td>
                    <td className="font-semibold">
                      {record.co2e_kg ? parseFloat(record.co2e_kg).toLocaleString(undefined, {maximumFractionDigits: 2}) : '-'}
                    </td>
                    <td>
                      <span className={`badge ${getStatusClass(record.status)}`}>{record.status}</span>
                    </td>
                    <td>
                      {warnings.length > 0 ? (
                        <div className="warning-list">
                          {warnings.map((w, i) => (
                            <span key={i} className="warning-item" title={w}>
                              <AlertTriangle size={12} /> {w.substring(0, 30)}...
                            </span>
                          ))}
                        </div>
                      ) : <span className="text-gray">-</span>}
                    </td>
                    <td>
                      <div className="row-actions">
                        {record.status !== 'APPROVED' && (
                          <button 
                            className="icon-btn approve" 
                            onClick={() => handleApprove(record.id)}
                            title="Approve"
                          >
                            <Check size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
