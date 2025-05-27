import './styles/App.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainPage from './pages/MainPage';
import ChatPage from './pages/ChatPage';
import AdminPage from './pages/AdminPage';
import DashBoardPage from './pages/DashBoardPage';
import { PageProvider } from './utils/PageContext';
import { QAHistoryProvider } from './utils/QAHistoryContext';

function App() {
  return (
    <PageProvider>
      <QAHistoryProvider>
        <Router>
          <Routes>
            <Route path="/" element={<MainPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/admin/:pageId" element={<AdminPage />} />
            <Route path="/dashboard/:pageId" element={<DashBoardPage />} />
          </Routes>
        </Router>  
      </QAHistoryProvider>
    </PageProvider>
  );
}

export default App;