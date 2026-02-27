import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const COLORS = {
    on_duty: '#22c55e',
    on_delivery: '#f97316',
    on_pickup: '#3b82f6',
    off_duty: '#9ca3af',
};

export default function FleetStatusBar({ fleet }) {
    if (!fleet) return null;

    const data = [
        { name: 'On Duty', value: fleet.on_duty || 0, key: 'on_duty' },
        { name: 'On Delivery', value: fleet.on_delivery || 0, key: 'on_delivery' },
        { name: 'On Pickup', value: fleet.on_pickup || 0, key: 'on_pickup' },
        { name: 'Off Duty', value: fleet.off_duty || 0, key: 'off_duty' },
    ];

    return (
        <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#999' }} />
                <YAxis tick={{ fontSize: 11, fill: '#999' }} allowDecimals={false} />
                <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #e5e7eb' }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {data.map((entry) => (
                        <Cell key={entry.key} fill={COLORS[entry.key]} />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}
