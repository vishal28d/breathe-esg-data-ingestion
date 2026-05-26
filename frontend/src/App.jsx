import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Ingestion from './pages/Ingestion';
import Review from './pages/Review';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="ingest" element={<Ingestion />} />
        <Route path="review" element={<Review />} />
      </Route>
    </Routes>
  );
}

export default App;
