import { useState } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';

export default function DataTable({ columns, data, onRowClick, emptyMessage = 'No data' }) {
    const [sortCol, setSortCol] = useState(null);
    const [sortDir, setSortDir] = useState('asc');

    const handleSort = (key) => {
        if (sortCol === key) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        } else {
            setSortCol(key);
            setSortDir('asc');
        }
    };

    const sorted = sortCol
        ? [...(data || [])].sort((a, b) => {
            const va = a[sortCol] ?? '';
            const vb = b[sortCol] ?? '';
            const cmp = typeof va === 'number' ? va - vb : String(va).localeCompare(String(vb));
            return sortDir === 'asc' ? cmp : -cmp;
        })
        : data || [];

    if (!data || data.length === 0) {
        return <div className="text-center text-gray-400 py-12">{emptyMessage}</div>;
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-gray-200">
                        {columns.map(col => (
                            <th
                                key={col.key}
                                className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700"
                                onClick={() => col.sortable !== false && handleSort(col.key)}
                            >
                                <div className="flex items-center gap-1">
                                    {col.label}
                                    {sortCol === col.key && (
                                        sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />
                                    )}
                                </div>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {sorted.map((row, i) => (
                        <tr
                            key={row.id || i}
                            onClick={() => onRowClick?.(row)}
                            className={`border-b border-gray-100 ${onRowClick ? 'cursor-pointer hover:bg-gray-50' : ''}`}
                        >
                            {columns.map(col => (
                                <td key={col.key} className="py-3 px-3 text-gray-700">
                                    {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '—')}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
