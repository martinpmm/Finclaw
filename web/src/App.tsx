import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import CompanyDetail from './pages/CompanyDetail'
import Documents from './pages/Documents'
import Setup from './pages/Setup'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/company/:symbol" element={<CompanyDetail />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/setup" element={<Setup />} />
      </Route>
    </Routes>
  )
}
