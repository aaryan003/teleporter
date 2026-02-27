import { useState } from 'react';
import { useInsights, useGenerateInsights } from '../api/client';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import { BrainCircuit, RefreshCw } from 'lucide-react';

const CATEGORIES = ['demand', 'revenue', 'fleet', 'operations', 'trends'];

export default function Insights() {
    const [category, setCategory] = useState('');
    const { data: insights, isLoading } = useInsights({ category: category || undefined });
    const generateMutation = useGenerateInsights();

    const handleGenerate = async () => {
        try {
            const result = await generateMutation.mutateAsync();
            alert(`Generated ${result.generated} new insight(s)!`);
        } catch (e) {
            alert('Failed to generate insights: ' + e.message);
        }
    };

    if (isLoading) return <Spinner />;

    return (
        <div className="space-y-4">
            {/* Toolbar */}
            <div className="flex items-center justify-between bg-white rounded-lg border border-gray-200 p-3">
                <div className="flex items-center gap-3">
                    <select
                        value={category}
                        onChange={e => setCategory(e.target.value)}
                        className="px-3 py-1.5 text-sm border border-gray-200 rounded"
                    >
                        <option value="">All Categories</option>
                        {CATEGORIES.map(c => (
                            <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                        ))}
                    </select>
                    <span className="text-xs text-gray-400">{(insights || []).length} insights</span>
                </div>
                <button
                    onClick={handleGenerate}
                    disabled={generateMutation.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
                >
                    {generateMutation.isPending ? (
                        <RefreshCw size={14} className="animate-spin" />
                    ) : (
                        <BrainCircuit size={14} />
                    )}
                    {generateMutation.isPending ? 'Generating...' : 'Generate Insights'}
                </button>
            </div>

            {/* Insight Cards */}
            {(!insights || insights.length === 0) ? (
                <div className="text-center text-gray-400 py-12">
                    <BrainCircuit size={40} className="mx-auto mb-3 text-gray-300" />
                    <p>No insights yet. Click "Generate Insights" to analyze your data.</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {insights.map(insight => (
                        <div key={insight.id} className={`bg-white rounded-lg border p-4 ${insight.severity === 'CRITICAL' ? 'border-red-200' :
                                insight.severity === 'WARNING' ? 'border-yellow-200' :
                                    'border-gray-200'
                            }`}>
                            <div className="flex items-center gap-2 mb-2">
                                <Badge value={insight.severity} />
                                <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">{insight.category}</span>
                                <span className="text-xs text-gray-400 ml-auto">
                                    {new Date(insight.generated_at).toLocaleString('en-IN')}
                                </span>
                                {!insight.is_read && <span className="w-2 h-2 bg-blue-500 rounded-full" title="Unread" />}
                            </div>
                            <h3 className="text-sm font-semibold text-gray-800 mb-1">{insight.title}</h3>
                            <p className="text-sm text-gray-600 leading-relaxed">{insight.insight}</p>
                            {insight.data && Object.keys(insight.data).length > 0 && (
                                <div className="mt-2 text-xs text-gray-400">
                                    Data: {JSON.stringify(insight.data).substring(0, 100)}...
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
