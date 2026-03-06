import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/shared/Layout'
import { AgentPage } from './pages/AgentPage'
import { StudioPage } from './pages/StudioPage'
import { LoginPage } from './pages/LoginPage'
import { ProtectedRoute } from './components/shared/ProtectedRoute'

function App() {
    return (
        <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
                <Route element={<Layout />}>
                    <Route path="/" element={<AgentPage />} />
                    <Route path="/studio" element={<StudioPage />} />
                </Route>
            </Route>
        </Routes>
    )
}

export default App
