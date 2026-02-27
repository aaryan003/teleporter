import { useLocation } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

const pageTitles = {
    '/': 'Dashboard',
    '/orders': 'Orders',
    '/fleet': 'Fleet Management',
    '/warehouses': 'Warehouses',
    '/insights': 'AI Insights',
    '/settings': 'Settings',
};

export default function TopBar() {
    const location = useLocation();
    const qc = useQueryClient();
    const [refreshing, setRefreshing] = useState(false);

    const title = pageTitles[location.pathname] || 'Dashboard';

    const handleRefresh = async () => {
        setRefreshing(true);
        await qc.invalidateQueries();
        setTimeout(() => setRefreshing(false), 600);
    };

    return (
        <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6">
            <h1 className="text-lg font-semibold text-gray-800">{title}</h1>
            <div className="flex items-center gap-4">
                <span className="text-xs text-gray-400">Auto-refreshes every 30s</span>
                <button
                    onClick={handleRefresh}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
                >
                    <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
                    Refresh
                </button>
            </div>
        </header>
    );
}
