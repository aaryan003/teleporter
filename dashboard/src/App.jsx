import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import Dashboard from './pages/Dashboard';
import Orders from './pages/Orders';
import Fleet from './pages/Fleet';
import Warehouses from './pages/Warehouses';
import Insights from './pages/Insights';
import Settings from './pages/Settings';

export default function App() {
    return (
        <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
                <TopBar />
                <main className="flex-1 overflow-y-auto p-6 bg-gray-50">
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/orders" element={<Orders />} />
                        <Route path="/fleet" element={<Fleet />} />
                        <Route path="/warehouses" element={<Warehouses />} />
                        <Route path="/insights" element={<Insights />} />
                        <Route path="/settings" element={<Settings />} />
                    </Routes>
                </main>
            </div>
        </div>
    );
}
