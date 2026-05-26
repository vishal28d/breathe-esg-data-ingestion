import { useState } from 'react';
import api from '../utils/api';
import { UploadCloud, Server, Database, CheckCircle, AlertCircle } from 'lucide-react';

export default function Ingestion() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const tenantId = 1;

  const handleFileUpload = async (event, source) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('tenant_id', tenantId);

    try {
      const { data } = await api.post(`ingest/${source}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResult({ type: 'success', data });
    } catch (err) {
      setResult({ type: 'error', message: err.response?.data?.error || err.message });
    } finally {
      setLoading(false);
      event.target.value = ''; // Reset input
    }
  };

  const handleApiPull = async () => {
    setLoading(true);
    setResult(null);
    try {
      const { data } = await api.post('ingest/travel/', { tenant_id: tenantId });
      setResult({ type: 'success', data });
    } catch (err) {
      setResult({ type: 'error', message: err.response?.data?.error || err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ingestion-page">
      <h1 className="page-title">Data Ingestion</h1>
      
      {result && (
        <div className={`alert ${result.type}`}>
          {result.type === 'success' ? (
            <>
              <CheckCircle size={20} />
              <span>Import successful! Processed {result.data.row_count} rows ({result.data.error_count} errors).</span>
            </>
          ) : (
            <>
              <AlertCircle size={20} />
              <span>Import failed: {result.message}</span>
            </>
          )}
        </div>
      )}

      <div className="ingest-grid">
        {/* SAP */}
        <div className="card ingest-card">
          <div className="card-header">
            <Database className="card-icon blue" size={24} />
            <h3>SAP Flat File</h3>
          </div>
          <p>Upload CSV exports from SAP IS-Oil (Fuel / Procurement). We automatically parse German numbers and dates.</p>
          <div className="upload-btn-wrapper">
            <button className="btn primary" disabled={loading}>
              {loading ? 'Uploading...' : 'Upload SAP CSV'}
            </button>
            <input type="file" accept=".csv" onChange={(e) => handleFileUpload(e, 'sap')} disabled={loading} />
          </div>
        </div>

        {/* Utility */}
        <div className="card ingest-card">
          <div className="card-header">
            <UploadCloud className="card-icon green" size={24} />
            <h3>Utility Portal Data</h3>
          </div>
          <p>Upload electricity usage CSVs. Supports off-month billing periods and kWh/MWh conversion.</p>
          <div className="upload-btn-wrapper">
            <button className="btn primary" disabled={loading}>
              {loading ? 'Uploading...' : 'Upload Utility CSV'}
            </button>
            <input type="file" accept=".csv" onChange={(e) => handleFileUpload(e, 'utility')} disabled={loading} />
          </div>
        </div>

        {/* Travel API */}
        <div className="card ingest-card">
          <div className="card-header">
            <Server className="card-icon yellow" size={24} />
            <h3>Corporate Travel API</h3>
          </div>
          <p>Pull latest booking data directly from Navan / Concur. We calculate emissions from IATA codes.</p>
          <button className="btn primary" onClick={handleApiPull} disabled={loading}>
            {loading ? 'Pulling Data...' : 'Trigger API Pull'}
          </button>
        </div>
      </div>
    </div>
  );
}
