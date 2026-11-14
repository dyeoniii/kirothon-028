import { Link, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import { MaskAuthorsProvider } from './lib/maskAuthors';
import AnalyzePage from './pages/AnalyzePage';
import CaseDetailPage from './pages/CaseDetailPage';
import CasesPage from './pages/CasesPage';
import DashboardPage from './pages/DashboardPage';
import EvidencePage from './pages/EvidencePage';
import ShareTargetPage from './pages/ShareTargetPage';

export default function App() {
  return (
    <MaskAuthorsProvider>
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/cases" element={<CasesPage />} />
        <Route path="/cases/:id" element={<CaseDetailPage />} />
        <Route path="/evidence" element={<EvidencePage />} />
        <Route path="/share-target" element={<ShareTargetPage />} />
        <Route
          path="*"
          element={
            <p className="text-sm">
              페이지를 찾을 수 없습니다.{' '}
              <Link to="/" className="font-semibold text-brand-700">
                홈으로
              </Link>
            </p>
          }
        />
      </Routes>
    </Layout>
    </MaskAuthorsProvider>
  );
}
