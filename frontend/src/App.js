import './styles/App.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainPage from './pages/MainPage';
import ChatPage from './pages/ChatPage';
import AdminPage from './pages/AdminPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/admin/:pageId" element={<AdminPage />} />
      </Routes>
    </Router>
  );
}

export default App;