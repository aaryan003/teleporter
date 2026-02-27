import { NavLink } from 'react-router-dom';
import {
    LayoutDashboard, Package, Truck, Warehouse, BrainCircuit, Settings,
} from 'lucide-react';

const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/orders', icon: Package, label: 'Orders' },
    { to: '/fleet', icon: Truck, label: 'Fleet' },
    { to: '/warehouses', icon: Warehouse, label: 'Warehouses' },
    { to: '/insights', icon: BrainCircuit, label: 'AI Insights' },
    { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
    return (
        <aside className="w-56 bg-white border-r border-gray-200 flex flex-col h-screen">
            <div className="h-14 flex items-center px-4 border-b border-gray-200">
                <span className="text-lg font-bold text-gray-800">📦 TeleporterBot</span>
            </div>
            <nav className="flex-1 py-3">
                {navItems.map(({ to, icon: Icon, label }) => (
                    <NavLink
                        key={to}
                        to={to}
                        end={to === '/'}
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-colors ${isActive
                                ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                            }`
                        }
                    >
                        <Icon size={18} />
                        {label}
                    </NavLink>
                ))}
            </nav>
            <div className="p-4 border-t border-gray-200 text-xs text-gray-400">
                TeleporterBot Admin v2.0
            </div>
        </aside>
    );
}
