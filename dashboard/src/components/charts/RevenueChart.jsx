import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function RevenueChart({ data }) {
    if (!data || data.length === 0) {
        return <div className="text-center text-gray-400 py-8">No revenue data</div>;
    }

    return (
        <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: '#999' }}
                    tickFormatter={v => v.slice(5)}
                />
                <YAxis tick={{ fontSize: 11, fill: '#999' }} tickFormatter={v => `₹${v}`} />
                <Tooltip
                    formatter={(v) => [`₹${v}`, 'Revenue']}
                    contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #e5e7eb' }}
                />
                <Line
                    type="monotone"
                    dataKey="revenue"
                    stroke="#2563eb"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                />
            </LineChart>
        </ResponsiveContainer>
    );
}
