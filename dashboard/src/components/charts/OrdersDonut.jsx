import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const STATUS_COLORS = {
    ORDER_PLACED: '#9ca3af',
    PAYMENT_CONFIRMED: '#3b82f6',
    PICKUP_SCHEDULED: '#6366f1',
    PICKED_UP: '#f59e0b',
    AT_WAREHOUSE: '#8b5cf6',
    OUT_FOR_DELIVERY: '#f97316',
    DELIVERED: '#22c55e',
    CANCELLED: '#ef4444',
};

export default function OrdersDonut({ orders }) {
    if (!orders || orders.length === 0) {
        return <div className="text-center text-gray-400 py-8">No order data</div>;
    }

    // Count by status
    const counts = {};
    orders.forEach(o => {
        counts[o.status] = (counts[o.status] || 0) + 1;
    });

    const chartData = Object.entries(counts)
        .map(([status, count]) => ({ name: status.replace(/_/g, ' '), value: count, status }))
        .sort((a, b) => b.value - a.value);

    return (
        <ResponsiveContainer width="100%" height={280}>
            <PieChart>
                <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    dataKey="value"
                    label={({ name, value }) => `${value}`}
                    labelLine={false}
                >
                    {chartData.map((entry) => (
                        <Cell key={entry.status} fill={STATUS_COLORS[entry.status] || '#d1d5db'} />
                    ))}
                </Pie>
                <Tooltip
                    formatter={(v, name) => [v, name]}
                    contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #e5e7eb' }}
                />
                <Legend
                    wrapperStyle={{ fontSize: 11 }}
                    formatter={(value) => <span className="text-gray-600">{value}</span>}
                />
            </PieChart>
        </ResponsiveContainer>
    );
}
