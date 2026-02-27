export default function StatCard({ label, value, icon: Icon, sub, color = 'blue' }) {
    const colors = {
        blue: 'bg-blue-50 text-blue-600',
        green: 'bg-green-50 text-green-600',
        orange: 'bg-orange-50 text-orange-600',
        red: 'bg-red-50 text-red-600',
        purple: 'bg-purple-50 text-purple-600',
        gray: 'bg-gray-50 text-gray-600',
    };

    return (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-500">{label}</span>
                {Icon && (
                    <div className={`w-8 h-8 rounded flex items-center justify-center ${colors[color]}`}>
                        <Icon size={16} />
                    </div>
                )}
            </div>
            <div className="text-2xl font-bold text-gray-900">{value ?? '—'}</div>
            {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
        </div>
    );
}
