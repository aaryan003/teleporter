import {
    Package, Truck, CheckCircle, XCircle, IndianRupee, Clock, TrendingUp, Users,
} from 'lucide-react';
import { useStats, useRevenueChart, useFleetSummary, useOrders } from '../api/client';
import StatCard from '../components/ui/StatCard';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import RevenueChart from '../components/charts/RevenueChart';
import OrdersDonut from '../components/charts/OrdersDonut';
import FleetStatusBar from '../components/charts/FleetStatusBar';

export default function Dashboard() {
    const { data: stats, isLoading: statsLoading } = useStats();
    const { data: revenue } = useRevenueChart(30);
    const { data: fleet } = useFleetSummary();
    const { data: recentOrders } = useOrders({ limit: 5 });

    if (statsLoading) return <Spinner />;

    return (
        <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard label="Orders Today" value={stats?.orders_today} icon={Package} color="blue" />
                <StatCard label="In Transit" value={stats?.orders_in_transit} icon={Truck} color="orange" />
                <StatCard label="Delivered" value={stats?.orders_delivered} icon={CheckCircle} color="green" />
                <StatCard label="Cancelled" value={stats?.orders_cancelled} icon={XCircle} color="red" />
                <StatCard label="Revenue Today" value={stats?.revenue_today != null ? `₹${stats.revenue_today}` : '—'} icon={IndianRupee} color="green" />
                <StatCard label="Revenue This Week" value={stats?.revenue_this_week != null ? `₹${stats.revenue_this_week}` : '—'} icon={TrendingUp} color="blue" />
                <StatCard label="Revenue This Month" value={stats?.revenue_this_month != null ? `₹${stats.revenue_this_month}` : '—'} icon={TrendingUp} color="purple" />
                <StatCard label="Active Riders" value={stats?.active_riders} icon={Users} color="green" sub={stats?.avg_delivery_time_min ? `Avg ${stats.avg_delivery_time_min} min` : null} />
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">Revenue (30 Days)</h3>
                    <RevenueChart data={revenue?.data} />
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">Fleet Status</h3>
                    <FleetStatusBar fleet={fleet} />
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Orders by Status */}
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">Orders by Status</h3>
                    <OrdersDonut orders={recentOrders} />
                </div>

                {/* Recent Orders */}
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">Recent Orders</h3>
                    {recentOrders && recentOrders.length > 0 ? (
                        <div className="space-y-2">
                            {recentOrders.slice(0, 5).map(order => (
                                <div key={order.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                                    <div>
                                        <span className="text-sm font-mono font-medium text-gray-800">{order.order_number}</span>
                                        <div className="text-xs text-gray-400 mt-0.5 truncate max-w-[200px]">{order.pickup_address}</div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-medium">₹{order.total_cost}</span>
                                        <Badge value={order.status} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center text-gray-400 py-8">No orders yet</div>
                    )}
                </div>
            </div>
        </div>
    );
}
